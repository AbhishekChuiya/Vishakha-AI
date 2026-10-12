"""Safely update ONLY the V1 subcategory intent-routing block in existing orchestrator.py.
Run from Darpan project root; backs up the original. Idempotent.
"""
from pathlib import Path
from datetime import datetime
import shutil
import re

path = Path.cwd() / 'ai' / 'agent' / 'orchestrator.py'
if not path.is_file():
    raise SystemExit(f'Cannot find {path}; run from Darpan project root')
src = path.read_text(encoding='utf-8')
start_marker = '        # DARPAN SUBCATEGORY ANALYTICS ROUTE V1\n'
end_marker = '            # Company-wide category rankings (previously restricted to IT/HR/Admin).\n'
if src.count(start_marker) != 1 or src.count(end_marker) != 1:
    raise SystemExit('Expected single V1 routing block not found. No changes made; upload your current orchestrator.py.')
start = src.index(start_marker)
end = src.index(end_marker, start)
replacement = '''        # DARPAN SUBCATEGORY ANALYTICS ROUTE V2
        # Resolve unique category names even when user omits department.
        # Prefer longest matching category: Finance / Financial Control is ambiguous
        # with substring matching; Financial Control is the intended category.
        if not re.search(r"\\b[A-Z][A-Z0-9]{1,15}-\\d{2,}\\b", user_message, re.I) and not re.search(
            r"\\b(?:create|raise|submit|delete|modify|update|assign)\\s+(?:an?\\s+)?(?:new\\s+)?(?:ticket|request)\\b",
            message_lower,
        ):
            from ai.agent.catalog import CATEGORIES
            alias_patterns = (
                ("IT Department", r"\\b(?:it|information technology)(?:\\s+department)?\\b"),
                ("HR Department", r"\\b(?:hr|human resources)(?:\\s+department)?\\b"),
                ("Admin", r"\\b(?:admin|administration)(?:\\s+department)?\\b"),
                ("Safety", r"\\bsafety\\b"),
                ("Security", r"\\bsecurity\\b"),
                ("Branding", r"\\bbranding\\b"),
                ("Insurance", r"\\binsurance\\b"),
                ("Finance", r"\\bfinance\\b"),
                ("Compliance & Risk", r"\\b(?:compliance(?:\\s+(?:and|&)\\s+risk)?|risk compliance)\\b"),
                ("Projects", r"\\bprojects\\b"),
                ("Quality management", r"\\bquality(?:\\s+management)?\\b"),
                ("Strategy", r"\\bstrategy\\b"),
            )
            analytics_dept = next((name for name, pattern in alias_patterns
                                   if re.search(pattern, message_lower)), None)
            has_subcat = bool(re.search(r"\\bsubcategor(?:y|ies)\\b|\\bsub[- ]categor(?:y|ies)\\b", message_lower))
            has_report = bool(re.search(r"\\b(?:top|highest|most|rank|ranking|report|analysis|analytics|breakdown|summary|show|list|which|compare)\\b", message_lower))

            # Recognize a uniquely named category in the absence of a department.
            if has_subcat and has_report and not analytics_dept:
                across = [(dept, cat) for dept, cats in CATEGORIES.items()
                          for cat in cats if re.search(r"(?<!\\w)" + re.escape(cat.casefold()) + r"(?!\\w)", message_lower.casefold())]
                if across:
                    longest = max(len(cat) for _, cat in across)
                    strongest = [(dept, cat) for dept, cat in across if len(cat) == longest]
                    if len(strongest) == 1:
                        analytics_dept = strongest[0][0]

            if analytics_dept and has_subcat and has_report:
                matches = [name for name in CATEGORIES.get(analytics_dept, {})
                           if re.search(r"(?<!\\w)" + re.escape(name.casefold()) + r"(?!\\w)", message_lower.casefold())]
                chosen_category = None
                if matches:
                    longest = max(len(name) for name in matches)
                    best = [name for name in matches if len(name) == longest]
                    if len(best) == 1:
                        chosen_category = best[0]
                top_match = re.search(r"\\btop\\s+(\\d{1,2})\\b", message_lower)
                return {
                    "intent": "ANALYZE_TICKETS", "analytics_department": analytics_dept,
                    "analytics_view": "SUBCATEGORY_RANKING",
                    "analytics_category": chosen_category,
                    "analytics_sort": "non_closed" if re.search(r"\\b(?:open|pending|backlog|active|unresolved|non[- ]closed)\\b", message_lower) else "total",
                    "analytics_limit": min(50, int(top_match.group(1))) if top_match else 10,
                    "missing_fields": [],
                }
'''
updated = src[:start] + replacement + src[end:]
compile(updated, str(path), 'exec')
if updated == src:
    print('No changes required.')
else:
    backup = path.with_name(path.name + '.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    shutil.copy2(path, backup)
    path.write_text(updated, encoding='utf-8')
    print('Updated:', path)
    print('Backup:', backup)
