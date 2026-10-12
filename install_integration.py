"""Run from Darpan project root. Safely patch only analytics routing in existing files."""
from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path.cwd()
FILES = [ROOT / 'ai/agent/orchestrator.py', ROOT / 'ai/agent/workflow.py']
for path in FILES:
    if not path.is_file():
        raise SystemExit(f'Missing {path}; run from Darpan project root')

orchestrator_path, workflow_path = FILES
orch = orchestrator_path.read_text(encoding='utf-8')
flow = workflow_path.read_text(encoding='utf-8')
ORCH_MARK = '        # DARPAN SUBCATEGORY ANALYTICS ROUTE V1\n'
FLOW_MARK = '        # DARPAN SUBCATEGORY ANALYTICS HANDLER V1\n'

orch_block = '''        # DARPAN SUBCATEGORY ANALYTICS ROUTE V1
        # Read-only department category/subcategory rankings never reach the LLM.
        # Reuse configured catalog names, not guessed portal IDs.
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
            if analytics_dept and has_subcat and has_report:
                matches = [name for name in CATEGORIES.get(analytics_dept, {})
                           if re.search(r"(?<!\\w)" + re.escape(name.casefold()) + r"(?!\\w)", message_lower.casefold())]
                chosen_category = matches[0] if len(matches) == 1 else None
                top_match = re.search(r"\\btop\\s+(\\d{1,2})\\b", message_lower)
                return {
                    "intent": "ANALYZE_TICKETS", "analytics_department": analytics_dept,
                    "analytics_view": "SUBCATEGORY_RANKING",
                    "analytics_category": chosen_category,
                    "analytics_sort": "non_closed" if re.search(r"\\b(?:open|pending|backlog|active|unresolved|non[- ]closed)\\b", message_lower) else "total",
                    "analytics_limit": min(50, int(top_match.group(1))) if top_match else 10,
                    "missing_fields": [],
                }
            # Company-wide category rankings (previously restricted to IT/HR/Admin).
            category_report = bool(re.search(
                r"\\b(?:top\\s*\\d*|highest|most|rank|ranking|category[- ]wise|by category|category breakdown|categories breakdown|category analytics|category report|category summary)\\b",
                message_lower,
            ))
            if (analytics_dept and category_report and not has_subcat
                    and re.search(r"\\b(?:categor(?:y|ies)|tickets?)\\b", message_lower)):
                return {
                    "intent": "ANALYZE_TICKETS", "analytics_department": analytics_dept,
                    "analytics_view": "CATEGORY_RANKING",
                    "analytics_sort": "non_closed" if re.search(r"\\b(?:open|pending|backlog|active|unresolved|non[- ]closed)\\b", message_lower) else "total",
                    "missing_fields": [],
                }

'''

flow_block = '''        # DARPAN SUBCATEGORY ANALYTICS HANDLER V1
        # This code is inside handle_ticket_analytics, AFTER its email allowlist.
        if agent_result.get("analytics_view") == "SUBCATEGORY_RANKING":
            category = agent_result.get("analytics_category")
            if not category:
                return {"type": "message", "message":
                        f"Please specify a {department} category for subcategory analysis. "
                        f"Available categories: {', '.join(__import__('ai.agent.catalog', fromlist=['CATEGORIES']).CATEGORIES.get(department, {}))}."}
            try:
                from ai.analytics.category_analytics import get_subcategory_ranking
                report = get_subcategory_ranking(
                    self.ticketing, department, config["ticket_type_ids"], category,
                    sort_by=agent_result.get("analytics_sort", "total"),
                    limit=agent_result.get("analytics_limit", 10),
                )
                return {"type": "category_analytics", "analytics": report,
                        "message": f"{department} / {category} subcategory ranking"}
            except Exception as exc:
                print("SUBCATEGORY ANALYTICS ERROR:", type(exc).__name__, str(exc))
                return {"type": "error", "message": "Subcategory analytics could not be retrieved. Check the server logs."}

'''
if ORCH_MARK not in orch:
    anchor = '        message_lower = user_message.lower().strip()\n'
    if orch.count(anchor) < 1:
        raise SystemExit('Orchestrator routing anchor missing; no files changed')
    orch = orch.replace(anchor, anchor + '\n' + orch_block, 1)
if FLOW_MARK not in flow:
    anchor = '        if agent_result.get("analytics_view") == "CATEGORY_RANKING":\n'
    if flow.count(anchor) != 1:
        raise SystemExit('Workflow analytics anchor missing or duplicated; no files changed')
    flow = flow.replace(anchor, flow_block + anchor, 1)

for path, code in [(orchestrator_path, orch), (workflow_path, flow)]:
    compile(code, str(path), 'exec')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for path, code in [(orchestrator_path, orch), (workflow_path, flow)]:
    if path.read_text(encoding='utf-8') == code:
        print('Already integrated:', path)
        continue
    backup = path.with_name(path.name + '.backup_' + stamp)
    shutil.copy2(path, backup)
    path.write_text(code, encoding='utf-8')
    print('Updated:', path, '\nBackup:', backup)
print('Routing integration complete. Verify authorization settings and run Django checks.')
