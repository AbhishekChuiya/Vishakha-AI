"""Conservative normalization of answers to an *existing* SEP workflow question.

This is intentionally not an intent engine. Values must be matched against
configured options; ambiguous site references are left for the normal prompt.
"""
import re
import unicodedata


def _fold(text):
    value = unicodedata.normalize('NFKC', str(text or '')).casefold().strip()
    return re.sub(r'\s+', ' ', value)


def _matching_option(value, allowed):
    folded = _fold(value)
    matches = [candidate for candidate in allowed if _fold(candidate) == folded]
    return matches[0] if len(matches) == 1 else None


def normalize_pending_answer(field, answer, *, departments=(), request_types=(),
                             categories=(), subcategories=(), locations=()):
    """Return a configured canonical answer, or the original text for validation.

    Never choose between multiple locations, category IDs or ticket types.
    """
    original = str(answer or '').strip()
    folded = _fold(original)
    if not original:
        return original

    if field == 'priority':
        cleaned = re.sub(r'[.!?]+$', '', folded).strip()
        # Require a standalone level, optionally with a clearly priority-related word.
        match = re.fullmatch(r'(?:(?:set|make|keep|choose|select|please|priority|is|it|to|as|ko|rakho|kar\s+do)\s+)*(high|medium|low)(?:\s+(?:priority|prio|hai|rakhna|rakho|kar\s+do))?', cleaned)
        if match:
            return match.group(1).title()
        if cleaned in {'उच्च', 'ज्यादा', 'हाई'}:
            return 'High'
        if cleaned in {'मध्यम', 'मीडियम'}:
            return 'Medium'
        if cleaned in {'कम', 'लो'}:
            return 'Low'
        return original

    candidates = {
        'department': departments,
        'request_type': request_types,
        'category': categories,
        'subcategory': subcategories,
        'location': locations,
    }.get(field)
    if candidates is None:
        return original

    exact = _matching_option(original, candidates)
    if exact:
        return exact

    if field == 'request_type':
        short_names = {'incident': 'Incident Request', 'service': 'Service Request'}
        target = short_names.get(folded)
        if target:
            return _matching_option(target, candidates) or original

    if field == 'department':
        target = {'it': 'IT Department', 'it dept': 'IT Department',
                  'hr': 'HR Department', 'hr dept': 'HR Department'}.get(folded)
        if target:
            return _matching_option(target, candidates) or original

    if field == 'location':
        # Only resolve a site nickname if exactly one configured site matches.
        cleaned = re.sub(r'\b(?:at|in|from|plant|office|location|site|mera|meri|hai|the|please)\b', ' ', folded)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if not cleaned:
            return original
        exact = _matching_option(cleaned, candidates)
        if exact:
            return exact
        # Match distinctive names as whole words. "Mundra" intentionally
        # matches multiple sites and therefore remains a clarification.
        matches = [loc for loc in candidates if re.search(r'(?<!\w)' + re.escape(cleaned) + r'(?!\w)', _fold(loc))]
        if len(matches) == 1:
            return matches[0]

    return original
