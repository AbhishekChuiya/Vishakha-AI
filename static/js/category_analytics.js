// Darpan category analytics: load AFTER chat.js. Does not modify existing chat functions.
(function () {
    "use strict";
    if (typeof handleAIResponse !== "function") { console.error("Darpan chat.js must load before category_analytics.js"); return; }
    const previousHandler = handleAIResponse;
    handleAIResponse = function (result) {
        if (!result || result.type !== "category_analytics") return previousHandler(result);
        const data = result.analytics || {};
        const area = document.getElementById("chat-area");
        if (!area) return;
        const wrapper = document.createElement("section");
        wrapper.className = "darpan-analytics-report darpan-category-report";
        wrapper.style.cssText = "max-width:680px;width:calc(100% - 52px);box-sizing:border-box;margin:12px 0 22px 48px;padding:22px;border-radius:16px;border:1px solid #64748b55";
        const heading = document.createElement("h3");
        heading.textContent = (data.department || "Department") + " — Category ranking";
        heading.style.margin = "0 0 8px";
        const sub = document.createElement("p");
        sub.textContent = "Sorted by " + (data.sort_by === "non_closed" ? "non-closed tickets" : "total tickets") + " · " + (data.categories_counted || 0) + " categories";
        sub.style.cssText = "font-size:12px;opacity:.75;margin:0 0 14px";
        wrapper.append(heading, sub);
        if (!data.complete) {
            const warn = document.createElement("p");
            warn.textContent = "Incomplete report: " + (data.unresolved || []).length + " category routes failed. Rankings may change after retrying.";
            warn.style.cssText = "color:#d97706;font-weight:600;font-size:13px";
            wrapper.appendChild(warn);
        }
        const rows = data.categories || [];
        const max = Math.max(1, ...rows.map(r => Number(data.sort_by === "non_closed" ? r.non_closed : r.total) || 0));
        const fmt = v => Number(v || 0).toLocaleString("en-IN");
        rows.forEach(function (r, i) {
            const row = document.createElement("div");
            row.style.cssText = "padding:11px 0;border-bottom:1px solid #64748b40";
            const line = document.createElement("div");
            line.style.cssText = "display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:13px";
            const name = document.createElement("strong");
            name.textContent = (i + 1) + ". " + r.category + (r.complete ? "" : " (partial)");
            const counts = document.createElement("span");
            counts.textContent = fmt(r.total) + " total · " + fmt(r.non_closed) + " non-closed";
            line.append(name, counts);
            const track = document.createElement("div");
            track.style.cssText = "height:7px;border-radius:8px;background:#64748b35;margin-top:9px;overflow:hidden";
            const bar = document.createElement("div");
            bar.style.cssText = "height:100%;background:#3b82f6;border-radius:8px;width:" + (100 * (Number(data.sort_by === "non_closed" ? r.non_closed : r.total) || 0) / max).toFixed(1) + "%";
            track.appendChild(bar);
            row.append(line, track);
            wrapper.appendChild(row);
        });
        if (!rows.length) {
            const empty = document.createElement("p");
            empty.textContent = "No mapped categories are available for this report.";
            wrapper.appendChild(empty);
        }
        const foot = document.createElement("p");
        foot.style.cssText = "font-size:11px;opacity:.72;margin-top:14px";
        foot.textContent = "Non-closed uses the Service Excellence includeClosed=false filter. " + (data.note || "");
        wrapper.appendChild(foot);
        area.appendChild(wrapper);
        if (typeof saveChatHistory === "function") saveChatHistory();
        if (typeof scrollToBottom === "function") scrollToBottom();
    };
})();
