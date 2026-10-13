"""Read-only follow-up for Phase 3B missing SEP mappings. No API write calls.

Run from Darpan project root:
  python tools/diagnose_sep_missing.py
Optional: --input sep_audit_results/sep_mapping_audit.csv --output sep_audit_results
"""
import argparse
import csv
import difflib
import os
import re
import sys
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def normalize(value):
    s = unicodedata.normalize('NFKC', str(value or '')).casefold()
    s = re.sub(r'\s*&\s*', ' and ', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def rank_candidates(name, items, limit=5):
    scored = []
    needle = normalize(name)
    for item in items:
        title = str(item.get('name') or '')
        candidate = normalize(title)
        score = difflib.SequenceMatcher(None, needle, candidate).ratio()
        if needle and candidate and (needle in candidate or candidate in needle):
            score = max(score, 0.85)
        scored.append((score, item))
    return [item for _, item in sorted(scored, key=lambda x: x[0], reverse=True)[:limit]]


def check_routing(rows):
    by_key = defaultdict(set)
    invalid = []
    for row in rows:
        key = (str(row.get('Department') or '').strip(), str(row.get('Ticket Type') or '').strip(), str(row.get('Location') or '').strip())
        group = str(row.get('Group Name') or '').strip()
        gid = row.get('Group ID')
        tid = row.get('Ticket Id')
        if not all(key) or not group or not isinstance(gid, int) or not isinstance(tid, int):
            invalid.append((*key, 'INCOMPLETE', group, str(gid), str(tid)))
        by_key[key].add((group, str(gid), str(tid)))
    for key, values in by_key.items():
        if len(values) > 1:
            invalid.append((*key, 'CONFLICT', ' | '.join(map(str, sorted(values))), '', ''))
    return invalid


def run(opts):
    from dotenv import load_dotenv
    import requests
    from tools.audit_sep_mappings import get_page_all, route_rows
    load_dotenv(ROOT / '.env')
    base = os.getenv('TICKETING_BASE_URL', '').rstrip('/')
    token = os.getenv('TICKETING_PAT', '')
    if not base.startswith('https://') or not token:
        raise RuntimeError('Project .env must contain HTTPS TICKETING_BASE_URL and TICKETING_PAT')
    source = Path(opts.input)
    if not source.is_absolute():
        source = ROOT / source
    if not source.is_file():
        raise FileNotFoundError(f'Missing earlier audit CSV: {source}')
    with source.open(encoding='utf-8-sig', newline='') as handle:
        missing = [r for r in csv.DictReader(handle) if r.get('status') == 'MISSING']
    routes = list(route_rows(ROOT / 'data' / 'ticket_routing.xlsx'))
    ticket_ids = defaultdict(set)
    for row in routes:
        ticket_ids[(str(row['Department']).strip(), str(row['Ticket Type']).strip())].add(row['Ticket Id'])
    session = requests.Session()
    session.headers.update({'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
    cache = {}
    def fetch(kind, params):
        key = (kind, tuple(sorted(params.items())))
        if key not in cache:
            cache[key] = get_page_all(session, base, kind, params)
        return cache[key]

    output = []
    for entry in missing:
        dept, req, kind = entry['department'], entry['request_type'], entry['kind']
        source_name = entry['darpan_value']
        ids = ticket_ids.get((dept, req), set())
        base_row = dict(department=dept, request_type=req, kind=kind,
                        category=entry['category'], subcategory=entry['subcategory'],
                        darpan_value=source_name)
        def emit(status, suggestion='', sep_id='', score='', notes=''):
            output.append({**base_row, 'diagnosis':status, 'candidate':suggestion,
                           'candidate_id':sep_id, 'similarity':score, 'notes':notes})
        if len(ids) != 1 or not isinstance(next(iter(ids), None), int):
            emit('ROUTING_ID_UNRESOLVED', notes='No unique numeric ticket type ID in routing workbook')
            continue
        tid = next(iter(ids))
        try:
            active_categories = fetch('categories', {'ticketTypeId':tid,'includeInactive':'false'})
            all_categories = fetch('categories', {'ticketTypeId':tid,'includeInactive':'true'})
            if kind == 'category':
                active, full = active_categories, all_categories
            else:
                parents = [c for c in all_categories if normalize(c.get('name')) == normalize(entry['category'])]
                if len(parents) != 1 or parents[0].get('id') is None:
                    emit('PARENT_CATEGORY_UNRESOLVED',notes='Parent category absent or ambiguous in SEP')
                    continue
                cid = parents[0]['id']
                active = fetch('subcategories', {'categoryId':cid,'includeInactive':'false'})
                full = fetch('subcategories', {'categoryId':cid,'includeInactive':'true'})
            exact_full = [x for x in full if normalize(x.get('name')) == normalize(source_name)]
            exact_active = [x for x in active if normalize(x.get('name')) == normalize(source_name)]
            if len(exact_active) == 1:
                match = exact_active[0]
                emit('NOW_FOUND', match.get('name',''), match.get('id',''), '1.000', 'Recheck initial audit')
            elif len(exact_full) == 1 and not exact_active:
                match = exact_full[0]
                emit('ONLY_IN_INACTIVE_QUERY',match.get('name',''),match.get('id',''),'1.000', 'Check active flag and SEP configuration; do not auto-enable')
            elif len(exact_full) > 1:
                emit('AMBIGUOUS',notes='Multiple normalized exact matches; requires manual resolution')
            else:
                candidates = rank_candidates(source_name, full)
                if not candidates:
                    emit('NO_CANDIDATES',notes='No results in SEP lookup; check parent/request type and SEP configuration')
                for item in candidates:
                    ratio = difflib.SequenceMatcher(None, normalize(source_name), normalize(item.get('name'))).ratio()
                    emit('REVIEW_CANDIDATE',item.get('name',''),item.get('id',''),f'{ratio:.3f}',
                         'Suggestion only; verify manually before changing the catalog')
        except Exception as exc:
            emit('API_ERROR',notes=f'{type(exc).__name__}: {str(exc)[:130]}')

    out_dir = Path(opts.output)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / 'sep_missing_diagnostics.csv'
    headers = ['department','request_type','kind','category','subcategory','darpan_value','diagnosis','candidate','candidate_id','similarity','notes']
    with dest.open('w',encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f,fieldnames=headers);writer.writeheader();writer.writerows(output)
    conflicts = check_routing(routes)
    route_dest = out_dir / 'routing_consistency.csv'
    with route_dest.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['department','request_type','location','issue','group','group_id','ticket_type_id']);writer.writerows(conflicts)
    print(f'Original missing entries: {len(missing)}')
    print(f'Diagnostic rows: {len(output)}; summary: {dict(Counter(r["diagnosis"] for r in output))}')
    print(f'Workbook routing issues: {len(conflicts)} (not live group-ID verification)')
    print(f'Diagnostic CSV: {dest}')
    print(f'Routing CSV: {route_dest}')
    print('No tickets created; IDs in candidates are suggestions only. Review before modifying catalog.')


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',default='sep_audit_results/sep_mapping_audit.csv')
    ap.add_argument('--output',default='sep_audit_results')
    run(ap.parse_args())
