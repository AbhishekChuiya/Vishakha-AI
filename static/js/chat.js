const chatInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const chatMessages = document.getElementById("chat-area");
// Server-rendered authenticated user ID; never trust an email supplied by JS.
const DARPAN_USER_ID = document.body.dataset.darpanUserId;
if (!DARPAN_USER_ID || !/^\d+$/.test(DARPAN_USER_ID)) {
    throw new Error("Authenticated user identity missing from page");
}
// Current app is scoped to the authenticated account; old chats default to SEP.
const VISH_APP_KEY = `vishakha_selected_app_user_${DARPAN_USER_ID}`;
const VISH_ACTIVE_APP_KEY = app => `vishakha_active_chat_${app}_user_${DARPAN_USER_ID}`;
let selectedVishakhaApp = localStorage.getItem(VISH_APP_KEY) === 'general' ? 'general' : 'ticketing';
const applicationForChat = chat => chat && chat.application === 'general' ? 'general' : 'ticketing';
const CHAT_HISTORY_KEY = `darpan_chat_history_user_${DARPAN_USER_ID}`;
let activeChatRequestController = null;
let isAIResponding = false;


// Multiple-conversation storage
const CHAT_LIST_KEY = `darpan_chat_list_user_${DARPAN_USER_ID}`;
const ACTIVE_CHAT_KEY = `darpan_active_chat_id_user_${DARPAN_USER_ID}`;

let activeChatId =
    localStorage.getItem(ACTIVE_CHAT_KEY);

if (!activeChatId) {

    activeChatId =
        "chat_" + crypto.randomUUID();

    localStorage.setItem(
        ACTIVE_CHAT_KEY,
        activeChatId
    );
}

/* =========================================================
   USER MESSAGE
========================================================= */

function addUserMessage(message) {

    const messageDiv = document.createElement("div");

    messageDiv.className = "message user-message";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    const text = document.createElement("p");
    text.className = "vishakha-user-text";
    text.textContent = message;
    bubble.appendChild(text);
    messageDiv.appendChild(bubble);

    chatMessages.appendChild(messageDiv);
    saveChatHistory();

    scrollToBottom();
}


/* =========================================================
   AI MESSAGE
========================================================= */

// DARPAN SAFE RICH AI TEXT V1
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

function addAIMessage(message) {

    const messageDiv = document.createElement("div");

    messageDiv.className = "message ai-message";

    messageDiv.innerHTML = `
        <div class="avatar">
            AI
        </div>

        <div class="message-bubble darpan-rich-answer">
            ${darpanFormatMessage(message)}
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    saveChatHistory();

    scrollToBottom();
}

function addDepartmentDetectionMessage(message) {

    const messageDiv = document.createElement("div");

    messageDiv.className = "message ai-message";

    messageDiv.innerHTML = `
        <div class="avatar">
            AI
        </div>

        <div class="message-bubble">
            <p>${escapeHtml(message)}</p>

            <button
                type="button"
                class="department-change-button"
                title="Change department"
            >
                Change
            </button>
        </div>
    `;

    const changeButton =
        messageDiv.querySelector(
            ".department-change-button"
        );

    changeButton.addEventListener(
        "click",
        function() {

            changeButton.disabled = true;

            sendOption("Change Department");
        }
    );

    chatMessages.appendChild(messageDiv);

    saveChatHistory();
    scrollToBottom();
}

function addTextInput(placeholder, field) {

    const container = document.createElement("div");
    container.className = "ai-options";

    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = placeholder;
    input.className = "chat-text-question-input";

    /*
    * Remember which workflow field this input belongs to.
    */
    input.dataset.field = field;

    const submitButton = document.createElement("button");
    submitButton.textContent = "Submit";
    submitButton.className = "chat-text-question-submit";

    async function submitAnswer() {

        const answer = input.value.trim();

        if (!answer) {
            input.focus();
            return;
        }

        // Prevent duplicate submissions
        submitButton.disabled = true;
        input.disabled = true;

        // Display user's answer in chat
        addUserMessage(answer);

        // Remove the temporary input
        container.remove();

        // Send answer using existing backend function
        await sendToBackend(answer, "text");
    }

    submitButton.addEventListener("click", submitAnswer);

    input.addEventListener("keydown", function(event) {

        if (event.key === "Enter") {
            event.preventDefault();
            submitAnswer();
        }

    });

    container.classList.add('vishakha-date-options');
    const pickerWrap = document.createElement('div');
    pickerWrap.className = 'vishakha-date-picker-wrap';
    pickerWrap.appendChild(input);
    const pickerButton = document.createElement('button');
    pickerButton.type = 'button';
    pickerButton.className = 'vishakha-calendar-button';
    pickerButton.title = 'Open calendar';
    pickerButton.setAttribute('aria-label', 'Open date and time picker');
    pickerButton.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/></svg>';
    pickerButton.addEventListener('click', (event) => { event.stopPropagation(); if (input.showPicker) { try { input.showPicker(); return; } catch (_) {} } input.focus(); input.click(); });
    pickerWrap.appendChild(pickerButton);
    container.appendChild(pickerWrap);
    container.appendChild(submitButton);

    chatMessages.appendChild(container);

    saveChatHistory();
    scrollToBottom();

    input.focus();
}


/* =========================================================
   DATE AND DATE-TIME INPUTS
========================================================= */

function addDateInput(field, inputType, placeholder) {

    const container = document.createElement("div");
    container.className = "ai-options";

    const input = document.createElement("input");
    input.type = inputType; // "date" or "datetime-local"
    input.className = "chat-text-question-input";
    input.required = true;

    /*
    * Remember which workflow field this input belongs to.
    * This remains in saved chat HTML.
    */
    input.dataset.field = field;

    // Target date: allow today and all future dates
    if (field === "target_date") {
        const today = new Date();

        const minDate = [
            today.getFullYear(),
            String(today.getMonth() + 1).padStart(2, "0"),
            String(today.getDate()).padStart(2, "0")
        ].join("-");

        input.min = minDate;

        // Request Indian/UK date display format
        input.lang = "en-GB";
    }

    // Incident start time:
    // do not allow the user to select a future date/time.
    if (field === "start_time") {

        function getLocalDateTimeValue(date) {
            const year = date.getFullYear();

            const month = String(
                date.getMonth() + 1
            ).padStart(2, "0");

            const day = String(
                date.getDate()
            ).padStart(2, "0");

            const hours = String(
                date.getHours()
            ).padStart(2, "0");

            const minutes = String(
                date.getMinutes()
            ).padStart(2, "0");

            return (
                `${year}-${month}-${day}` +
                `T${hours}:${minutes}`
            );
        }

        input.max = getLocalDateTimeValue(
            new Date()
        );

        input.addEventListener(
            "focus",
            function () {

                this.max = getLocalDateTimeValue(
                    new Date()
                );
            }
        );
    }

        // Validate manually entered target dates
    if (field === "target_date") {
        input.addEventListener("change", function () {
            if (this.value && this.value < this.min) {
                alert("Please select today or a future date.");
                this.value = "";
            }
        });
    }

    if (field === "start_time") {

        input.addEventListener(
            "change",
            function () {

                const selectedTime =
                    new Date(this.value);

                const now =
                    new Date();

                if (selectedTime > now) {

                    alert(
                        "Incident start time cannot be in the future."
                    );

                    this.value = "";
                }
            }
        );
    }

    if (placeholder) {
        input.setAttribute("aria-label", placeholder);
    }

    const submitButton = document.createElement("button");
    submitButton.textContent = "Submit";
    submitButton.className = "chat-text-question-submit";

    async function submitAnswer() {

        const answer = input.value;

        if (!answer) {
            input.focus();
            return;
        }

        submitButton.disabled = true;
        input.disabled = true;

        addUserMessage(answer);
        container.remove();

        await sendToBackend(answer, "text");
    }

    submitButton.addEventListener("click", submitAnswer);

    input.addEventListener("keydown", function(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            submitAnswer();
        }
    });

    container.appendChild(input);
    container.appendChild(submitButton);

    chatMessages.appendChild(container);

    saveChatHistory();
    scrollToBottom();

    input.focus();
}

/* =========================================================
   OPTION BUTTONS
========================================================= */

function addOptionButtons(options) {

    const container = document.createElement("div");

    container.className = "ai-options";

    options.forEach(function(option) {

        const button = document.createElement("button");

        button.className = "ai-option-button";

        button.textContent = option;

        button.addEventListener("click", function() {

            // Prevent clicking multiple options
            disableButtons(container);

            sendOption(option);

        });

        container.appendChild(button);

    });

    chatMessages.appendChild(container);
    
    saveChatHistory();

    scrollToBottom();
}


/* =========================================================
   CONFIRMATION CARD
========================================================= */


function addConfirmation(ticket) {

    const container = document.createElement("div");
    container.className = "ticket-confirmation";

    // Helper to safely display each field
    function detailRow(label, value) {
        if (value === null || value === undefined || value === "") {
            return "";
        }

        return `
            <div class="ticket-detail">
                <strong>${escapeHtml(label)}:</strong>
                <span>${escapeHtml(value)}</span>
            </div>
        `;
    }

    // Common ticket details
    let detailsHTML = `
        ${detailRow("Department", ticket.department)}
        ${detailRow("Request Type", ticket.request_type)}
        ${detailRow("Category", ticket.category)}
        ${detailRow("Subcategory", ticket.subcategory)}
        ${detailRow("Description", ticket.description)}
        ${detailRow("Location", ticket.location)}
        ${detailRow("Priority", ticket.priority)}
    `;


    function formatDateTime(value) {

        if (!value) {
            return "";
        }

        const date = new Date(value);

        if (isNaN(date.getTime())) {
            return value;
        }

        return date.toLocaleString(
            "en-IN",
            {
                day: "2-digit",
                month: "short",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                hour12: true
            }
        );
    }

    // Incident-specific details
    if (
        ticket.request_type === "Incident Request" &&
        ticket.department !== "IT Department"
    ) {
        detailsHTML += `
            ${detailRow("Impact", ticket.impact)}
            ${detailRow(
                "Incident Start Time",
                formatDateTime(ticket.start_time)
            )}
        `;
    }

    // Service Request-specific details
    if (ticket.request_type === "Service Request") {
        detailsHTML += `
            ${detailRow("Target Date", ticket.target_date)}
            ${detailRow(
                "Business Justification",
                ticket.business_justification
            )}
        `;

        // HR Service Request-specific details
        if (ticket.department === "HR Department") {
            detailsHTML += `
                ${detailRow("Urgency", ticket.urgency)}
            `;
        }
    }

    // IT Service Request / Incident Request contact details
    if (
        ticket.department === "IT Department" &&
        ["Service Request", "Incident Request"].includes(ticket.request_type)
    ) {
        detailsHTML += `
            ${detailRow("Vishakha Email", ticket.email)}
            ${detailRow("Phone Number", ticket.phone)}
        `;
    }

    container.innerHTML = `
        <div class="confirmation-card">

            <h3>Review Ticket Details</h3>

            <p>
                Please review the information below
                before creating your ticket.
            </p>

            <div class="confirmation-details">
                ${detailsHTML}
            </div>

            <div class="confirmation-buttons">

                <button class="confirm-button">
                    Confirm & Create Ticket
                </button>

                <button class="change-details-button">
                    Change Details
                </button>

                <button class="cancel-button">
                    Cancel
                </button>

            </div>

        </div>
    `;

    const confirmButton =
        container.querySelector(".confirm-button");

    const changeDetailsButton =
        container.querySelector(".change-details-button");

    const cancelButton =
        container.querySelector(".cancel-button");

    // CONFIRM
    confirmButton.addEventListener("click", function() {
        disableButtons(container);
        sendOption("Confirm & Create Ticket");
    });

    // CHANGE DETAILS
    changeDetailsButton.addEventListener("click", function() {
        disableButtons(container);
        sendOption("Change Details");
    });

    // CANCEL
    cancelButton.addEventListener("click", function() {
        disableButtons(container);
        sendOption("Cancel");
    });

    chatMessages.appendChild(container);

    saveChatHistory();
    scrollToBottom();
}

/* =========================================================
   DISABLE BUTTONS
========================================================= */

function disableButtons(container) {

    const buttons =
        container.querySelectorAll("button");

    buttons.forEach(function(button) {

        button.disabled = true;

        button.style.opacity = "0.5";

        button.style.cursor = "not-allowed";

    });
}


/* =========================================================
   LOADING
========================================================= */

let vishakhaThinkingTimer = null;
const VISHKHA_THINKING_MESSAGES = {
    general: ["Thinking it through…", "Connecting the dots…", "Putting ideas together…", "Considering your question…", "Working on a response…", "Making sense of it…"],
    sep: ["Working on your request…", "Checking records…", "Retrieving details…", "Processing your request…", "Looking into it…", "Getting things ready…"]
};
function addLoadingMessage() {
    removeLoadingMessage();
    const messageDiv = document.createElement('div');
    messageDiv.id = 'ai-loading';
    messageDiv.className = 'message ai-message ai-thinking-message';
    // The animation represents activity, not verified backend progress.
    messageDiv.innerHTML = `
        <div class="avatar ai-thinking-avatar" aria-hidden="true">✦</div>
        <div class="ai-thinking-bubble" role="status" aria-live="off" aria-label="Vishakha AI is preparing a response">
            <div class="vishakha-thinking-orb" aria-hidden="true"><span></span><span></span><span></span></div>
            <div class="ai-thinking-content"><span class="ai-thinking-text" id="ai-thinking-text">Working on your request…</span></div>
            <div class="vishakha-thinking-progress" aria-hidden="true"></div>
        </div>`;
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
    const isGeneral = selectedVishakhaApp === 'general';
    const messages = isGeneral ? VISHKHA_THINKING_MESSAGES.general : VISHKHA_THINKING_MESSAGES.sep;
    const text = document.getElementById('ai-thinking-text');
    if (text) text.textContent = messages[0];
    let index = 0;
    vishakhaThinkingTimer = window.setInterval(() => {
        const current = document.getElementById('ai-thinking-text');
        if (!current) { window.clearInterval(vishakhaThinkingTimer); vishakhaThinkingTimer = null; return; }
        index = (index + 1) % messages.length;
        current.classList.remove('vishakha-text-enter');
        void current.offsetWidth;
        current.textContent = messages[index];
        current.classList.add('vishakha-text-enter');
    }, 3400);
}
function removeLoadingMessage() {
    if (vishakhaThinkingTimer !== null) {
        window.clearInterval(vishakhaThinkingTimer);
        vishakhaThinkingTimer = null;
    }
    const loadingMessage = document.getElementById('ai-loading');
    if (loadingMessage) {
        loadingMessage.remove();
        saveChatHistory();
    }
}


/* =========================================================
   SCROLL
========================================================= */

function scrollToBottom() {

    chatMessages.scrollTop =
        chatMessages.scrollHeight;
}


/* =========================================================
   ESCAPE HTML
========================================================= */

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent =
        text ?? "";

    return div.innerHTML;
}


/* =========================================================
   CHAT HISTORY
========================================================= */

function saveChatHistory() {

    // Keep the old key temporarily for backward compatibility.
    localStorage.setItem(
        CHAT_HISTORY_KEY,
        chatMessages.innerHTML
    );

    let chats = [];

    try {

        chats = JSON.parse(
            localStorage.getItem(CHAT_LIST_KEY)
            || "[]"
        );

    } catch (error) {

        console.error(
            "Could not read chat list:",
            error
        );

        chats = [];
    }


    const now =
        new Date().toISOString();


    const existingChat =
        chats.find(function(chat) {

            return chat.id === activeChatId;

        });


    if (existingChat) {

        existingChat.html =
            chatMessages.innerHTML;

        existingChat.updatedAt =
            now;
        existingChat.application = selectedVishakhaApp;

    } else {

        chats.unshift({
            id: activeChatId,
            application: selectedVishakhaApp,
            title: "New Chat",
            html: chatMessages.innerHTML,
            createdAt: now,
            updatedAt: now
        });
    }


    localStorage.setItem(
        CHAT_LIST_KEY,
        JSON.stringify(chats)
    );


    localStorage.setItem(
        ACTIVE_CHAT_KEY,
        activeChatId
    );
    localStorage.setItem(VISH_ACTIVE_APP_KEY(selectedVishakhaApp), activeChatId);
}

function openSavedChat(chatId) {

    let chats = [];

    try {

        chats = JSON.parse(
            localStorage.getItem(CHAT_LIST_KEY)
            || "[]"
        );

    } catch (error) {

        console.error(
            "Could not open saved chat:",
            error
        );

        return;
    }


    const selectedChat =
        chats.find(function(chat) {

            return chat.id === chatId;

        });


    if (!selectedChat) {

        return;
    }


    /*
     * Change active conversation.
     */
    activeChatId =
        selectedChat.id;

    localStorage.setItem(
        ACTIVE_CHAT_KEY,
        activeChatId
    );
    localStorage.setItem(VISH_ACTIVE_APP_KEY(selectedVishakhaApp), activeChatId);

    /*
     * Display selected conversation.
     */
    chatMessages.innerHTML =
        selectedChat.html || "";


    /*
     * Restore buttons contained inside
     * the saved HTML.
     */
    restoreButtonEvents();


    /*
     * Refresh sidebar highlight.
     */
    renderRecentChats();

    scrollToBottom();


    /*
    * Restore/check the backend workflow state
    * belonging specifically to this conversation.
    */
    restoreConversationState();
}

function renderRecentChats() {

    const recentChatsContainer =
        document.getElementById(
            "recent-chats"
        );

    if (!recentChatsContainer) {
        return;
    }


    let chats = [];

    try {

        chats = JSON.parse(
            localStorage.getItem(CHAT_LIST_KEY)
            || "[]"
        );

    } catch (error) {

        console.error(
            "Could not read recent chats:",
            error
        );

        chats = [];
    }


    recentChatsContainer.innerHTML = "";


    /*
     * Show most recently updated chats first.
     */
    chats = chats.filter(chat => applicationForChat(chat) === selectedVishakhaApp);
    const searchTerm = (document.getElementById('vishakha-chat-search')?.value || '').trim().toLocaleLowerCase();
    if (searchTerm) {
        chats = chats.filter(chat => (chat.title || '').toLocaleLowerCase().includes(searchTerm)
            || (chat.html || '').replace(/<[^>]*>/g, ' ').toLocaleLowerCase().includes(searchTerm));
    }
    chats.sort(function(a, b) {
        const byPin = Number(Boolean(b.pinned)) - Number(Boolean(a.pinned));
        return byPin || (new Date(b.updatedAt) - new Date(a.updatedAt));
    });


let darpanLastChatGroup = null;
chats.forEach(function(chat) {
    const timestamp = new Date(chat.updatedAt || chat.createdAt || 0);
    const startOfToday = new Date(); startOfToday.setHours(0,0,0,0);
    const startOfYesterday = new Date(startOfToday); startOfYesterday.setDate(startOfYesterday.getDate()-1);
    const group = chat.pinned ? 'Pinned' : timestamp >= startOfToday ? 'Today' : timestamp >= startOfYesterday ? 'Yesterday' : 'Older';
    if (group !== darpanLastChatGroup) {
        const heading = document.createElement('div');
        heading.className = 'darpan-history-group';
        heading.textContent = group;
        recentChatsContainer.appendChild(heading);
        darpanLastChatGroup = group;
    }


    const row =
        document.createElement("div");

    row.className =
        "recent-chat-row";


    if (chat.id === activeChatId) {

        row.classList.add(
            "active"
        );
    }



    /* =========================
       CHAT TITLE
    ========================= */

    const button =
        document.createElement("button");

    button.type = "button";

    button.className =
        "recent-chat-item";

    button.textContent = (chat.pinned ? '📌 ' : '') + (chat.title || "New Chat");


    button.addEventListener(
        "click",
        function() {

            openSavedChat(
                chat.id
            );

        }
    );


    /* =========================
       THREE DOT MENU BUTTON
    ========================= */

    const menuButton =
        document.createElement("button");

    menuButton.type = "button";

    menuButton.className =
        "chat-menu-button";

    menuButton.textContent = "⋮";

    menuButton.title =
        "Chat options";


    /* =========================
       POPUP MENU
    ========================= */

    const menu =
        document.createElement("div");

    menu.className =
        "chat-options-menu";

    menu.innerHTML = `
        <button type="button" class="pin-chat-button">${chat.pinned ? 'Unpin chat' : 'Pin chat'}</button>
        <button
            type="button"
            class="rename-chat-button">
            Rename
        </button>

        <button
            type="button"
            class="delete-chat-button">
            Delete
        </button>
    `;


    /* Initially hide menu */

    menu.style.display =
        "none";


    /* =========================
       OPEN / CLOSE MENU
    ========================= */

    menuButton.addEventListener(
        "click",
        function(event) {

            event.stopPropagation();

            const isOpen =
                menu.style.display ===
                "block";


            /*
             * Close any other open
             * chat menus first.
             */

            document
                .querySelectorAll(
                    ".chat-options-menu"
                )
                .forEach(function(otherMenu) {

                    otherMenu.style.display =
                        "none";

                });


            menu.style.display =
                isOpen
                    ? "none"
                    : "block";

        }
    );


    const pinButton = menu.querySelector('.pin-chat-button');
    pinButton.addEventListener('click', function(event) {
        event.stopPropagation();
        chat.pinned = !Boolean(chat.pinned);
        localStorage.setItem(CHAT_LIST_KEY, JSON.stringify(chats));
        renderRecentChats();
    });

    /* =========================
       RENAME
    ========================= */

    const renameButton =
        menu.querySelector(
            ".rename-chat-button"
        );


    renameButton.addEventListener(
        "click",
        function(event) {

            event.stopPropagation();

            const currentTitle =
                chat.title ||
                "New Chat";


            const newTitle =
                prompt(
                    "Rename chat:",
                    currentTitle
                );


            if (
                newTitle === null ||
                !newTitle.trim()
            ) {

                return;
            }


            chat.title =
                newTitle.trim();

            chat.updatedAt =
                new Date().toISOString();


            localStorage.setItem(
                CHAT_LIST_KEY,
                JSON.stringify(chats)
            );


            renderRecentChats();

        }
    );


    /* =========================
       DELETE
    ========================= */

    const deleteButton =
        menu.querySelector(
            ".delete-chat-button"
        );


    deleteButton.addEventListener(
        "click",
        async function(event) {

            event.stopPropagation();


            const confirmed =
                confirm(
                    "Delete this chat?"
                );


            if (!confirmed) {

                return;
            }


            /*
             * Delete this conversation's workflow
             * from the Django session as well.
             */
            try {

                const response =
                    await fetch(
                        "/api/chat/delete/",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                chat_id: chat.id
                            })
                        }
                    );


                const data =
                    await response.json();


                if (!data.success) {

                    alert(
                        "Could not delete this chat."
                    );

                    return;
                }

            } catch (error) {

                console.error(
                    "Delete chat error:",
                    error
                );

                alert(
                    "Could not delete this chat."
                );

                return;
            }

            const updatedChats =
                chats.filter(
                    function(savedChat) {

                        return (
                            savedChat.id !==
                            chat.id
                        );

                    }
                );


            localStorage.setItem(
                CHAT_LIST_KEY,
                JSON.stringify(
                    updatedChats
                )
            );


            /*
             * If the currently open chat
             * was deleted, open another
             * available conversation.
             */

            if (
                chat.id ===
                activeChatId
            ) {

                if (
                    updatedChats.length > 0
                ) {

                    activeChatId =
                        updatedChats[0].id;

                    localStorage.setItem(
                        ACTIVE_CHAT_KEY,
                        activeChatId
                    );

                    chatMessages.innerHTML =
                        updatedChats[0].html ||
                        "";

                    restoreButtonEvents();

                    /*
                    * Restore the backend workflow belonging
                    * to the conversation we just switched to.
                    */
                    restoreConversationState();

                } else {

                    /*
                     * No conversations remain.
                     * Create a fresh empty conversation
                     * and show the normal welcome screen.
                     */

                    activeChatId =
                        "chat_" +
                        Date.now().toString();

                    localStorage.setItem(
                        ACTIVE_CHAT_KEY,
                        activeChatId
                    );

                    localStorage.removeItem(
                        CHAT_HISTORY_KEY
                    );

                    chatMessages.innerHTML =
                        "";


                    /*
                     * Show initial AI message.
                     */

                    addAIMessage(
                        "Hello! 👋\n\n" +
                        "I'm your Vishakha AI Employee Assistant.\n\n" +
                        "I can help you perform tasks across your company applications.\n\n" +
                        "Currently, the Ticketing application is available."
                    );


                    /*
                     * Show initial suggestions.
                     */

                    const suggestions =
                        document.createElement(
                            "div"
                        );

                    suggestions.className =
                        "suggestions";

                    suggestions.innerHTML = `
                        <button>
                            Create a laptop repair ticket
                        </button>

                        <button>
                            Report a network issue
                        </button>

                        <button>
                            Check my ticket status
                        </button>
                    `;


                    chatMessages.appendChild(
                        suggestions
                    );

                    setupSuggestionButtons(
                        suggestions
                    );


                    /*
                     * Save the fresh conversation
                     * into browser chat history.
                     */

                    saveChatHistory();

                }
            }


            renderRecentChats();

            scrollToBottom();

        }
    );


    /* =========================
       BUILD ROW
    ========================= */

    row.appendChild(
        button
    );

    row.appendChild(
        menuButton
    );

    row.appendChild(
        menu
    );


    recentChatsContainer.appendChild(
        row
    );

});
}

function restoreButtonEvents() {

    const optionButtons =
        document.querySelectorAll(
            ".ai-option-button"
        );

    optionButtons.forEach(function(button) {

        button.addEventListener(
            "click",
            function() {

                const option =
                    button.textContent.trim();

                const container =
                    button.parentElement;

                disableButtons(
                    container
                );

                sendOption(option);

            }
        );

    });


    const confirmButtons =
        document.querySelectorAll(
            ".confirm-button"
        );

    confirmButtons.forEach(function(button) {

        button.addEventListener(
            "click",
            function() {

                const container =
                    button.closest(
                        ".ticket-confirmation"
                    );

                disableButtons(
                    container
                );

                sendOption(
                    "Confirm & Create Ticket"
                );

            }
        );

    });


    const changeDetailsButtons =
        document.querySelectorAll(
            ".change-details-button"
        );

    changeDetailsButtons.forEach(function(button) {

        button.addEventListener(
            "click",
            function() {

                const container =
                    button.closest(
                        ".ticket-confirmation"
                    );

                disableButtons(
                    container
                );

                sendOption(
                    "Change Details"
                );

            }
        );

    });

    const cancelButtons =
        document.querySelectorAll(
            ".cancel-button"
        );

    cancelButtons.forEach(function(button) {

        button.addEventListener(
            "click",
            function() {

                const container =
                    button.closest(
                        ".ticket-confirmation"
                    );

                disableButtons(
                    container
                );

                sendOption(
                    "Cancel"
                );

            }
        );

    });


        /*
     * Restore Department Change buttons
     * when an old conversation is reopened.
     */
    const departmentChangeButtons =
        document.querySelectorAll(
            ".department-change-button"
        );

    departmentChangeButtons.forEach(
        function(button) {

            button.addEventListener(
                "click",
                function() {

                    button.disabled = true;

                    sendOption(
                        "Change Department"
                    );
                }
            );

        }
    );

        /*
     * Restore text/date input Submit and Enter events
     * when an old conversation is reopened.
     */
    const restoredInputs =
        document.querySelectorAll(
            ".chat-text-question-input"
        );

    restoredInputs.forEach(
        function(input) {


            /*
             * Restore Service Request Target Date validation.
             */
            if (
                input.dataset.field ===
                "target_date"
            ) {

                function getLocalDateValue(date) {

                    const year =
                        date.getFullYear();

                    const month =
                        String(
                            date.getMonth() + 1
                        ).padStart(
                            2,
                            "0"
                        );

                    const day =
                        String(
                            date.getDate()
                        ).padStart(
                            2,
                            "0"
                        );

                    return (
                        `${year}-${month}-${day}`
                    );
                }


                /*
                 * Target date must be today
                 * or a future date.
                 */
                input.min =
                    getLocalDateValue(
                        new Date()
                    );

                input.lang =
                    "en-GB";


                /*
                 * Protect against manually
                 * entered invalid dates too.
                 */
                input.addEventListener(
                    "change",
                    function() {

                        if (
                            this.value &&
                            this.value <
                            this.min
                        ) {

                            alert(
                                "Please select today or a future date."
                            );

                            this.value =
                                "";
                        }
                    }
                );
            }

            /*
             * Restore Incident Start Time validation.
             */
            if (
                input.dataset.field ===
                "start_time"
            ) {

                function getLocalDateTimeValue(date) {

                    const year =
                        date.getFullYear();

                    const month =
                        String(
                            date.getMonth() + 1
                        ).padStart(
                            2,
                            "0"
                        );

                    const day =
                        String(
                            date.getDate()
                        ).padStart(
                            2,
                            "0"
                        );

                    const hours =
                        String(
                            date.getHours()
                        ).padStart(
                            2,
                            "0"
                        );

                    const minutes =
                        String(
                            date.getMinutes()
                        ).padStart(
                            2,
                            "0"
                        );

                    return (
                        `${year}-${month}-${day}` +
                        `T${hours}:${minutes}`
                    );
                }


                /*
                 * Prevent the browser picker from
                 * allowing a future date/time.
                 */
                input.max =
                    getLocalDateTimeValue(
                        new Date()
                    );


                /*
                 * Refresh the maximum whenever
                 * the field receives focus.
                 */
                input.addEventListener(
                    "focus",
                    function() {

                        this.max =
                            getLocalDateTimeValue(
                                new Date()
                            );
                    }
                );


                /*
                 * Also validate manually entered values.
                 */
                input.addEventListener(
                    "change",
                    function() {

                        if (!this.value) {
                            return;
                        }

                        const selectedTime =
                            new Date(
                                this.value
                            );

                        const now =
                            new Date();


                        if (
                            selectedTime >
                            now
                        ) {

                            alert(
                                "Incident start time cannot be in the future."
                            );

                            this.value =
                                "";
                        }
                    }
                );
            }



            const container =
                input.closest(
                    ".ai-options"
                );

            if (!container) {
                return;
            }


            const submitButton =
                container.querySelector(
                    ".chat-text-question-submit"
                );

            if (!submitButton) {
                return;
            }


            /*
             * Do not restore completed/disabled
             * historical inputs.
             */
            if (
                input.disabled ||
                submitButton.disabled
            ) {
                return;
            }


            async function submitRestoredAnswer() {

                const answer =
                    input.value.trim();

                if (!answer) {

                    input.focus();

                    return;
                }


                /*
                 * Prevent duplicate submissions.
                 */
                submitButton.disabled = true;
                input.disabled = true;


                /*
                 * Display the user's answer.
                 */
                addUserMessage(
                    answer
                );


                /*
                 * Remove the temporary input.
                 */
                container.remove();


                /*
                 * Continue this chat's backend workflow.
                 */
                await sendToBackend(
                    answer,
                    "text"
                );
            }


            submitButton.addEventListener(
                "click",
                submitRestoredAnswer
            );


            input.addEventListener(
                "keydown",
                function(event) {

                    if (
                        event.key === "Enter"
                    ) {

                        event.preventDefault();

                        submitRestoredAnswer();
                    }
                }
            );

        }
    );

}

function restoreChatHistory() {

    let chats = [];

    try {

        chats = JSON.parse(
            localStorage.getItem(CHAT_LIST_KEY)
            || "[]"
        );

    } catch (error) {

        console.error(
            "Could not restore chat list:",
            error
        );

        chats = [];
    }


    const activeChat =
        chats.find(function(chat) {

            return chat.id === activeChatId;

        });


    /*
     * Restore the active conversation from
     * the new multi-chat storage.
     */
    if (activeChat && activeChat.html) {

        chatMessages.innerHTML =
            activeChat.html;

        restoreButtonEvents();

        scrollToBottom();

        return true;
    }


    /*
     * Backward compatibility:
     * restore an old conversation saved before
     * multi-chat history was introduced.
     */
    const legacyHistory =
        localStorage.getItem(
            CHAT_HISTORY_KEY
        );


    if (legacyHistory) {

        chatMessages.innerHTML =
            legacyHistory;

        restoreButtonEvents();

        scrollToBottom();

        // Migrate it into the new storage.
        saveChatHistory();

        return true;
    }


    return false;
}


function clearChatHistory() {

    localStorage.removeItem(
        CHAT_HISTORY_KEY
    );

    chatMessages.innerHTML = "";

}


function setAutomaticChatTitle(message) {

    let chats = [];

    try {

        chats = JSON.parse(
            localStorage.getItem(CHAT_LIST_KEY)
            || "[]"
        );

    } catch (error) {

        console.error(
            "Could not update chat title:",
            error
        );

        return;
    }


    const activeChat =
        chats.find(function(chat) {

            return chat.id === activeChatId;

        });


    if (!activeChat) {
        return;
    }


    /*
     * Only automatically rename chats that
     * still have the default title.
     *
     * This prevents manually renamed chats
     * from being overwritten.
     */
    if (
        activeChat.title !== "New Chat"
    ) {
        return;
    }


    let title =
        message.trim();


    /*
     * Keep stored titles reasonably short.
     */
    if (title.length > 45) {

        title =
            title.substring(0, 45)
                .trim() + "...";
    }


    if (!title) {
        return;
    }


    activeChat.title =
        title;

    activeChat.updatedAt =
        new Date().toISOString();


    localStorage.setItem(
        CHAT_LIST_KEY,
        JSON.stringify(chats)
    );


    renderRecentChats();
}

/* =========================================================
   SEND NORMAL MESSAGE
========================================================= */

async function sendMessage() {

    const message =
        chatInput.value.trim();

    if (!message) {
        return;
    }


    addUserMessage(
        message
    );


    /*
     * Use the employee's first message
     * as the automatic conversation title.
     */
    setAutomaticChatTitle(
        message
    );


    chatInput.value = "";
    chatInput.dispatchEvent(new Event('input', { bubbles: true }));

    await sendToBackend(
        message,
        "text"
    );
}

/* =========================================================
   SEND OPTION
========================================================= */

async function sendOption(option) {

    addUserMessage(option);

    await sendToBackend(
        option,
        "option"
    );
}


/* =========================================================
   BACKEND REQUEST
========================================================= */

async function sendToBackend(
    message,
    messageType
) {

    addLoadingMessage();

    try {

        // Cancel any previous unfinished request.
        if (activeChatRequestController) {
            activeChatRequestController.abort();
        }

        activeChatRequestController =
            new AbortController();

        isAIResponding = true;

        sendButton.innerHTML = "■";
        sendButton.title = "Stop response";
        sendButton.setAttribute(
            "aria-label",
            "Stop response"
        );
        sendButton.classList.add("stop-response");

        const response =
            await fetch(
                "/api/chat/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        message: message,
                        message_type: messageType,
                        chat_id: activeChatId,
                        application: selectedVishakhaApp
                    }),
                    signal: activeChatRequestController.signal

                }
            );


        if (response.status === 401 || response.status === 403) {
            window.location.assign("/login/");
            return;
        }
        const data = await response.json();

        removeLoadingMessage();


        if (!data.success) {

            addAIMessage(
                "Sorry, I encountered an error: "
                + data.error
            );

            return;

        }


        handleAIResponse(
            data.response
        );

    }
    catch (error) {

        removeLoadingMessage();

        // User intentionally clicked Stop
        if (error.name === "AbortError") {

            console.log(
                "AI response stopped by user."
            );

            return;
        }

        // Actual connection/server error
        addAIMessage(
            "Sorry, I could not connect to the AI service."
        );

        console.error(error);
    }
    finally {

    isAIResponding = false;
    activeChatRequestController = null;

    sendButton.innerHTML = "➤";
    sendButton.title = "Send";
    sendButton.setAttribute(
        "aria-label",
        "Send"
    );

    sendButton.classList.remove(
        "stop-response"
    );
}
}


/* =========================================================
   HANDLE AI RESPONSE
========================================================= */

function handleAIResponse(result) {
    if (result && result.workflow_interrupted) {
        document.querySelectorAll(".ai-options, .ticket-confirmation").forEach(el => el.remove());
        saveChatHistory();
    }

    if (!result) {

        return;

    }


    /* STRUCTURED ANALYTICS REPORT */
    if (result.type === "ticket_analytics" && result.analytics) {
        addTicketAnalyticsCard(result.analytics, result.analytics_view || "OVERVIEW");
        return;
    }

    /* MESSAGE */

    if (result.type === "message") {

        addAIMessage(
            result.message
        );

        return;
    }


    /* QUESTION */

    if (result.type === "question") {

        if (
            result.field === "request_type" &&
            result.department
        ) {

            addDepartmentDetectionMessage(
                result.message
            );

        } else {

            addAIMessage(
                result.message
            );
        }


        if (result.input_type === "date") {

            addDateInput(
                result.field,
                "date",
                result.placeholder || "Select a date"
            );

        } else if (result.input_type === "datetime-local") {

            addDateInput(
                result.field,
                "datetime-local",
                result.placeholder || "Select date and time"
            );

        } else if (result.input_type === "text") {

            addTextInput(
                result.placeholder || "Type your answer here...",
                result.field
            );

        } else {

            addOptionButtons(result.options || []);

        }

        return;
    }

    /* CONFIRMATION */

    if (result.type === "confirmation") {

        addAIMessage(
            result.message
        );

        addConfirmation(
            result.ticket
        );

        return;
    }


    /* SUCCESS */

    if (result.type === "success") {

        addAIMessage(
            result.message
        );


        if (result.ticket_number) {

            addAIMessage(
                "Ticket Number: "
                + result.ticket_number
            );

        }


        if (result.web_url) {

            addTicketLink(
                result.web_url
            );

        }

        return;
    }

    if (result.type === "ticket_search_summary") {
        addAIMessage(result.message);

        addTicketSearchSummary(result);

        return;
    }

    /* TICKET STATUS */

    if (result.type === "ticket_status") {

        addAIMessage(result.message);

        if (result.tickets && result.tickets.length > 0) {

            addTicketStatusCards(
                result.tickets
            );
        }

        return;
    }


    /* TICKET SEARCH */

    if (result.type === "ticket_search") {

        addAIMessage(result.message);

        if (result.tickets && result.tickets.length > 0) {

            addTicketSearchCards(
                result.tickets
            );
        }

        return;
    }

    if (result.type === "ticket_answer") {
        addAIMessage(result.message);

        if (result.ticket) {
            addTicketAnswerCard(result.ticket, result.answer_type);
        }

        return;
    }

    if (result.type === "ticket_list") {

        addAIMessage(result.message);

        if (result.tickets && result.tickets.length > 0) {

            addTicketStatusCards(
                result.tickets.map(function(ticket) {

                    return {
                        ticket_number:
                            ticket.ticketNumber ||
                            ticket.ticket_number,

                        title:
                            ticket.title,

                        status:
                            ticket.status?.status ||
                            ticket.status,

                        priority:
                            ticket.priority?.name ||
                            ticket.priority,

                        web_url:
                            ticket.webUrl ||
                            ticket.web_url
                    };
                })
            );
        }

        return;
    }

    if (result.type === "ticket_detail") {
        addAIMessage(result.message);

        if (result.ticket) {
            addTicketDetailCard(result.ticket);
        }

        return;
    }

    /* ERROR */

    if (result.type === "error") {

        addAIMessage(
            result.message
        );

        return;
    }

}

function getTicketStatusClass(status) {

    if (!status) {
        return "status-default";
    }

    const value = status
        .toString()
        .trim()
        .toLowerCase();

    if (
        value === "resolved" ||
        value === "completed" ||
        value === "fulfilled" ||
        value === "approved"
    ) {
        return "status-success";
    }

    if (
        value === "cancelled" ||
        value === "canceled" ||
        value === "rejected" ||
        value === "failed"
    ) {
        return "status-danger";
    }

    if (
        value === "pending" ||
        value === "pending approval" ||
        value === "on-hold" ||
        value === "user input required"
    ) {
        return "status-warning";
    }

    if (
        value === "new" ||
        value === "open" ||
        value === "re-open"
    ) {
        return "status-info";
    }

    if (
        value === "in progress" ||
        value === "in fulfillment" ||
        value === "under investigation" ||
        value === "development" ||
        value === "testing" ||
        value === "under uat"
    ) {
        return "status-progress";
    }

    if (
        value === "closed" ||
        value === "cr closed"
    ) {
        return "status-neutral";
    }

    return "status-default";
}


/* =========================================================
   ANALYTICS REPORT — DATA COMES FROM AUTHORIZED BACKEND
========================================================= */
function addTicketAnalyticsCard(data, view = "OVERVIEW") {
    const fmt = n => Number(n ?? 0).toLocaleString("en-IN");
    const total = Number(data.total_tickets || 0);
    const segments = [
        ["Open / non-closed", Number(data.open_tickets || 0), "#f59e0b"],
        ["Resolved", Number(data.resolved_tickets || 0), "#10b981"],
        ["Cancelled", Number(data.cancelled_tickets || 0), "#ef476f"],
        ["Closed", Number(data.closed_tickets || 0), "#818cf8"],
    ];
    const typeRows = Object.entries(data.by_request_type || {});
    const incident = data.by_request_type?.["Incident Request"] || {};
    const service = data.by_request_type?.["Service Request"] || {};
    let offset = 0;
    const stops = segments.filter(x => x[1] > 0).map(([label, value, color]) => {
        const from = offset;
        offset += total > 0 ? 100 * value / total : 0;
        return `${color} ${from.toFixed(2)}% ${offset.toFixed(2)}%`;
    });
    const ring = stops.length ? `conic-gradient(${stops.join(",")})` : "#64748b";
    const percent = n => `${Number(n || 0).toFixed(1)}%`;
    const viewLabels = {
        OVERVIEW: "Department overview",
        REQUEST_TYPES: "Incident vs Service Request",
        RESOLUTION_RATE: "Resolution percentage",
        BACKLOG: "Non-closed ticket workload",
        STATUS_BREAKDOWN: "Status distribution"
    };
    let highlight = "";
    if (view === "REQUEST_TYPES") {
        highlight = `<div class="darpan-analytics-types"><h4>Request Type Comparison</h4>
            <div><span>Incident share</span><strong>${percent(data.incident_share_percent)}</strong></div>
            <div><span>Service share</span><strong>${percent(data.service_share_percent)}</strong></div></div>`;
    } else if (view === "RESOLUTION_RATE") {
        highlight = `<div class="darpan-analytics-types"><h4>Resolution Rate</h4>
            <div><span>Resolved / total</span><strong>${percent(data.resolution_rate_percent)}</strong></div>
            <div><span>Resolved tickets</span><strong>${fmt(data.resolved_tickets)}</strong></div></div>`;
    } else if (view === "BACKLOG") {
        highlight = `<div class="darpan-analytics-types"><h4>Non-closed workload</h4>
            <div><span>Non-closed tickets</span><strong>${fmt(data.open_tickets)}</strong></div>
            <div><span>Share of total</span><strong>${percent(data.non_closed_rate_percent)}</strong></div></div>`;
    } else if (view === "STATUS_BREAKDOWN") {
        highlight = `<div class="darpan-analytics-types"><h4>Status totals</h4>
            <div><span>Resolved</span><strong>${fmt(data.resolved_tickets)}</strong></div>
            <div><span>Closed</span><strong>${fmt(data.closed_tickets)}</strong></div>
            <div><span>Cancelled</span><strong>${fmt(data.cancelled_tickets)}</strong></div></div>`;
    }
    const metric = (label, value) => `<div class="darpan-analytics-metric"><span>${label}</span><strong>${fmt(value)}</strong></div>`;
    const wrapper = document.createElement("section");
    wrapper.className = "darpan-analytics-report";
    wrapper.innerHTML = `
        <div class="darpan-analytics-heading"><div><small>TICKET ANALYTICS</small>
        <h3>${escapeHtml(data.department || "IT Department")}</h3>
        <p>${escapeHtml(viewLabels[view] || viewLabels.OVERVIEW)} · Service Excellence</p></div><span class="darpan-analytics-pill">Report</span></div>
        <div class="darpan-analytics-metrics">
            ${metric("Total Tickets", total)}
            ${metric("Open / non-closed", data.open_tickets)}
            ${metric("Resolved", data.resolved_tickets)}
            ${metric("Cancelled", data.cancelled_tickets)}
        </div>
        <div class="darpan-analytics-lower">
            <div class="darpan-analytics-ring" style="background:${ring}"><div>${fmt(total)}<small>Total</small></div></div>
            <div class="darpan-analytics-legend">${segments.map(([name,value,color]) =>
                `<div><span class="darpan-analytics-dot" style="background:${color}"></span><span>${name}</span><b>${fmt(value)}</b></div>`
            ).join("")}</div>
        </div>
        ${highlight}
        <div class="darpan-analytics-types"><h4>Request Type Breakdown</h4>
        ${typeRows.map(([label,row]) => `<div><span>${escapeHtml(label)}</span><strong>${fmt(row.total)}</strong></div>`).join("")}</div>
        <p class="darpan-analytics-foot">Open is defined using the API's non-closed filter. Values reflect the latest API response.</p>
    `;
    chatMessages.appendChild(wrapper);
    saveChatHistory();
    scrollToBottom();
}

/* =========================================================
   TICKET SEARCH SUMMARY
========================================================= */

function addTicketSearchSummary(result) {

    const container = document.createElement("div");
    container.className = "ticket-search-summary";

    const categoryPath = [
        result.category,
        result.subcategory
    ]
        .filter(Boolean)
        .join(" › ");

    const breakdownHTML = (result.breakdown || [])
        .map(function(item) {

            return `
                <div class="ticket-summary-breakdown-item">

                    <span class="ticket-summary-breakdown-label">
                        ${escapeHtml(item.label)}
                    </span>

                    <strong class="ticket-summary-breakdown-count">
                        ${item.count ?? 0}
                    </strong>

                </div>
            `;

        })
        .join("");


    container.innerHTML = `

        <div class="ticket-summary-card">

            <div class="ticket-summary-header">

                <div>
                    <div class="ticket-summary-title">
                        Ticket Search Results
                    </div>

                    <div class="ticket-summary-department">
                        ${escapeHtml(
                            result.department ||
                            "All Departments"
                        )}
                    </div>
                </div>

                ${
                    result.status
                        ? `
                            <span class="ticket-summary-status ${getTicketStatusClass(result.status)}">
                                ${escapeHtml(result.status)}
                            </span>
                        `
                        : ""
                }

            </div>


            ${
                categoryPath
                    ? `
                        <div class="ticket-summary-category">
                            ${escapeHtml(categoryPath)}
                        </div>
                    `
                    : ""
            }

            ${
                result.keyword
                    ? `
                        <div class="ticket-summary-category">
                            <strong>Keyword:</strong>
                            ${escapeHtml(result.keyword)}
                        </div>
                    `
                    : ""
            }


            <div class="ticket-summary-total">

                <strong>
                    ${result.total ?? 0}
                </strong>

                <span>
                    ${
                        result.total === 1
                            ? "Matching Ticket"
                            : "Matching Tickets"
                    }
                </span>

            </div>


            ${
                breakdownHTML
                    ? `
                        <div class="ticket-summary-breakdown">
                            ${breakdownHTML}
                        </div>
                    `
                    : ""
            }

        </div>
    `;


    chatMessages.appendChild(container);

    saveChatHistory();

    scrollToBottom();
}

function addTicketStatusCards(tickets) {

    const container =
        document.createElement("div");

    container.className =
        "ticket-status-list";

    tickets.forEach(function(ticket) {

        const card =
            document.createElement("div");


            
        card.className =
            "ticket-status-card";

        const ticketUrl =
            ticket.web_url || "#";

        card.innerHTML = `

        <div class="ticket-status-header">

            <strong>
                ${escapeHtml(
                    ticket.ticket_number || "Unknown"
                )}
            </strong>

            <span class="ticket-status-badge">
                ${escapeHtml(
                    ticket.status || "Unknown"
                )}
            </span>

        </div>

        <div class="ticket-status-title">

            ${escapeHtml(
                ticket.title || "No title"
            )}

        </div>

        <div class="ticket-status-meta">

            <span>
                Priority:
                ${escapeHtml(
                    ticket.priority || "Unknown"
                )}
            </span>

        </div>

        ${
            ticketUrl !== "#"
                ? `
                <div class="ticket-status-footer">

                    <a
                        href="${escapeHtml(ticketUrl)}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Open Ticket ↗
                    </a>

                </div>
                `
                : ""
        }

    `;

        container.appendChild(card);

    });

    chatMessages.appendChild(container);

    scrollToBottom();

    saveChatHistory();
}

/* =========================================================
   TICKET LINK
========================================================= */

function addTicketLink(url) {

    const messageDiv =
        document.createElement("div");

    messageDiv.className =
        "message ai-message";

    messageDiv.innerHTML = `

        <div class="avatar">
            AI
        </div>

        <div class="message-bubble">

            <p>
                Ticket Link:
            </p>

            <p>
                <a
                    href="${escapeHtml(url)}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    Open Ticket
                </a>
            </p>

        </div>
    `;

    chatMessages.appendChild(messageDiv);

    scrollToBottom();
}


/* =========================================================
   SUGGESTION BUTTONS
========================================================= */
// One delegated handler supports buttons inserted by New Chat, history restore,
// and application switching. No per-button listeners (avoids duplicate submits).
const VISH_GENERAL_SUGGESTIONS = [
    'Explain what agentic AI is',
    'Help me write a project update email',
    'Summarize the advantages of automation'
];
const VISH_SEP_SUGGESTIONS = [
    'Create a laptop repair ticket',
    'Report a network issue',
    'Check my ticket status'
];
function setupSuggestionButtons(container) {
    // The container is handled through the delegated chat-area listener.
    // Keep this function for compatibility with existing callers.
    if (container) container.querySelectorAll('button').forEach(btn => btn.type = 'button');
}
function renderApplicationSuggestions(container) {
    const target = container || document.createElement('div');
    target.className = 'suggestions';
    target.replaceChildren();
    const prompts = selectedVishakhaApp === 'general'
        ? VISH_GENERAL_SUGGESTIONS : VISH_SEP_SUGGESTIONS;
    prompts.forEach(prompt => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = prompt;
        target.appendChild(btn);
    });
    return target;
}
function setupSuggestions() {
    const suggestions = document.querySelector('.suggestions');
    if (suggestions) renderApplicationSuggestions(suggestions);
}
chatMessages.addEventListener('click', function(event) {
    const button = event.target.closest('.suggestions button');
    if (!button || !chatMessages.contains(button) || isAIResponding || button.disabled) return;
    event.preventDefault();
    const prompt = button.textContent.trim();
    if (!prompt) return;
    // A quick prompt is a normal chat message, not an option answer.
    addUserMessage(prompt);
    setAutomaticChatTitle(prompt);
    chatInput.value = '';
    button.closest('.suggestions')?.remove();
    sendToBackend(prompt, 'text');
});


/* =========================================================
   SEND BUTTON
========================================================= */

sendButton.addEventListener(
    "click",
    async function() {

        if (
            isAIResponding &&
            activeChatRequestController
        ) {

            // Stop displaying/waiting for the current response
            activeChatRequestController.abort();

            // Tell Django which chat was stopped
            try {

                await fetch(
                    "/api/chat/stop/",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            chat_id: activeChatId
                        })
                    }
                );

            } catch (error) {

                console.error(
                    "Could not notify backend about stop:",
                    error
                );
            }

            return;
        }

        sendMessage();
    }
);


/* =========================================================
   ENTER KEY
========================================================= */

chatInput.addEventListener(
    "keydown",
    function(event) {

        // The text area inserts a newline for Shift+Enter.
        // Avoid submitting while an IME is composing text.
        if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
            event.preventDefault();
            if (!isAIResponding) sendMessage();
        }

    }
);
async function restoreConversationState() {

    try {

        const response =
            await fetch(
            "/api/chat/state/?chat_id=" +
            encodeURIComponent(
                activeChatId
            )
        );

        const data =
            await response.json();

        if (!data.success) {

            return;

        }

        if (!data.active) {

            return;

        }

        /*
         * If chat history already exists,
         * don't duplicate the current question.
         */

        const hasPendingInput =
            document.querySelector(
                ".ai-options"
            ) ||
            document.querySelector(
                ".chat-text-question-input"
            );

        if (
            data.type === "question" &&
            !hasPendingInput
        ) {

            /*
            * Request Type question:
            * restore the detected department message
            * together with its Change button.
            */
            if (
                data.field === "request_type" &&
                data.department
            ) {

                addDepartmentDetectionMessage(
                    data.message
                );

            } else {

                addAIMessage(
                    data.message
                );
            }


            if (data.input_type === "date") {

                addDateInput(
                    data.field,
                    "date",
                    data.placeholder ||
                        "Select a date"
                );

            } else if (
                data.input_type ===
                "datetime-local"
            ) {

                addDateInput(
                    data.field,
                    "datetime-local",
                    data.placeholder ||
                        "Select date and time"
                );

            } else if (
                data.input_type === "text"
            ) {

                addTextInput(
                    data.placeholder ||
                        "Type your answer here...",
                    data.field
                );

            } else {

                addOptionButtons(
                    data.options || []
                );
            }
        }

        if (
            data.type === "confirmation" &&
            !document.querySelector(
                ".ticket-confirmation"
            )
        ) {

            addAIMessage(
                data.message
            );

            addConfirmation(
                data.ticket
            );

        }

    }
    catch (error) {

        console.error(
            "Could not restore conversation:",
            error
        );

    }

}

/* =========================================================
   NEW CHAT
========================================================= */

async function startNewChat() {

    const confirmed =
        confirm(
            "Start a new chat?\n\n" +
            "The current conversation will be cleared."
        );

    if (!confirmed) {

        return;

    }


    try {

                    /*
            * Create the NEW conversation ID first.
            * The backend must initialize the new chat,
            * not reset the currently open chat.
            */
            activeChatId =
                (selectedVishakhaApp === "general" ? "gen_" : "sep_") +
                crypto.randomUUID();

            localStorage.setItem(
                ACTIVE_CHAT_KEY,
                activeChatId
            );

        const response =
            await fetch(
                "/api/chat/new/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        chat_id: activeChatId
                    })
                }
            );


        const data =
            await response.json();


        if (!data.success) {

            alert(
                "Could not start a new chat."
            );

            return;

        }


        /* -------------------------------------------------
        Start a completely new conversation
        ------------------------------------------------- */

        // Remove the legacy single-chat copy.
        localStorage.removeItem(
            CHAT_HISTORY_KEY
        );



        /* Clear visible chat */

        chatMessages.innerHTML = "";


        /* Show initial AI message */

        addAIMessage(
            "Hello! 👋\n\n" +
            (selectedVishakhaApp === "general"
                ? "General mode: ask me anything, brainstorm, or draft writing. I won't perform company actions in this mode."
                : "SEP mode: I can create tickets, check statuses, search requests, and show authorized analytics.")
        );


        /* Show suggestions */

        const suggestions =
            document.createElement("div");

        suggestions.className =
            "suggestions";

        renderApplicationSuggestions(suggestions);

        chatMessages.appendChild(
            suggestions
        );

        setupSuggestionButtons(
            suggestions
        );


        /*
        * Save the newly created conversation.
        */
        saveChatHistory();


        /*
        * Immediately show the new conversation
        * in the Recent Chats sidebar.
        */
        renderRecentChats();


        scrollToBottom();

    }
    catch (error) {

        console.error(
            "New chat error:",
            error
        );

        alert(
            "Could not start a new chat."
        );

    }
}

/* =========================================================
   INITIALIZE
========================================================= */

setupSuggestions();

// On first upgrade, keep existing untagged chats in SEP and never mix them with General.
(function initializeApplicationChat() {
    const allChats = (() => { try { return JSON.parse(localStorage.getItem(CHAT_LIST_KEY) || '[]'); } catch (_) { return []; } })();
    const selectedId = localStorage.getItem(VISH_ACTIVE_APP_KEY(selectedVishakhaApp));
    const matches = id => allChats.some(c => c.id === id && applicationForChat(c) === selectedVishakhaApp);
    if (selectedId && matches(selectedId)) activeChatId = selectedId;
    else if (!matches(activeChatId)) activeChatId = (selectedVishakhaApp === 'general' ? 'gen_' : 'sep_') + crypto.randomUUID();
    localStorage.setItem(ACTIVE_CHAT_KEY, activeChatId);
    localStorage.setItem(VISH_ACTIVE_APP_KEY(selectedVishakhaApp), activeChatId);
    // Do not import legacy SEP HTML into a brand-new General chat.
    if (selectedVishakhaApp === 'general' && !matches(activeChatId)) localStorage.removeItem(CHAT_HISTORY_KEY);
})();
const vishakhaChatRestored = restoreChatHistory();
if (selectedVishakhaApp === 'general' && !vishakhaChatRestored) {
    chatMessages.replaceChildren();
    addAIMessage('General mode is ready. Ask questions, get explanations, or draft writing.');
    chatMessages.appendChild(renderApplicationSuggestions());
}
renderRecentChats();
if (selectedVishakhaApp === 'ticketing') restoreConversationState();


/* New Chat */

const newChatButton =
    document.getElementById(
        "new-chat-button"
    );

if (newChatButton) {

    newChatButton.addEventListener(
        "click",
        startNewChat
    );

}

/*
 * Close Recent Chat three-dot menus
 * when clicking anywhere outside them.
 *
 * Capture mode makes this run even when
 * another element uses stopPropagation().
 */
document.addEventListener(
    "click",
    function(event) {

        const clickedMenu =
            event.target.closest(
                ".chat-options-menu"
            );

        const clickedMenuButton =
            event.target.closest(
                ".chat-menu-button"
            );


        /*
         * Let clicks on the three-dot button
         * or inside the popup menu behave normally.
         */
        if (
            clickedMenu ||
            clickedMenuButton
        ) {
            return;
        }


        document
            .querySelectorAll(
                ".chat-options-menu"
            )
            .forEach(
                function(menu) {

                    menu.style.display =
                        "none";
                }
            );

    },
    true
);

function addTicketDetailCard(ticket) {
    const container = document.createElement("div");
    container.className = "ticket-detail-card";

    container.innerHTML = `
        <div class="ticket-detail-header">
            <strong>${escapeHtml(ticket.ticket_number || "Unknown")}</strong>
            <span class="ticket-status-badge">
                ${escapeHtml(ticket.status || "Unknown")}
            </span>
        </div>

        <div class="ticket-detail-title">
            ${escapeHtml(ticket.title || "No title")}
        </div>

        <div class="ticket-detail-row">
            <span>Priority</span>
            <strong>${escapeHtml(ticket.priority || "Unknown")}</strong>
        </div>

        <div class="ticket-detail-row">
            <span>Requester</span>
            <strong>${escapeHtml(ticket.requester || "Unknown")}</strong>
        </div>

        <div class="ticket-detail-row">
            <span>Assigned To</span>
            <strong>${escapeHtml(ticket.assigned_to || "Not assigned")}</strong>
        </div>

        <div class="ticket-detail-description">
            <span>Description</span>
            <p>${escapeHtml(ticket.description || "No description")}</p>
        </div>

        <div class="ticket-detail-footer">
            <a href="${escapeHtml(ticket.web_url || "#")}"
               target="_blank"
               rel="noopener noreferrer">
                Open Ticket ↗
            </a>
        </div>
    `;

    chatMessages.appendChild(container);
    scrollToBottom();
    saveChatHistory();
}

function addTicketAnswerCard(ticket, answerType) {

    const container = document.createElement("div");
    container.className = "ticket-answer-card";

    let content = "";

    if (answerType === "STATUS") {

        content = `
            <div class="ticket-answer-header">
                <strong>
                    ${escapeHtml(ticket.ticket_number || "Unknown")}
                </strong>

                <span class="ticket-status-badge">
                    ${escapeHtml(ticket.status || "Unknown")}
                </span>
            </div>

            <div class="ticket-answer-title">
                ${escapeHtml(ticket.title || "No title")}
            </div>

            <div class="ticket-answer-row">
                <span>Priority</span>
                <strong>
                    ${escapeHtml(ticket.priority || "Unknown")}
                </strong>
            </div>
        `;

    }

    else if (answerType === "ASSIGNED_TO") {

        content = `
            <div class="ticket-answer-header">
                <strong>
                    ${escapeHtml(ticket.ticket_number || "Unknown")}
                </strong>
            </div>

            <div class="ticket-answer-row">
                <span>Assigned To</span>
                <strong>
                    ${escapeHtml(
                        ticket.assigned_to || "Not assigned"
                    )}
                </strong>
            </div>

            <div class="ticket-answer-row">
                <span>Status</span>
                <strong>
                    ${escapeHtml(ticket.status || "Unknown")}
                </strong>
            </div>
        `;

    }

    else if (answerType === "REQUESTER") {

        content = `
            <div class="ticket-answer-header">
                <strong>
                    ${escapeHtml(
                        ticket.ticket_number || "Unknown"
                    )}
                </strong>
            </div>

            <div class="ticket-answer-row">
                <span>Raised By</span>
                <strong>
                    ${escapeHtml(
                        ticket.requester || "Unknown"
                    )}
                </strong>
            </div>
        `;

    }

    else if (answerType === "CREATED_DATE") {

        content = `
            <div class="ticket-answer-header">
                <strong>
                    ${escapeHtml(
                        ticket.ticket_number || "Unknown"
                    )}
                </strong>
            </div>

            <div class="ticket-answer-row">
                <span>Created At</span>
                <strong>
                    ${escapeHtml(
                        ticket.created_at || "Unknown"
                    )}
                </strong>
            </div>
        `;
    }

    // ONE Open Ticket button only
    if (ticket.web_url) {

        content += `
            <div class="ticket-answer-footer">

                <a
                    href="${escapeHtml(ticket.web_url)}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    Open Ticket ↗
                </a>

            </div>
        `;
    }

    container.innerHTML = content;

    chatMessages.appendChild(container);

    scrollToBottom();

    saveChatHistory();
}

function addTicketSearchCards(tickets) {
    const container = document.createElement("div");
    container.className = "ticket-search-list";

    tickets.forEach(function(ticket) {
        const card = document.createElement("div");
        card.className = "ticket-search-card";

        const ticketUrl = ticket.web_url || "#";

        card.innerHTML = `
            <div class="ticket-search-header">
                <strong>
                    ${escapeHtml(ticket.ticket_number || "Unknown")}
                </strong>

                <span class="ticket-status-badge">
                    ${escapeHtml(ticket.status || "Unknown")}
                </span>
            </div>

            <div class="ticket-search-title">
                ${escapeHtml(ticket.title || "No title")}
            </div>

            <div class="ticket-search-meta">
                <span>
                    Priority:
                    <strong>
                        ${escapeHtml(ticket.priority || "Unknown")}
                    </strong>
                </span>
            </div>

            ${
                ticketUrl !== "#"
                    ? `
                    <div class="ticket-search-footer">
                        <a
                            href="${escapeHtml(ticketUrl)}"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            Open Ticket ↗
                        </a>
                    </div>
                    `
                    : ""
            }
        `;

        container.appendChild(card);
    });

    chatMessages.appendChild(container);

    scrollToBottom();
    saveChatHistory();
}

/* =========================
   APPLICATION SELECTOR
========================= */

const applicationSelectorButton =
    document.getElementById("application-selector-button");

const applicationDropdown =
    document.getElementById("application-dropdown");


if (applicationSelectorButton && applicationDropdown) {

    // Open / close when selector is clicked
    applicationSelectorButton.addEventListener(
        "click",
        function(event) {

            event.stopPropagation();

            applicationDropdown.classList.toggle("open");

            const arrow =
                applicationSelectorButton.querySelector(
                    ".application-selector-arrow"
                );

            if (arrow) {
                arrow.style.transform =
                    applicationDropdown.classList.contains("open")
                        ? "rotate(180deg)"
                        : "rotate(0deg)";
            }
        }
    );


    // Selected app determines both backend permission boundary and chat history.
    function refreshApplicationSelector() {
        const appButton = applicationDropdown.querySelector(`[data-application="${selectedVishakhaApp}"]`);
        const icon = appButton?.querySelector('span:first-child')?.textContent || '✦';
        const label = appButton?.querySelector('.application-dropdown-name')?.textContent || 'General';
        const selectedName = applicationSelectorButton.querySelector('.selected-app-name');
        const selectedIcon = applicationSelectorButton.querySelector('.selected-app-icon');
        if (selectedName) selectedName.textContent = label.trim();
        if (selectedIcon) selectedIcon.textContent = icon.trim();
        applicationDropdown.querySelectorAll('[data-application]').forEach(button =>
            button.classList.toggle('active', button.dataset.application === selectedVishakhaApp));
        chatInput.placeholder = selectedVishakhaApp === 'general'
            ? 'Ask anything in General...' : 'Ask about SEP tickets or actions...';
    }
    function switchApplication(nextApp) {
        if (!['general', 'ticketing'].includes(nextApp) || nextApp === selectedVishakhaApp) return;
        if (isAIResponding) { alert('Please stop the current response before switching applications.'); return; }
        saveChatHistory();
        selectedVishakhaApp = nextApp;
        localStorage.setItem(VISH_APP_KEY, selectedVishakhaApp);
        let chats = [];
        try { chats = JSON.parse(localStorage.getItem(CHAT_LIST_KEY) || '[]'); } catch (_) {}
        const lastId = localStorage.getItem(VISH_ACTIVE_APP_KEY(nextApp));
        const chosen = chats.find(c => c.id === lastId && applicationForChat(c) === nextApp)
            || chats.filter(c => applicationForChat(c) === nextApp)
                .sort((a,b) => new Date(b.updatedAt || 0) - new Date(a.updatedAt || 0))[0];
        activeChatId = chosen ? chosen.id : (nextApp === 'general' ? 'gen_' : 'sep_') + crypto.randomUUID();
        localStorage.setItem(ACTIVE_CHAT_KEY, activeChatId);
        localStorage.setItem(VISH_ACTIVE_APP_KEY(nextApp), activeChatId);
        chatMessages.replaceChildren();
        chatInput.value = '';
        if (chosen) {
            chatMessages.innerHTML = chosen.html || '';
            restoreButtonEvents();
            if (nextApp === 'ticketing') restoreConversationState();
        } else {
            addAIMessage(nextApp === 'general'
                ? 'General mode is ready. Ask a question, learn something, or draft a message.'
                : 'Service Excellence Portal is selected. I can help with tickets, status checks and analytics.');
            chatMessages.appendChild(renderApplicationSuggestions());
        }
        // Previously saved chats retain the suggestion buttons they had at the time.
        // Replace suggestions only for empty/start chats so a mode cannot show
        // another application's sample prompts.
        refreshApplicationSelector();
        renderRecentChats();
        scrollToBottom();
        applicationDropdown.classList.remove('open');
    }
    applicationDropdown.addEventListener('click', event => {
        event.stopPropagation();
        const item = event.target.closest('[data-application]');
        if (item && !item.disabled) switchApplication(item.dataset.application);
    });
    refreshApplicationSelector();


    // Close when clicking anywhere outside
    document.addEventListener(
        "click",
        function() {

            applicationDropdown.classList.remove("open");

            const arrow =
                applicationSelectorButton.querySelector(
                    ".application-selector-arrow"
                );

            if (arrow) {
                arrow.style.transform = "rotate(0deg)";
            }
        }
    );
}

/* =========================
   SIDEBAR COLLAPSE / EXPAND
========================= */

const sidebar =
    document.getElementById("sidebar");

const sidebarToggle =
    document.getElementById("sidebar-toggle");

const SIDEBAR_STATE_KEY =
    "darpan_sidebar_collapsed";


if (sidebar && sidebarToggle) {

    // Restore saved sidebar state
    const sidebarCollapsed =
        localStorage.getItem(SIDEBAR_STATE_KEY) === "true";

    if (sidebarCollapsed) {

        sidebar.classList.add("collapsed");

        sidebarToggle.setAttribute(
            "title",
            "Expand sidebar"
        );

        sidebarToggle.setAttribute(
            "aria-label",
            "Expand sidebar"
        );

    }


    // Collapse / expand
    sidebarToggle.addEventListener(
        "click",
        function() {

            const isCollapsed =
                sidebar.classList.toggle("collapsed");


            localStorage.setItem(
                SIDEBAR_STATE_KEY,
                isCollapsed ? "true" : "false"
            );


            if (isCollapsed) {

                sidebarToggle.setAttribute(
                    "title",
                    "Expand sidebar"
                );

                sidebarToggle.setAttribute(
                    "aria-label",
                    "Expand sidebar"
                );

            } else {

                sidebarToggle.setAttribute(
                    "title",
                    "Collapse sidebar"
                );

                sidebarToggle.setAttribute(
                    "aria-label",
                    "Collapse sidebar"
                );

            }

        }
    );
}

/* =========================
   COLLAPSED SIDEBAR ACTIONS
========================= */

const collapsedNewChat =
    document.getElementById("collapsed-new-chat");

const collapsedRecentChats =
    document.getElementById("collapsed-recent-chats");


if (collapsedNewChat) {

    collapsedNewChat.addEventListener(
        "click",
        function() {

            // Use the existing working
            // New Chat functionality
            const normalNewChatButton =
                document.getElementById(
                    "new-chat-button"
                );

            if (normalNewChatButton) {
                normalNewChatButton.click();
            }

        }
    );
}


if (
    collapsedRecentChats &&
    sidebar &&
    sidebarToggle
) {

    collapsedRecentChats.addEventListener(
        "click",
        function() {

            // Expand sidebar so Recent Chats
            // become visible
            sidebar.classList.remove("collapsed");

            localStorage.setItem(
                SIDEBAR_STATE_KEY,
                "false"
            );

            sidebarToggle.setAttribute(
                "title",
                "Collapse sidebar"
            );

            sidebarToggle.setAttribute(
                "aria-label",
                "Collapse sidebar"
            );

        }
    );
}

/* =========================
   LIGHT / DARK MODE
========================= */

const themeToggle =
    document.getElementById("theme-toggle");

const themeMoonIcon =
    document.getElementById("theme-moon-icon");

const themeSunIcon =
    document.getElementById("theme-sun-icon");

const THEME_STORAGE_KEY =
    "darpan_theme";


function applyTheme(theme) {

    const isDark = theme === "dark";

    document.body.classList.toggle(
        "dark-mode",
        isDark
    );


    if (themeMoonIcon) {
        themeMoonIcon.style.display =
            isDark ? "none" : "block";
    }


    if (themeSunIcon) {
        themeSunIcon.style.display =
            isDark ? "block" : "none";
    }


    if (themeToggle) {

        const label =
            isDark
                ? "Switch to light mode"
                : "Switch to dark mode";

        themeToggle.setAttribute(
            "title",
            label
        );

        themeToggle.setAttribute(
            "aria-label",
            label
        );
    }
}


/* Restore saved theme */

const savedTheme =
    localStorage.getItem(THEME_STORAGE_KEY);

applyTheme(
    savedTheme === "dark"
        ? "dark"
        : "light"
);


/* Toggle theme */

if (themeToggle) {

    themeToggle.addEventListener(
        "click",
        function() {

            const isCurrentlyDark =
                document.body.classList.contains(
                    "dark-mode"
                );

            const newTheme =
                isCurrentlyDark
                    ? "light"
                    : "dark";


            localStorage.setItem(
                THEME_STORAGE_KEY,
                newTheme
            );

            applyTheme(newTheme);
        }
    );
}

// =========================================================
// USER / PROFILE MENU
// =========================================================

const userMenuButton = document.getElementById(
    "user-menu-button"
);

const userDropdown = document.getElementById(
    "user-dropdown"
);


// Open / close user menu
if (userMenuButton && userDropdown) {

    userMenuButton.addEventListener(
        "click",
        function (event) {

            event.stopPropagation();

            userDropdown.classList.toggle("open");

        }
    );


    // Prevent clicks inside dropdown from closing it
    userDropdown.addEventListener(
        "click",
        function (event) {
            event.stopPropagation();
        }
    );


    // Close when clicking anywhere outside
    document.addEventListener(
        "click",
        function () {

            userDropdown.classList.remove("open");

        }
    );

}

/* =========================================================
   MULTILINE COMPOSER + OPTIONAL BROWSER VOICE DICTATION
   No audio is sent to the Django ticketing API.
   Recognition availability and processing depend on browser.
========================================================= */
(function setupVishakhaComposer() {
    if (!chatInput) return;
    function resizeComposer() {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(Math.max(chatInput.scrollHeight, 42), 224) + 'px';
    }
    chatInput.addEventListener('input', resizeComposer);
    resizeComposer();

    const mic = document.getElementById('voice-input-button');
    const status = document.getElementById('voice-input-status');
    if (!mic) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        mic.disabled = true;
        mic.title = 'Voice input is not supported by this browser';
        mic.setAttribute('aria-label', mic.title);
        if (status) status.textContent = 'Voice input is unavailable in this browser.';
        return;
    }

    let recognition;
    let listening = false;
    let confirmedText = '';
    let baseText = '';
    let audioStream = null;
    let audioContext = null;
    let analyser = null;
    let audioSource = null;
    let waveFrame = 0;
    let meterToken = 0;
    const voicePanel = document.getElementById('vishakha-dictation-panel');
    const bars = Array.from(document.querySelectorAll('#vishakha-voice-wave span'));
    const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    bars.forEach((bar, i) => bar.style.setProperty('--voice-index', String(i)));

    function updateDraft(previewText) {
        const segment = [confirmedText, previewText].filter(Boolean).join(' ').trim();
        const gap = baseText && segment && !/\s$/.test(baseText) ? ' ' : '';
        chatInput.value = baseText + gap + segment;
        chatInput.dispatchEvent(new Event('input', {bubbles: true}));
        chatInput.scrollTop = chatInput.scrollHeight;
    }

    function stopAudioMeter() {
        meterToken++;
        if (waveFrame) cancelAnimationFrame(waveFrame);
        waveFrame = 0;
        if (audioStream) { audioStream.getTracks().forEach(track => track.stop()); audioStream = null; }
        try { audioSource?.disconnect(); } catch (_) {}
        audioSource = null;
        analyser = null;
        if (audioContext) { audioContext.close().catch(() => {}); audioContext = null; }
        bars.forEach(bar => bar.style.setProperty('--voice-height', '6px'));
    }

    async function startAudioMeter() {
        const token = ++meterToken;
        if (!navigator.mediaDevices?.getUserMedia || !bars.length) return;
        let stream;
        try {
            stream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true}});
            if (!listening || token !== meterToken) { stream.getTracks().forEach(t => t.stop()); return; }
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (!AudioContextClass) { stream.getTracks().forEach(t => t.stop()); return; }
            audioStream = stream;
            audioContext = new AudioContextClass();
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 512;
            analyser.smoothingTimeConstant = .7;
            audioSource = audioContext.createMediaStreamSource(stream);
            audioSource.connect(analyser);
            const samples = new Uint8Array(analyser.frequencyBinCount);
            let smooth = 0;
            function draw() {
                if (!listening || token !== meterToken || !analyser) return;
                analyser.getByteFrequencyData(samples);
                let sum = 0;
                // Frequency range weighted toward human speech.
                const lower = 2, upper = Math.min(samples.length, 95);
                for (let i = lower; i < upper; i++) sum += samples[i];
                const intensity = Math.min(1, (sum / (upper - lower)) / 74);
                smooth = .62 * smooth + .38 * intensity;
                bars.forEach((bar, i) => {
                    const middle = (bars.length - 1) / 2;
                    const envelope = .2 + .8 * Math.pow(Math.max(0, 1 - Math.abs(i - middle) / (middle + 1)), .75);
                    const variation = .76 + .24 * Math.sin(i * 1.43 + performance.now() / 170);
                    const height = 6 + Math.round(43 * smooth * envelope * variation);
                    bar.style.setProperty('--voice-height', (prefersReducedMotion?.matches ? 6 + Math.round(25 * smooth * envelope) : height) + 'px');
                });
                waveFrame = requestAnimationFrame(draw);
            }
            draw();
        } catch (_) {
            // If level monitoring is denied/unavailable, speech recognition may still work.
            // The panel remains visible and shows restrained fallback movement.
            if (stream) stream.getTracks().forEach(t => t.stop());
            voicePanel?.classList.add('vishakha-meter-fallback');
        }
    }

    function setListening(value) {
        listening = value;
        mic.classList.toggle('recording', value);
        const wrapper = mic.closest('.chat-input-wrapper');
        wrapper?.classList.toggle('vishakha-listening', value);
        if (voicePanel) voicePanel.hidden = !value;
        const stop = document.getElementById('vishakha-voice-stop');
        if (stop) stop.hidden = !value;
        mic.setAttribute('aria-pressed', String(value));
        mic.setAttribute('aria-label', value ? 'Stop voice input' : 'Start voice input');
        mic.title = value ? 'Stop dictation' : 'Dictate a message';
        if (status) status.textContent = value ? 'Listening · live transcription' : '';
        if (!value) {
            stopAudioMeter();
            voicePanel?.classList.remove('vishakha-meter-fallback');
        }
    }

    mic.addEventListener('click', function () {
        if (listening) { recognition?.stop(); return; }
        try {
            recognition = new SpeechRecognition();
            recognition.lang = document.documentElement.lang || 'en-IN';
            recognition.continuous = false;
            recognition.interimResults = true;
            baseText = chatInput.value;
            confirmedText = '';
            recognition.onresult = function (event) {
                let finalTranscript = '';
                let interimTranscript = '';
                for (let i = 0; i < event.results.length; i++) {
                    const text = event.results[i][0]?.transcript || '';
                    if (event.results[i].isFinal) finalTranscript += text + ' ';
                    else interimTranscript += text + ' ';
                }
                confirmedText = finalTranscript.trim();
                updateDraft(interimTranscript.trim());
                if (status) status.textContent = interimTranscript.trim() ? 'Transcribing as you speak…' : 'Speech captured';
            };
            recognition.onerror = function (event) {
                const messages = {
                    'not-allowed': 'Microphone permission denied.',
                    'service-not-allowed': 'Speech recognition is not available.',
                    'audio-capture': 'No microphone was detected.',
                    'network': 'Voice recognition needs a connection in this browser.',
                    'no-speech': 'No speech detected. Try again.'
                };
                if (status) status.textContent = messages[event.error] || 'Voice input could not continue.';
            };
            recognition.onend = function () {
                setListening(false);
                if (confirmedText && status) status.textContent = 'Dictation complete · review and send';
            };
            recognition.start();
            setListening(true);
            startAudioMeter();
        } catch (error) {
            setListening(false);
            if (status) status.textContent = 'Unable to start microphone. Check browser permissions.';
        }
    });
    // Stop dictating when switching apps, starting a new chat, or navigating.
    document.addEventListener('click', function (event) {
        if (!listening || event.target.closest('#voice-input-button')) return;
        if (event.target.closest('#new-chat-button, [data-application], .new-chat-button, .recent-chat-item')) {
            recognition?.stop();
        }
    }, true);
    window.addEventListener('pagehide', () => { if (listening) recognition?.stop(); });
})();

/* Vishakha AI v4: sidebar branding and scoped chat search. */
(function () {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebar-toggle');
    document.getElementById('vishakha-expand-brand')?.addEventListener('click', function () {
        if (sidebar?.classList.contains('collapsed')) toggle?.click();
    });
    document.getElementById('vishakha-home-brand')?.addEventListener('click', function () {
        document.getElementById('darpan-tab-dashboard')?.click();
    });
    const search = document.getElementById('vishakha-chat-search');
    search?.addEventListener('input', function () { renderRecentChats(); });
    // Dialog-free stop for voice dictation, using same existing microphone action.
    document.getElementById('vishakha-voice-stop')?.addEventListener('click', function () {
        document.getElementById('voice-input-button')?.click();
    });
})();

// Restored chat HTML does not retain event listeners; reattach picker action via delegation.
document.addEventListener('click', function(event) {
    const button = event.target.closest('.vishakha-calendar-button');
    if (!button || button.dataset.bound === '1') return;
    const input = button.closest('.vishakha-date-picker-wrap')?.querySelector('input[type="date"],input[type="datetime-local"]');
    if (!input) return;
    if (input.showPicker) { try { input.showPicker(); return; } catch (_) {} }
    input.focus();
});
