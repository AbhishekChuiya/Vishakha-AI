"""Read-only Phase 3D audit of Darpan Excel routing definitions.

Does not call a write API, change files in the project, or assert live SEP group validity.
Optional --sep-groups accepts an administrator-provided CSV export with columns id,name
for positive verification of routing group IDs/names.
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def normalize(value):
    return ' '.join(str(value or '').lower().strip().split())


def check_rows(rows, sep_groups=None):
    output = []
    pairs = defaultdict(list)
    id_names = defaultdict(set)
    name_ids = defaultdict(set)
    for row_index, row in enumerate(rows, start=2):
        dept = str(row.get('Department') or '').strip()
        req = str(row.get('Ticket Type') or '').strip()
        location = str(row.get('Location') or '').strip()
        group = str(row.get('Group Name') or '').strip()
        gid = str(row.get('Group ID') or '').strip()
        tid = str(row.get('Ticket Id') or '').strip()
        rec = dict(row_number=row_index, department=dept, request_type=req, location=location,
                   group_name=group, group_id=gid, ticket_type_id=tid, status='', detail='')
        for field in ('department','request_type','location','group_name','group_id','ticket_type_id'):
            if not rec[field]:
                output.append({**rec,'status':'MISSING_FIELD','detail':f'Missing {field}'})
        if gid and not gid.isdigit() or tid and not tid.isdigit():
            output.append({**rec, 'status':'NON_NUMERIC_ID','detail':'Group ID or ticket type ID is not numeric'})
        pairs[(normalize(dept),normalize(req),normalize(location))].append(rec)
        if gid and group:
            id_names[gid].add(normalize(group))
            name_ids[(normalize(dept),normalize(group))].add(gid)
        if sep_groups is not None and gid:
            actual = sep_groups.get(gid)
            if actual is None:
                output.append({**rec, 'status':'SEP_ID_NOT_FOUND', 'detail':'ID absent from supplied SEP groups export'})
            elif normalize(actual) != normalize(group):
                output.append({**rec, 'status':'SEP_NAME_DIFFERS', 'detail':f'SEP group name: {actual}'})
            else:
                output.append({**rec, 'status':'SEP_VERIFIED_FROM_EXPORT', 'detail':'ID/name matched supplied SEP group export'})
    for group_id,names in id_names.items():
        if len(names)>1:
            for row in rows:
                if str(row.get('Group ID') or '').strip()==group_id:
                    output.append(dict(row_number='',department=row.get('Department',''),request_type=row.get('Ticket Type',''),location=row.get('Location',''),group_name=row.get('Group Name',''),group_id=group_id,ticket_type_id=row.get('Ticket Id',''),status='SAME_ID_MULTIPLE_NAMES',detail=f'Group ID {group_id} appears with {len(names)} names'))
    for key, ids in name_ids.items():
        if len(ids)>1:
            output.append(dict(row_number='',department=key[0],request_type='',location='',group_name=key[1],group_id=' | '.join(sorted(ids)),ticket_type_id='',status='SAME_NAME_MULTIPLE_IDS',detail='Check retired/duplicate SEP groups'))
    for key, matches in pairs.items():
        distinct = {(r['group_id'],r['group_name'],r['ticket_type_id']) for r in matches}
        if len(distinct) <= 1:
            continue
        is_it = key[0]=='it department'
        for r in matches:
            output.append({**r,'status':'SPECIALIST_GROUP_SELECTION_REQUIRED' if is_it else 'AMBIGUOUS_ROUTING_KEY',
                           'detail':f'{len(distinct)} choices for same department/request/location; requires verified routing rule'+(' (may be intentional application-specific routing)' if is_it else '')})
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sep-groups',type=Path,help='Optional, read-only SEP group export CSV with id,name columns')
    parser.add_argument('--output',type=Path,default=ROOT/'sep_audit_results'/'sep_group_routing_audit.csv')
    args=parser.parse_args()
    from tools.audit_sep_mappings import route_rows
    workbook=ROOT/'data'/'ticket_routing.xlsx'
    rows=list(route_rows(workbook))
    groups=None
    if args.sep_groups:
        with args.sep_groups.open(encoding='utf-8-sig', newline='') as f:
            reader=csv.DictReader(f)
            if not {'id','name'}.issubset(set(reader.fieldnames or [])):
                parser.error('SEP group export must have id,name columns')
            groups={str(r['id']).strip():str(r['name']).strip() for r in reader}
    findings=check_rows(rows,groups)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fields=['row_number','department','request_type','location','group_name','group_id','ticket_type_id','status','detail']
    with args.output.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader();writer.writerows(findings)
    from collections import Counter
    print('Routing workbook rows:',len(rows))
    print('Audit findings:',dict(Counter(r['status'] for r in findings)))
    print('Output:',args.output.resolve())
    print('Live SEP groups verified:', 'only against user-provided export' if groups is not None else 'NO — provide --sep-groups export to verify IDs')
    print('No tickets created or changed.')

if __name__=='__main__':
    main()
