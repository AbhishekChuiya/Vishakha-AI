"""Conservative, offline interpretation of common SEP employee shorthand.

Only return an intent when the employee's wording clearly indicates a read-only
lookup, a newly reported IT issue, or an explicit ticket creation request.
Never choose SEP catalog IDs, request types, groups, locations or priorities.
"""
import re
import unicodedata


def _norm(text):
    value = unicodedata.normalize('NFKC', str(text or '')).casefold()
    value = value.replace('वाई-फाई', 'wifi').replace('वाइफाइ', 'wifi')
    return re.sub(r'\s+', ' ', value).strip()


def classify_employee_shorthand(message):
    text = _norm(message)
    if not text:
        return None

    # Don't hijack unrelated tasks or HR requests: there is currently no
    # PeopleStrong integration for leave or attendance operations.
    if re.search(r'\b(?:leave|chutti|chhutti|attendance|salary|payslip|holiday)\b|छुट्टी|वेतन|हाजिरी', text):
        return None

    ticket = bool(re.search(r'\b(?:ticket|tickets|tiket|tikket)\b|टिकट', text))
    mine = bool(re.search(r'\b(?:my|mine|mera|mere|meri|mujhe|meri|apna|apne)\b|मेरे|मेरा|मेरी|मुझे', text))
    lookup = bool(re.search(r'\b(?:dikhao|dikhaao|dikha|dikhana|batao|bataiye|btao|show|list|find|search|check|track|dekhna|dekho|dikhao|status|sts|kitne)\b|दिखाओ|दिखाइए|दिखाएं|बताओ|देखना|स्थिति|स्टेटस|कितने', text))
    count = bool(re.search(r'\b(?:kitne|count|how many|number of)\b|कितने', text))
    status = bool(re.search(r'\b(?:open|pending|resolved|closed|cancelled|canceled)\b|खुले|लंबित', text))
    status_filter = next((s.upper() for s in ('open', 'pending', 'resolved', 'closed', 'cancelled') if re.search(r'\b'+s+r'\b', text)), None)

    # Phrases like "mera ticket", "mere ticket dikhao", "my tckt".
    if (ticket and mine and (lookup or count or status or len(text.split()) <= 4)) or (ticket and lookup and re.search(r'\b(?:my|mine|mera|meri|mere)\b|मेरे|मेरा|मेरी', text)):
        return {
            'intent': 'SEARCH_TICKETS', 'ticket_number': None,
            'ticket_query': None, 'search_query': None,
            'search_scope': 'MY_TICKETS', 'ticket_count_only': bool(count),
            'ticket_status_filter': status_filter, 'missing_fields': [],
        }

    # Clear new IT incidents in natural employee language. Issue vocabulary is
    # deliberately limited: no department guess for generic "issue" or "problem".
    device = re.search(r'\b(?:laptop|laptp|laptob|computer|desktop|pc|printer|keyboard|keybord|mouse|monitor|wifi|wi-fi|network|netwrk|internet|vpn)\b|लैपटॉप|कंप्यूटर|प्रिंटर|कीबोर्ड|इंटरनेट|नेटवर्क', text)
    problem = re.search(r'\b(?:kharab|khrab|band|nahi|nahin|nhi|not|broken|issue|problem|repair|fix|slow|down|disconnected|working|chalta|chal|connect|fault|damage|stuck|hang|error)\b|खराब|नहीं|बंद|समस्या|दिक्कत|चल|काम', text)
    ticket_request = re.search(r'\b(?:create|raise|make|open|log|submit|banao|bana|banado|banana|banaye|banaiye|karo|karna)\b|बनाओ|बनाना|बनाइए|बना दो|दर्ज', text)

    # Avoid conflating read-only searches about IT issues with requests to create.
    if device and ((problem and not (lookup and ticket and not ticket_request)) or (ticket and ticket_request)):
        return {
            'intent': 'CREATE_TICKET', 'department': 'IT Department',
            'request_type': None, 'category': None,
            'description': str(message or '').strip(),
            'location': None, 'priority': None, 'ticket_number': None,
            'missing_fields': [],
        }

    # Explicit ticket creation without department should ask employee to choose.
    # Don't mistake "ticket create hua?" for a new ticket request.
    if ticket and ticket_request and not re.search(r'\b(?:hua|huya|ho gaya|already|existing)\b|बन गया', text):
        department = None
        if re.search(r'\b(?:it department|it support)\b|आईटी', text):
            department = 'IT Department'
        return {
            'intent': 'CREATE_TICKET', 'department': department,
            'request_type': None, 'category': None,
            'description': str(message or '').strip(),
            'location': None, 'priority': None, 'ticket_number': None,
            'missing_fields': [],
        }

    return None
