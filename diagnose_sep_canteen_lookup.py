"""Read-only SEP catalog diagnostics; run from your Django project root."""
import json
import requests
from integrations.ticketing.client import TicketingClient

TICKET_TYPE_ID = 11
CATEGORY = 'Canteen Management'
SUBCATEGORY = 'Feedback and Grievances'

client = TicketingClient()
base = client.base_url.rstrip('/') + '/api/itsm/v1/lookup/'
headers = {'Authorization': f'Bearer {client.pat}', 'Accept': 'application/json'}

def query(kind, params, tag):
    try:
        r = requests.get(base + kind, headers=headers, params=params, timeout=30)
        print(f'\n{tag} HTTP {r.status_code}')
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            print('response keys:', sorted(data.keys()))
            results = data.get('content')
            if results is None:
                print('NO content array; inspect API response structure with provider')
                print('types:', {k: type(v).__name__ for k,v in data.items()})
                return []
        elif isinstance(data, list):
            results = data
            print('response was a list, not a content object')
        else:
            print('unexpected response type:', type(data).__name__)
            return []
        print('count in response:', len(results))
        print('items (id, name, active):', [(x.get('id'), x.get('name'), x.get('active', '?')) for x in results[:30] if isinstance(x,dict)])
        return results
    except requests.HTTPError as e:
        print('HTTP error:', e)
    except (requests.RequestException, ValueError) as e:
        print('Lookup failed:', type(e).__name__, str(e)[:200])
    return []

cats = query('categories', {'ticketTypeId': TICKET_TYPE_ID, 'search': CATEGORY, 'includeInactive': 'false', 'size': 100}, 'CATEGORY SEARCH')
match = next((x for x in cats if isinstance(x,dict) and str(x.get('name','')).strip().casefold() == CATEGORY.casefold()), None)
if match:
    cid = match['id']
    print('CATEGORY MATCH ID:', cid)
    query('subcategories', {'categoryId': cid, 'search': SUBCATEGORY, 'includeInactive': 'false', 'size': 100}, 'SUBCATEGORY SEARCH')
    query('subcategories', {'categoryId': cid, 'includeInactive': 'false', 'size': 100}, 'SUBCATEGORY LIST WITHOUT SEARCH')
else:
    print('CATEGORY EXACT MATCH MISSING; cannot safely lookup subcategories.')
print('\nRead-only diagnostics complete. Do not share your PAT, requester email, or .env file.')
