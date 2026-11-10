(function () {
  const GREETING = "Hi! Tell me what you're looking for and I'll suggest products.";

  const box = document.createElement("div");
  box.id = "lm-chat";
  box.innerHTML = `
    <button id="lm-open" type="button">Ask our AI assistant</button>
    <section id="lm-panel" hidden>
      <header>
        <strong>Lemora AI assistant</strong>
        <button id="lm-new" type="button">New chat</button>
        <button id="lm-close" type="button" aria-label="Close">×</button>
      </header>
      <p class="lm-note">AI-generated suggestions. Prices and details come from our catalogue.</p>
      <div id="lm-log"></div>
      <form id="lm-form">
        <input id="lm-input" maxlength="500" placeholder="e.g. a serum for dry skin" autocomplete="off" required>
        <button type="submit">Send</button>
      </form>
    </section>`;
  document.body.appendChild(box);

  const panel = document.getElementById("lm-panel");
  const log = document.getElementById("lm-log");
  const form = document.getElementById("lm-form");
  const input = document.getElementById("lm-input");

  let conversationId = null;
  try { conversationId = sessionStorage.getItem("lm_conversation"); } catch (e) {}

  function addText(role, text) {
    const div = document.createElement("div");
    div.className = "lm-msg lm-" + role;
    div.textContent = text;          // textContent, never innerHTML: shows text as text, not code
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  function addCards(products) {
    products.forEach(function (p) {
      const a = document.createElement("a");
      a.className = "lm-card";
      a.href = "/product/" + encodeURIComponent(p.sku_id);
      const brand = document.createElement("small");
      brand.textContent = p.brand;
      const name = document.createElement("span");
      name.textContent = p.name;
      const price = document.createElement("b");
      price.textContent = "S$" + p.price_sgd;
      a.append(brand, name, price);
      log.appendChild(a);
    });
    log.scrollTop = log.scrollHeight;
  }

  function sendFeedback(messageId, verdict, text) {
    return fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_id: messageId, verdict: verdict, correction_text: text }),
    });
  }

  function addFeedback(messageId) {
    const row = document.createElement("div");
    row.className = "lm-feedback";
    [["accepted", "👍 Helpful"], ["corrected", "✏️ Not quite"], ["rejected", "👎 Wrong"]].forEach(function (c) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = c[1];
      b.onclick = async function () {
        let text = null;
        if (c[0] === "corrected") {
          text = prompt("What should it have said or suggested?");
          if (!text) return;
          text = text.slice(0, 500);
        }
        try {
          const res = await sendFeedback(messageId, c[0], text);
          row.textContent = res.ok ? "Thanks for the feedback!" : "Sorry, we couldn't save that.";
        } catch (e) {
          row.textContent = "Sorry, we couldn't save that.";
        }
      };
      row.appendChild(b);
    });
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }

  document.getElementById("lm-open").onclick = function () {
    panel.hidden = false;
    try { sessionStorage.setItem("lm_open", "1"); } catch (e) {}
    if (!log.children.length) addText("bot", GREETING);
    input.focus();
  };

  document.getElementById("lm-close").onclick = function () {
    panel.hidden = true;
    try { sessionStorage.setItem("lm_open", "0"); } catch (e) {}
  };

  document.getElementById("lm-new").onclick = function () {
    conversationId = null;
    try { sessionStorage.removeItem("lm_conversation"); } catch (e) {}
    log.textContent = "";
    addText("bot", GREETING);
  };

  async function restore() {
    if (conversationId) {
      try {
        const res = await fetch("/api/history?conversation_id=" + encodeURIComponent(conversationId));
        const data = await res.json();
        data.messages.forEach(function (m) {
          addText(m.role === "user" ? "user" : "bot", m.message);
          if (m.role === "assistant") addCards(m.products || []);
        });
      } catch (e) {}
    }
    try { if (sessionStorage.getItem("lm_open") === "1") panel.hidden = false; } catch (e) {}
    if (!panel.hidden && !log.children.length) addText("bot", GREETING);
  }
  restore();

  form.onsubmit = async function (event) {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    addText("user", text);
    const waiting = addText("bot", "Thinking…");
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: conversationId }),
      });
      const data = await res.json();
      waiting.textContent = data.message;
      if (!res.ok) return;
      conversationId = data.conversation_id;
      try { sessionStorage.setItem("lm_conversation", conversationId); } catch (e) {}
      addCards(data.products || []);
      addFeedback(data.message_id);
    } catch (e) {
      waiting.textContent = "Sorry, something went wrong. You can still browse the store with the filters.";
    }
  };
})();