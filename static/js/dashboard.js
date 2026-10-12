/* Dashboard / Vishakha AI view switch. No changes to chat persistence or account menu. */
(() => {
  'use strict';
  const dash = document.getElementById('darpan-dashboard');
  const chat = document.getElementById('darpan-chat-view');
  const dashboardTab = document.getElementById('darpan-tab-dashboard');
  const aiTab = document.getElementById('darpan-tab-ai');
  if (!dash || !chat || !dashboardTab || !aiTab) return;
  let fetched = false;
  function show(view) {
    const isDashboard = view === 'dashboard';
    dash.hidden = !isDashboard; chat.hidden = isDashboard;
    document.body.classList.toggle('darpan-view-dashboard', isDashboard);
    document.body.classList.toggle('darpan-view-ai', !isDashboard);
    const history = document.querySelector('.chat-history-section');
    const dashboardSide = document.getElementById('darpan-dashboard-side');
    const appSelector = document.getElementById('darpan-application-selector');
    if(history) history.hidden = isDashboard;
    if(dashboardSide) dashboardSide.hidden = !isDashboard;
    if(appSelector) appSelector.hidden = isDashboard;
    document.getElementById('new-chat-button')?.toggleAttribute('hidden', isDashboard);
    document.getElementById('collapsed-new-chat')?.toggleAttribute('hidden', isDashboard);
    document.getElementById('collapsed-recent-chats')?.toggleAttribute('hidden', isDashboard);
    dashboardTab.classList.toggle('active', isDashboard);
    aiTab.classList.toggle('active', !isDashboard);
    dashboardTab.setAttribute('aria-selected', String(isDashboard));
    aiTab.setAttribute('aria-selected', String(!isDashboard));
    if (isDashboard && !fetched) load();
    if (!isDashboard) document.getElementById('message-input')?.focus();
    try { sessionStorage.setItem('darpan_active_view', view); } catch (_) {}
  }
  const safeText = value => String(value == null ? '' : value);
  const set = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = safeText(value); };
  const validURL = url => {
    try {const parsed = new URL(url);return parsed.protocol === 'https:' && parsed.hostname === 'vresolved.vishakhapolyfab.com' ? parsed.href : null;} catch (_) {return null;}
  };
  function recentRow(ticket) {
    const row = document.createElement('div');row.className = 'darpan-recent-row';
    const icon=document.createElement('span');icon.className='darpan-recent-icon';icon.textContent='▤';row.appendChild(icon);
    const main=document.createElement('div');main.className='darpan-recent-main';
    const title=document.createElement('strong');title.textContent=safeText(ticket.title);main.appendChild(title);
    const meta=document.createElement('small');meta.textContent=[ticket.number, ticket.created_at ? ticket.created_at.slice(0,10):''].filter(Boolean).join(' · ');main.appendChild(meta);row.appendChild(main);
    const badge=document.createElement('span');badge.className='darpan-ticket-pill';badge.textContent=safeText(ticket.status);
    if (/resolved|closed|completed/i.test(ticket.status))badge.classList.add('done');
    else if (/pending|hold|waiting/i.test(ticket.status))badge.classList.add('wait');
    row.appendChild(badge);
    const link=validURL(ticket.url);if(link){row.style.cursor='pointer';row.title='Open ticket in Service Excellence';row.addEventListener('click',()=>window.open(link,'_blank','noopener,noreferrer'));}
    return row;
  }
  async function load() {
    const status=document.getElementById('darpan-metrics-status');
    if(status)status.textContent='Loading live SEP data…';
    try {
      const response=await fetch('/api/dashboard/',{credentials:'same-origin',headers:{'Accept':'application/json'}});
      const data=await response.json();
      if(!response.ok || !data.success)throw new Error(data.error || 'Service Excellence is unavailable');
      const m=data.metrics || {};
      for(const id of ['total','active','pending','resolved']) set('darpan-kpi-'+id, Number.isInteger(m[id]) ? m[id].toLocaleString() : '—');
      const list=document.getElementById('darpan-recent-tickets');
      if(list){list.replaceChildren();if((data.recent||[]).length){for(const ticket of data.recent)list.appendChild(recentRow(ticket));}else{const p=document.createElement('div');p.className='darpan-empty';p.textContent=m.total===0?'You have no SEP tickets yet.':'No recent tickets available.';list.appendChild(p);}}
      if(status)status.textContent=data.partial?'Some SEP metrics are unavailable — retry':'Updated from Service Excellence';
      fetched=!data.partial;
    } catch(e) {
      if(status)status.textContent='SEP dashboard temporarily unavailable';
      const list=document.getElementById('darpan-recent-tickets');if(list)list.textContent=e.message || 'Unable to load tickets';
    }
  }
  function promptAI(text) {
    show('ai');
    const field=document.getElementById('message-input');
    if(field){field.value=text;field.focus();}
    // Pre-fill only; do not silently initiate actions or bypass confirmation.
  }
  document.querySelectorAll('[data-darpan-side]').forEach(el => el.addEventListener('click', () => {
    show('dashboard');
    document.querySelectorAll('[data-darpan-side]').forEach(item => item.classList.toggle('active', item===el));
    const target = { overview: '.darpan-dash-intro', tickets: '#darpan-my-tickets-section', quick: '#darpan-quick-actions-section' }[el.dataset.darpanSide];
    if(target) document.querySelector(target)?.scrollIntoView({behavior:'smooth',block:'start'});
  }));
  dashboardTab.addEventListener('click',()=>show('dashboard'));
  aiTab.addEventListener('click',()=>show('ai'));
  document.getElementById('darpan-hero-open-ai')?.addEventListener('click',()=>show('ai'));
  document.getElementById('darpan-refresh-dashboard')?.addEventListener('click',()=>{fetched=false;load();});
  document.querySelectorAll('[data-darpan-prompt]').forEach(el=>el.addEventListener('click',()=>promptAI(el.dataset.darpanPrompt)));
  // Existing sidebar new chat/history controls are unchanged and must open AI.
  ['new-chat-button','collapsed-new-chat','collapsed-recent-chats'].forEach(id=>{document.getElementById(id)?.addEventListener('click',()=>show('ai'));});
  const list=document.getElementById('recent-chats');
  list?.addEventListener('click',()=>show('ai'));
  let initial='dashboard';try{initial=sessionStorage.getItem('darpan_active_view') || 'dashboard';}catch(_){}
  show(initial==='ai'?'ai':'dashboard');
})();
