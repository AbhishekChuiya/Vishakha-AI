"""Conservative collection of SEP draft details from one free-text utterance.

Only exact/unambiguous location references and explicit priority labels are
extracted.  Never choose a department, request type, category or submission.
"""
import re
from ai.agent.followup_answers import normalize_pending_answer

PRIORITY = re.compile(r'(?<!\w)(high|medium|low)\s*(?:priority|prio)(?!\w)|(?<!\w)(?:priority\s*(?:is|:|=|to)?\s*)(high|medium|low)(?!\w)', re.I)


def extract_ticket_details(text, locations):
    original = str(text or '').strip()
    if not original:
        return {}
    result = {}
    cleaned = original
    mentions = list(PRIORITY.finditer(original))
    priorities = {next(g for g in m.groups() if g).title() for m in mentions}
    if len(priorities) == 1:
        result['priority'] = priorities.pop()
        for match in reversed(mentions):
            cleaned = cleaned[:match.start()] + ' ' + cleaned[match.end():]

    # Check canonical complete location names first, or explicit site labels.
    candidates = []
    for location in locations:
        if re.search(r'(?<!\w)' + re.escape(location) + r'(?!\w)', original, re.I):
            candidates.append((location, location))
    if not candidates:
        site_pattern = re.compile(
            r'(?<!\w)(?:ahmedabad\s+plant|ho\s+shantigram|ho\s+prahladnagar|'
            r'kolkata\s+polyfab|mundra(?:\s+(?:vgpl|vmpl)\s*[12]|\s+vrpl)?)(?!\w)', re.I)
        for match in site_pattern.finditer(original):
            label = match.group(0)
            resolved = normalize_pending_answer('location', label, locations=locations)
            if resolved in locations:
                candidates.append((label, resolved))
            else:
                # An ambiguous site must not be silently resolved.
                return {k: v for k, v in result.items() if k != 'location'}
    distinct = {canonical for _, canonical in candidates}
    if len(distinct) == 1:
        result['location'] = distinct.pop()
        for label, _ in sorted(candidates, key=lambda entry: len(entry[0]), reverse=True):
            cleaned = re.sub(r'(?<!\w)' + re.escape(label) + r'(?!\w)', ' ', cleaned, flags=re.I)
    # Explicitly do not interpret the remainder as a description if it's just a
    # command, a location, or priority text.
    cleaned = re.sub(r'\b(?:at|in|from)\s*(?=[,.;]|$)', ' ', cleaned, flags=re.I)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,.;-')
    if cleaned:
        result['remaining_text'] = cleaned
    return result
