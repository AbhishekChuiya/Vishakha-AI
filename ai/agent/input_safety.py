"""Deterministic guardrails for user-provided ticket descriptions.

Never derive ticket facts from a bare creation instruction.
"""
import re

_GENERIC = re.compile(r"^\s*(?:(?:please|kindly)\s+)?(?:i\s+(?:want|need|would like)\s+to\s+)?(?:create|raise|submit|open|log|file)\s+(?:me\s+|an?\s+|the\s+|new\s+|my\s+)*(?:(?:it|hr|admin|finance|safety|security|branding|insurance|service excellence|sep)\s+)?(?:(?:incident|service)\s+)?(?:ticket|request)(?:\s+(?:for|in|under)\s+(?:(?:the\s+)?(?:it|hr|admin|finance|safety|security|branding|insurance|service excellence|sep)(?:\s+department)?))?\s*[.!?]*\s*$", re.I)

def meaningful_description(value):
    """Return employee-authored requirement or None for generic commands.

    Preserve all actual user text; a separate model may suggest a category,
    but it must never supply a missing description.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or _GENERIC.fullmatch(text):
        return None
    return text
