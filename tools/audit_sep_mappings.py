"""Read-only Darpan SEP catalog + Excel routing audit.

Run from project root:
 python tools/audit_sep_mappings.py --department Admin
 python tools/audit_sep_mappings.py --all

No ticket writes. Never prints PAT or email. CSV is created in chosen --output directory.
"""
import argparse
import csv
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def norm(value):
    value = unicodedata.normalize('NFKC', str(value or '')).casefold()
    value = re.sub(r'\s*&\s*', ' and ', value)
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def candidates(name, items):
    return [x for x in items if norm(x.get('name')) == norm(name)]


def get_page_all(session, base_url, endpoint, params):
    """Collect all pages; fail closed on malformed responses or excessive pagination."""
    found = []
    for page in range(50):
        query = {**params, 'page': page, 'size': 100}
        response = session.get(f'{base_url}/api/itsm/v1/lookup/{endpoint}', params=query, timeout=25)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get('content'), list):
            raise ValueError(f'Unexpected {endpoint} response format')
        found.extend(payload['content'])
        pages = payload.get('totalPages')
        if pages is not None:
            if page + 1 >= int(pages):
                return found
        elif len(payload['content']) < 100:
            return found
        time.sleep(.08)
    raise ValueError(f'{endpoint}: pagination exceeded safe limit')


def route_rows(path):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError('Install openpyxl: python -m pip install openpyxl') from exc
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        entries = iter(ws.values)
        headers = [str(v or '').strip() for v in next(entries)]
        needed = {'Ticket Id', 'Group Name', 'Ticket Type', 'Group ID', 'Location', 'Department'}
        if not needed.issubset(headers):
            raise ValueError(f'Routing sheet missing columns: {sorted(needed-set(headers))}')
        for row in entries:
            entry = dict(zip(headers, row))
            if entry.get('Department') and entry.get('Ticket Type'):
                yield entry
    finally:
        wb.close()


def run(args):
    from ai.agent.catalog import CATEGORIES, SUBCATEGORY_REQUEST_TYPES
    from dotenv import load_dotenv
    import requests
    load_dotenv(PROJECT_ROOT / '.env')
    base = os.getenv('TICKETING_BASE_URL', '').rstrip('/')
    token = os.getenv('TICKETING_PAT', '')
    if not base.startswith('https://') or not token:
        raise RuntimeError('Set TICKETING_BASE_URL (HTTPS) and TICKETING_PAT in your project .env')
    route_file = PROJECT_ROOT / 'data' / 'ticket_routing.xlsx'
    if not route_file.exists():
        raise FileNotFoundError(f'Routing workbook missing: {route_file}')
    rows = list(route_rows(route_file))
    dept_set = {r['Department'] for r in rows}
    if args.all:
        departments = sorted(set(CATEGORIES) & dept_set)
    else:
        departments = [args.department]
    session = requests.Session()
    session.headers.update({'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
    category_cache = {}
    subcategory_cache = {}
    output = []

    def report(dept, kind, request_type, location, category, subcategory, status, expected='', actual='', sep_id='', info=''):
        output.append(dict(department=dept, kind=kind, request_type=request_type, location=location,
                           category=category, subcategory=subcategory, status=status,
                           darpan_value=expected, sep_value=actual, sep_id=sep_id, detail=info))

    for dept in departments:
        if dept not in CATEGORIES:
            report(dept,'catalog','','','','','NO_CATALOG',info='Department absent from CATEGORIES')
            continue
        group_rows = [r for r in rows if str(r['Department']).strip().casefold() == dept.casefold()]
        if not group_rows:
            report(dept,'routing','','','','','NO_ROUTING',info='No routing rows found for department')
            continue
        by_type = defaultdict(list)
        for r in group_rows:
            by_type[str(r['Ticket Type']).strip()].append(r)
            if not isinstance(r['Ticket Id'], int) or not isinstance(r['Group ID'], int):
                report(dept,'routing',r['Ticket Type'],r['Location'],'','','BAD_ROUTING_ID',info=str(r['Group Name']))
        for request_type, ritems in sorted(by_type.items()):
            tids = sorted({int(r['Ticket Id']) for r in ritems if isinstance(r['Ticket Id'], int)})
            if len(tids) != 1:
                report(dept,'routing',request_type,'','','','CONFLICTING_TICKET_TYPE_IDS',actual=','.join(map(str,tids)))
                continue
            ticket_id = tids[0]
            if ticket_id not in category_cache:
                try:
                    category_cache[ticket_id] = get_page_all(session, base, 'categories',
                              {'ticketTypeId': ticket_id, 'includeInactive': 'false'})
                except Exception as exc:
                    report(dept,'api',request_type,'','','','API_ERROR',info=f'categories: {type(exc).__name__} {str(exc)[:160]}')
                    continue
            categories = category_cache[ticket_id]
            for category_name, subcat_list in CATEGORIES[dept].items():
                eligible = [sub for sub in subcat_list if request_type in SUBCATEGORY_REQUEST_TYPES.get(dept, {}).get(category_name, {}).get(sub, [])]
                if not eligible:
                    continue
                matched = candidates(category_name, categories)
                if len(matched) != 1:
                    report(dept,'category',request_type,'',category_name,'', 'MISSING' if not matched else 'AMBIGUOUS',
                           expected=category_name,actual=' | '.join(x.get('name','') for x in matched))
                    continue
                c = matched[0]
                category_status = 'EXACT' if str(c.get('name','')).strip().casefold()==category_name.casefold() else 'ALIAS'
                report(dept,'category',request_type,'',category_name,'',category_status,
                       expected=category_name,actual=c.get('name',''),sep_id=c.get('id',''))
                cid = c['id']
                if cid not in subcategory_cache:
                    try:
                        subcategory_cache[cid] = get_page_all(session, base, 'subcategories',
                                              {'categoryId': cid, 'includeInactive': 'false'})
                    except Exception as exc:
                        report(dept,'api',request_type,'',category_name,'','API_ERROR',info=f'subcategories: {type(exc).__name__} {str(exc)[:160]}')
                        continue
                for sub in eligible:
                    hit = candidates(sub, subcategory_cache[cid])
                    if not hit:
                        status, actual, value = 'MISSING','', ''
                    elif len(hit)>1:
                        status,actual,value='AMBIGUOUS',' | '.join(x.get('name','') for x in hit),''
                    else:
                        value=hit[0].get('id','')
                        actual=hit[0].get('name','')
                        status='EXACT' if actual.strip().casefold()==sub.casefold() else 'ALIAS'
                    report(dept,'subcategory',request_type,'',category_name,sub,status,expected=sub,actual=actual,sep_id=value)
            for r in ritems:
                report(dept,'routing',request_type,str(r['Location']),'','','CONFIGURED',
                       expected=str(r['Group Name']),sep_id=r['Group ID'],
                       info='Workbook only; group/location IDs NOT verified against SEP')
    outdir = Path(args.output).resolve()
    outdir.mkdir(parents=True,exist_ok=True)
    file = outdir / 'sep_mapping_audit.csv'
    with file.open('w',encoding='utf-8-sig',newline='') as fh:
        writer=csv.DictWriter(fh,fieldnames=['department','kind','request_type','location','category','subcategory','status','darpan_value','sep_value','sep_id','detail'])
        writer.writeheader()
        writer.writerows(output)
    from collections import Counter
    totals = Counter(x['status'] for x in output)
    print('Read-only audit complete. Departments:', ', '.join(departments))
    print('Results:', dict(sorted(totals.items())))
    print('Report:', file)
    print('Note: Resolver group and location IDs are workbook-only; this script does not validate them against SEP.')


def main():
    p=argparse.ArgumentParser(description='Read-only Service Excellence category mapping audit')
    scope=p.add_mutually_exclusive_group(required=True)
    scope.add_argument('--department', help='Audit one department, e.g. Admin')
    scope.add_argument('--all',action='store_true',help='Audit all matching catalog/routing departments (can issue many GET requests)')
    p.add_argument('--output',default='sep_audit_results',help='Output folder for CSV')
    args=p.parse_args()
    run(args)

if __name__=='__main__':
    main()
