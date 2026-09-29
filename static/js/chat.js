const chatInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const chatMessages = document.getElementById("chat-area");
const CHAT_HISTORY_KEY = "darpan_chat_history";

/* =========================================================
   USER MESSAGE
========================================================= */

function addUserMessage(message) {

    const messageDiv = document.createElement("div");

    messageDiv.className = "message user-message";

    messageDiv.innerHTML = `
        <div class="message-bubble">
            <p>${escapeHtml(message)}</p>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    saveChatHistory();

    scrollToBottom();
}


/* =========================================================
   AI MESSAGE
========================================================= */

function addAIMessage(message) {

    const messageDiv = document.createElement("div");

    messageDiv.className = "message ai-message";

    messageDiv.innerHTML = `
        <div class="avatar">
            AI
        </div>

        <div class="message-bubble">
            <p>${escapeHtml(message)}</p>
        </div>
    `;

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

    container.appendChild(input);
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
    if (ticket.request_type === "Incident Request") {
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
    }

    // IT contact details
    if (ticket.department === "IT") {
        detailsHTML += `
            ${detailRow("Email", ticket.email)}
            ${detailRow("Phone", ticket.phone)}
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

                <button class="cancel-button">
                    Cancel
                </button>

            </div>

        </div>
    `;

    const confirmButton =
        container.querySelector(".confirm-button");

    const cancelButton =
        container.querySelector(".cancel-button");

    // CONFIRM
    confirmButton.addEventListener("click", function() {
        disableButtons(container);
        sendOption("Confirm & Create Ticket");
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

function addLoadingMessage() {

    const messageDiv = document.createElement("div");

    messageDiv.id = "ai-loading";

    messageDiv.className = "message ai-message";

    messageDiv.innerHTML = `
        <div class="avatar">
            AI
        </div>

        <div class="message-bubble">
            <p>Thinking...</p>
        </div>
    `;

    chatMessages.appendChild(messageDiv);

    scrollToBottom();
}


function removeLoadingMessage() {

    const loadingMessage =
        document.getElementById("ai-loading");

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

    localStorage.setItem(
        CHAT_HISTORY_KEY,
        chatMessages.innerHTML
    );
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

}

function restoreChatHistory() {

    const history =
        localStorage.getItem(
            CHAT_HISTORY_KEY
        );

    if (!history) {

        return false;

    }

    chatMessages.innerHTML =
        history;

    restoreButtonEvents();

    scrollToBottom();

    return true;
}


function clearChatHistory() {

    localStorage.removeItem(
        CHAT_HISTORY_KEY
    );

    chatMessages.innerHTML = "";

}

/* =========================================================
   SEND NORMAL MESSAGE
========================================================= */

async function sendMessage() {

    const message = chatInput.value.trim();

    if (!message) {
        return;
    }

    addUserMessage(message);

    chatInput.value = "";

    await sendToBackend(message, "text");
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

                        message_type:
                            messageType

                    })
                }
            );


        const data =
            await response.json();


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

        addAIMessage(
            "Sorry, I could not connect to the AI service."
        );

        console.error(error);

    }
}


/* =========================================================
   HANDLE AI RESPONSE
========================================================= */

function handleAIResponse(result) {

    if (!result) {

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

        addAIMessage(result.message);


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

    if (result.type === "ticket_search") {
        addAIMessage(result.message);

        if (result.tickets && result.tickets.length > 0) {
            addTicketSearchCards(result.tickets);
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

    if (result.type === "ticket_status") {

        addAIMessage(result.message);

        if (result.tickets && result.tickets.length > 0) {

            addTicketStatusCards(result.tickets);

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
function setupSuggestionButtons(container) {

    const suggestionButtons =
        container.querySelectorAll(
            "button"
        );

    suggestionButtons.forEach(function(button) {

        button.addEventListener(
            "click",
            function() {

                const message =
                    button.textContent.trim();

                addUserMessage(
                    message
                );

                sendToBackend(
                    message,
                    "text"
                );

            }
        );

    });

}


function setupSuggestions() {

    const suggestions =
        document.querySelector(
            ".suggestions"
        );

    if (!suggestions) {

        return;

    }

    setupSuggestionButtons(
        suggestions
    );

}


/* =========================================================
   SEND BUTTON
========================================================= */

sendButton.addEventListener(
    "click",
    sendMessage
);


/* =========================================================
   ENTER KEY
========================================================= */

chatInput.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {

            event.preventDefault();

            sendMessage();

        }

    }
);
async function restoreConversationState() {

    try {

        const response =
            await fetch(
                "/api/chat/state/"
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

        if (
            data.type === "question" &&
            !document.querySelector(
                ".ai-options"
            )
        ) {

            addAIMessage(
                data.message
            );

            addOptionButtons(
                data.options
            );

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

        const response =
            await fetch(
                "/api/chat/new/",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    }
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


        /* Clear browser chat */

        localStorage.removeItem(
            CHAT_HISTORY_KEY
        );


        /* Clear visible chat */

        chatMessages.innerHTML = "";


        /* Show initial AI message */

        addAIMessage(
            "Hello! 👋\n\n" +
            "I'm your Darpan AI Employee Assistant.\n\n" +
            "I can help you perform tasks across your company applications.\n\n" +
            "Currently, the Ticketing application is available."
        );


        /* Show suggestions */

        const suggestions =
            document.createElement("div");

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

        saveChatHistory();

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

restoreChatHistory();

restoreConversationState();


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