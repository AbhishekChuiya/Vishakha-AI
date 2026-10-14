"""Read-only Darpan Phase 4A security preflight. No secrets printed."""
import ast
import json
from pathlib import Path
import re
import argparse


def inspect(root):
    findings = []
    def add(code, severity, location, detail, action):
        findings.append(dict(code=code, severity=severity, location=location, detail=detail, action=action))
    settings = root / 'config' / 'settings.py'
    views = root / 'apps' / 'assistant' / 'views.py'
    js = root / 'static' / 'js' / 'chat.js'
    if not settings.is_file():
        add('SETTINGS_MISSING', 'BLOCKER', 'config/settings.py', 'Settings not found', 'Run from the project root.')
    else:
        s = settings.read_text(encoding='utf-8-sig')
        try:
            tree = ast.parse(s)
            literals = {}
            for n in tree.body:
                if isinstance(n, ast.Assign):
                    for target in n.targets:
                        if isinstance(target, ast.Name):
                            try: literals[target.id] = ast.literal_eval(n.value)
                            except (ValueError, TypeError, SyntaxError, MemoryError): pass
            if literals.get('DEBUG') is True:
                add('DEBUG_ON', 'HIGH', 'config/settings.py', 'DEBUG set to True', 'Use DEBUG=False on deployment.')
            if isinstance(literals.get('SECRET_KEY'), str):
                add('HARDCODED_SECRET_KEY', 'CRITICAL', 'config/settings.py', 'SECRET_KEY is a literal in source; value intentionally hidden', 'Load a new production key from a protected environment variable and rotate before production.')
            if 'SECURE_SSL_REDIRECT' not in s:
                add('NO_SSL_REDIRECT', 'HIGH', 'config/settings.py', 'No HTTPS redirect setting found', 'Enable HTTPS redirect once reverse-proxy TLS is configured.')
            if 'SESSION_COOKIE_SECURE' not in s or 'CSRF_COOKIE_SECURE' not in s:
                add('INSECURE_COOKIES', 'HIGH', 'config/settings.py', 'Secure cookie flags not both configured', 'Enable both flags for HTTPS production; keep HTTP LAN development separate.')
            if 'SECURE_HSTS_SECONDS' not in s:
                add('NO_HSTS', 'MEDIUM', 'config/settings.py', 'HSTS not configured', 'Enable gradually only after validating HTTPS on all production hostnames.')
            if 'STATIC_ROOT' not in s:
                add('NO_STATIC_ROOT', 'MEDIUM', 'config/settings.py', 'STATIC_ROOT not configured', 'Configure collectstatic and web-server static serving.')
            if "sqlite3" in s:
                add('SQLITE_PROD_REVIEW', 'MEDIUM', 'config/settings.py', 'SQLite configured', 'Plan backed-up PostgreSQL and migration testing before multi-user rollout.')
        except SyntaxError:
            add('SETTINGS_SYNTAX', 'BLOCKER', 'config/settings.py', 'Cannot parse settings.py', 'Fix Python syntax.')
    if views.is_file():
        t = views.read_text(encoding='utf-8-sig')
        exempt_count = len(re.findall(r'^\s*@csrf_exempt\s*$', t, flags=re.M))
        if exempt_count:
            add('CSRF_EXEMPT_POST', 'HIGH', 'apps/assistant/views.py', f'{exempt_count} CSRF exemptions detected', 'Add CSRF tokens to same-origin JS POSTs and remove exemptions with tests.')
        if 'endswith("@gmail.com")' in t or "endswith('@gmail.com')" in t:
            add('PUBLIC_EMAIL_SIGNUP', 'HIGH', 'apps/assistant/views.py', 'Sign-up code permits Gmail addresses', 'Require managed company identity or admin-approved accounts for production.')
        if 'def signup_view' in t:
            add('OPEN_SIGNUP_REVIEW', 'MEDIUM', 'apps/assistant/views.py', 'Self-registration route exists', 'Review organization-approved registration, verification and onboarding controls.')
    else:
        add('VIEWS_MISSING', 'BLOCKER', 'apps/assistant/views.py', 'View module not found', 'Check project structure.')
    if js.is_file():
        t = js.read_text(encoding='utf-8-sig')
        if 'crypto.randomUUID()' in t:
            add('RANDOMUUID_HTTP_REVIEW', 'MEDIUM', 'static/js/chat.js', 'crypto.randomUUID() occurs in JS', 'Verify secure-context fallback on tablet; avoid overwriting the working tablet fix.')
        if not re.search(r'X-CSRFToken|X-CSRF-Token', t, flags=re.I):
            add('JS_CSRF_HEADERS', 'HIGH', 'static/js/chat.js', 'No CSRF request headers found', 'Attach CSRF token to every mutating AJAX request before removing exemptions.')
    add('LIVE_AUTHORIZATION', 'VERIFY', 'SEP API', 'Cannot prove requester and actor authorization from static inspection', 'Test user-to-user isolation and server-derived actor identity against live SEP.')
    add('EXTERNAL_LLM_PRIVACY', 'VERIFY', 'LLM and speech services', 'Production data boundary not established by static scan', 'Confirm where prompts, transcripts and tickets are processed and retained.')
    return findings


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--project', default='.', type=Path)
    p.add_argument('--output', default='sep_audit_results/phase4a_security_preflight.json', type=Path)
    args = p.parse_args()
    findings = inspect(args.project.resolve())
    from collections import Counter
    counts = dict(Counter(x['severity'] for x in findings))
    print('Darpan Phase 4A — read-only security preflight')
    for f in findings:
        print(f"[{f['severity']}] {f['code']}: {f['detail']}")
    print('Findings:', counts)
    target = args.output if args.output.is_absolute() else args.project / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(findings=findings, counts=counts), indent=2), encoding='utf-8')
    print('Report:', target.resolve())
    print('No files changed except this diagnostic report; no network calls performed.')

if __name__ == '__main__': main()
