(function () {
    const box = document.createElement("div");
    box.id = "lm-chat";
    box.innerHTML = `
      <button id="lm-open" type="button">Ask our AI assistant</button>
      <section id="lm-panel" hidden>
        <header>
          <strong>Lemora AI assistant</strong>
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
    try { conversationId = localStorage.getItem("lm_conversation"); } catch (e) {}
  
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
  
    document.getElementById("lm-open").onclick = function () {
      panel.hidden = false;
      if (!log.children.length) addText("bot", "Hi! Tell me what you're looking for and I'll suggest products.");
      input.focus();
    };
    document.getElementById("lm-close").onclick = function () { panel.hidden = true; };
  
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
        try { localStorage.setItem("lm_conversation", conversationId); } catch (e) {}
        addCards(data.products || []);
      } catch (e) {
        waiting.textContent = "Sorry, something went wrong. You can still browse the store with the filters.";
      }
    };
  })();