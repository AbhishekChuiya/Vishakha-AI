"""Apply minimal ticket-command routing fix to current Darpan orchestrator."""
from pathlib import Path
from datetime import datetime
import ast
import shutil

root = Path(__file__).resolve().parent
file = root / 'ai' / 'agent' / 'orchestrator.py'
source = file.read_text(encoding='utf-8-sig')
marker = '        # DARPAN EXPLICIT TICKET COMMAND ROUTE V1'
if marker in source:
    print('Already installed; no changes needed.')
    raise SystemExit(0)
anchor = '        system_prompt = """\n'
if source.count(anchor) != 1:
    raise RuntimeError('Cannot safely find unique installation anchor; no files changed.')
patch = '''        # DARPAN EXPLICIT TICKET COMMAND ROUTE V1
        # Avoid truncated model JSON for unambiguous requests to create a ticket.
        # Only explicit ticket commands starting the message are handled here.
        explicit_ticket_command = bool(
            re.match(r"^\\s*(?:please\\s+)?(?:create|raise|submit|log|open|file)\\b", message_lower)
            and re.search(r"\\btickets?\\b", message_lower)
        )
        if explicit_ticket_command and not ticket_number_matches:
            # Infer only when the domain is explicit; otherwise let the form
            # ask for department. Request type remains employee-selected.
            explicit_dept = None
            if re.search(
                r"\\b(?:laptop|desktop|computer|keyboard|mouse|monitor|printer|"
                r"wi-?fi|internet|network|hardware|software|sap|odoo)\\b",
                message_lower,
            ) or re.search(r"\\bit\\s+(?:department\\s+)?tickets?\\b", message_lower):
                explicit_dept = "IT Department"
            return {
                "intent": "CREATE_TICKET",
                "department": explicit_dept,
                "request_type": None,
                "category": None,
                "description": user_message.strip(),
                "location": None,
                "ticket_number": None,
                "ticket_query": None,
                "search_query": None,
                "search_scope": None,
                "priority": None,
                "missing_fields": [],
            }

'''
updated = source.replace(anchor, patch + anchor, 1)
ast.parse(updated, filename=str(file))
backup = file.with_name(file.name + '.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
shutil.copy2(file, backup)
file.write_text(updated, encoding='utf-8')
print('Updated:', file)
print('Backup:', backup)
