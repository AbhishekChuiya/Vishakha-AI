from pathlib import Path
import ast, shutil
from datetime import datetime
ROOT = Path(__file__).resolve().parent
STAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

def change(path, old, new):
    source = path.read_text(encoding='utf-8-sig')
    if new in source:
        print('Already installed:', path.relative_to(ROOT));return
    if source.count(old)!=1:
        raise RuntimeError('Expected exact unique anchor in '+str(path)+' (found '+str(source.count(old))+')')
    result=source.replace(old,new,1)
    if path.suffix=='.py':ast.parse(result)
    backup=path.with_name(path.name+'.backup_'+STAMP)
    shutil.copy2(path,backup)
    path.write_text(result,encoding='utf-8')
    print('Updated:',path.relative_to(ROOT), '| backup:',backup.name)

workflow=ROOT/'ai/agent/workflow.py'
js=ROOT/'static/js/chat.js'
css=ROOT/'static/css/main.css'
for path in (workflow,js,css):
    if not path.is_file():raise FileNotFoundError(path)

old='''        if self.state.current_question:
            return self.handle_option(user_message)

        agent_result = self.orchestrator.understand_request('''
new='''        # Allow explicit cancellation or a clearly new task during a pending form.
        if self.state.current_question:
            import re
            text = str(user_message or "").strip()
            lower = text.casefold()
            if re.fullmatch(r"(?:exit|quit|cancel|stop|nevermind|never mind|abort)[.! ]*", lower):
                answer = self.cancel()
                answer["workflow_interrupted"] = True
                return answer

            # Don't mistake ordinary field answers for a new instruction.
            new_command = bool(
                (re.match(r"^(?:please\\s+)?(?:show|list|find|search|check|count|compare|analy[sz]e|summari[sz]e)\\b", lower)
                 and re.search(r"\\b(?:tickets?|categor(?:y|ies)|subcategor(?:y|ies)|analytics|report|status)\\b", lower))
                or re.match(r"^(?:please\\s+)?(?:create|raise|submit)\\s+(?:an?\\s+|my\\s+|new\\s+)*tickets?\\b", lower)
                or re.match(r"^(?:please\\s+)?(?:explain|define|teach|translate|what is|what are|how does|why does|write an? email|draft an? email|write a letter|draft a letter)\\b", lower)
                or re.fullmatch(r"(?:hi+|hello|hey|how are you|thank you|thanks)[!.? ]*", lower)
            )
            if not new_command:
                return self.handle_option(user_message)
            candidate = self.orchestrator.understand_request(
                user_message, current_ticket_number=None, chat_id=chat_id)
            intent = candidate.get("intent")
            if intent in ("ANALYZE_TICKETS", "SEARCH_TICKETS", "CHECK_TICKET_STATUS",
                          "CREATE_TICKET", "OTHER", "GENERAL_CHAT", None):
                self.state.reset()
                if intent == "ANALYZE_TICKETS":
                    answer = self.handle_ticket_analytics(candidate)
                elif intent in ("OTHER", "GENERAL_CHAT", None):
                    from ai.llm.general_chat import respond_to_general_chat
                    answer = respond_to_general_chat(
                        user_message=user_message, chat_id=chat_id,
                        requester_email=self.requester_email,
                        llm=self.orchestrator.llm)
                else:
                    self.state.update_from_agent(candidate)
                    if self.state.intent == "CREATE_TICKET":
                        answer = self.handle_create_ticket()
                    elif self.state.intent == "CHECK_TICKET_STATUS":
                        answer = self.handle_ticket_status()
                    else:
                        answer = self.handle_search_tickets()
                if isinstance(answer, dict):
                    answer["workflow_interrupted"] = True
                return answer
            return self.handle_option(user_message)

        agent_result = self.orchestrator.understand_request('''
change(workflow,old,new)

renderer=r'''// DARPAN SAFE RICH AI TEXT V1
function darpanFormatInline(value) {
    let text = escapeHtml(value);
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    text = text.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
    return text;
}
function darpanFormatMessage(message) {
    const lines = String(message == null ? '' : message).replace(/\r\n?/g, '\n').split('\n');
    const html = [];
    let paragraph = [], list = null, codeLines = [], inCode = false;
    function flushParagraph() {
        if (paragraph.length) {
            html.push('<p>' + paragraph.map(darpanFormatInline).join('<br>') + '</p>');
            paragraph=[];
        }
    }
    function closeList() { if (list) { html.push('</'+list+'>'); list=null; } }
    for (const line of lines) {
        if (/^\s*```/.test(line)) {
            flushParagraph();closeList();
            if (inCode) { html.push('<pre><code>'+escapeHtml(codeLines.join('\n'))+'</code></pre>');codeLines=[];inCode=false; }
            else inCode=true;
            continue;
        }
        if (inCode) { codeLines.push(line);continue; }
        if (!line.trim()) { flushParagraph();closeList();continue; }
        const heading=line.match(/^\s*#{1,3}\s+(.+)$/);
        if(heading) {flushParagraph();closeList();html.push('<h4>'+darpanFormatInline(heading[1])+'</h4>');continue;}
        const bullet=line.match(/^\s*[-*]\s+(.+)$/);
        const numbered=line.match(/^\s*\d+[.)]\s+(.+)$/);
        if(bullet||numbered){
            flushParagraph();const kind=bullet?'ul':'ol';
            if(list!==kind){closeList();html.push('<'+kind+'>');list=kind;}
            html.push('<li>'+darpanFormatInline((bullet||numbered)[1])+'</li>');continue;
        }
        closeList();paragraph.push(line.trim());
    }
    if(inCode) html.push('<pre><code>'+escapeHtml(codeLines.join('\n'))+'</code></pre>');
    flushParagraph();closeList();return html.join('');
}

'''
change(js,'function addAIMessage(message) {',renderer+'function addAIMessage(message) {')
old='''    messageDiv.className = "message ai-message";

    messageDiv.innerHTML = `
        <div class="avatar">
            AI
        </div>

        <div class="message-bubble">
            <p>${escapeHtml(message)}</p>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    saveChatHistory();'''
new='''    messageDiv.className = "message ai-message";

    messageDiv.innerHTML = `
        <div class="avatar">
            AI
        </div>

        <div class="message-bubble darpan-rich-answer">
            ${darpanFormatMessage(message)}
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    saveChatHistory();'''
change(js,old,new)
old='function handleAIResponse(result) {'
new='''function handleAIResponse(result) {
    if (result && result.workflow_interrupted) {
        document.querySelectorAll(".ai-options, .ticket-confirmation").forEach(el => el.remove());
        saveChatHistory();
    }''' 
change(js,old,new)
css_mark='/* DARPAN RICH AI ANSWERS V1 */'
if css_mark not in css.read_text(encoding='utf-8-sig'):
    backup=css.with_name(css.name+'.backup_'+STAMP);shutil.copy2(css,backup)
    with css.open('a',encoding='utf-8') as f:
        f.write('''
/* DARPAN RICH AI ANSWERS V1 */
.ai-message .darpan-rich-answer{line-height:1.65;overflow-wrap:anywhere;max-width:100%}
.ai-message .darpan-rich-answer p{margin:0 0 12px;white-space:normal}
.ai-message .darpan-rich-answer p:last-child{margin-bottom:0}
.ai-message .darpan-rich-answer h4{font-size:1.04rem;font-weight:700;line-height:1.4;margin:16px 0 8px}
.ai-message .darpan-rich-answer h4:first-child{margin-top:0}
.ai-message .darpan-rich-answer ul,.ai-message .darpan-rich-answer ol{padding-left:24px;margin:8px 0 14px;list-style-position:outside}
.ai-message .darpan-rich-answer ul{list-style-type:disc}
.ai-message .darpan-rich-answer ol{list-style-type:decimal}
.ai-message .darpan-rich-answer li{display:list-item;margin:6px 0}
.ai-message .darpan-rich-answer strong{font-weight:700}
.ai-message .darpan-rich-answer code{font-family:Consolas,monospace;font-size:.88em;padding:2px 5px;border-radius:4px;background:rgba(127,127,127,.14)}
.ai-message .darpan-rich-answer pre{overflow-x:auto;padding:12px;border-radius:10px;background:rgba(127,127,127,.13);margin:10px 0}
.ai-message .darpan-rich-answer pre code{padding:0;background:none;white-space:pre}
''')
    print('Updated:',css.relative_to(ROOT),'| backup:',backup.name)
print('All patches applied. Run python manage.py check and restart Django.')
