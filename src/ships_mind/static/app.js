async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

function formatDate(value) {
  if (!value) {
    return "pending";
  }

  return new Date(value).toLocaleString();
}

function renderCurrentItem(question) {
  const name = question.sender_name || "Unlisted";
  const sentAt = question.sent_at ? ` TX ${formatDate(question.sent_at)}` : " TX pending";

  return `
    <li class="terminal-row status-${question.status}">
      <div class="row-top">
        <strong>${formatDate(question.created_at)}</strong>
        <span class="status-tag">${question.status}</span>
      </div>
      <div class="terminal-copy"><span class="muted">${name}</span> :: ${question.text}</div>
      <div class="meta">${sentAt}</div>
    </li>
  `;
}

function renderAnswered(question) {
  const name = question.sender_name || "Unlisted";
  return `
    <li class="terminal-row">
      <div class="row-top">
        <strong>${formatDate(question.answered_at)}</strong>
        <span class="status-tag">answered</span>
      </div>
      <div class="terminal-copy"><span class="muted">${name}</span> :: ${question.text}</div>
      <div class="reply">CORE :: ${question.reply_text || ""}</div>
    </li>
  `;
}

async function refreshState() {
  const state = await requestJson("/api/state");

  const coreStatus = document.getElementById("core-status");
  coreStatus.textContent = state.responder_id ? "SHIPS CORE ACTIVE" : "REFERENCE LISTENING";
  coreStatus.style.color = state.responder_id ? "var(--ok)" : "var(--accent-warm)";

  const currentQuestions = state.current_questions.slice(0, 18);
  const answeredQuestions = state.answered_questions.slice(0, 18);

  document.getElementById("queue-count").textContent = `${currentQuestions.length} records`;
  document.getElementById("current-list").innerHTML =
    currentQuestions.map(renderCurrentItem).join("") || '<li class="muted terminal-empty">No current questions in the queue.</li>';
  document.getElementById("answered-list").innerHTML =
    answeredQuestions.map(renderAnswered).join("") || '<li class="muted terminal-empty">No archived responses recorded yet.</li>';
}

async function handleQuestionSubmit(event) {
  event.preventDefault();

  const senderName = document.getElementById("sender-name");
  const questionText = document.getElementById("question-text");

  await requestJson("/api/questions", {
    method: "POST",
    body: JSON.stringify({
      sender_name: senderName.value || "Unlisted",
      text: questionText.value,
    }),
  });

  questionText.value = "";
  await refreshState();
}

document.getElementById("question-form").addEventListener("submit", (event) => {
  handleQuestionSubmit(event).catch((error) => window.alert(error.message));
});

refreshState().catch((error) => console.error(error));
setInterval(() => refreshState().catch((error) => console.error(error)), 3000);
