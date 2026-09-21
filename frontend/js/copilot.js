/**
 * AI Travel Copilot — Chat UI Component
 * Handles open/close, message rendering, quick actions, and API calls.
 */

class TravelCopilot {
    constructor() {
        this.panel      = document.getElementById('copilot-panel');
        this.fab        = document.getElementById('copilot-fab');
        this.messagesEl = document.getElementById('copilot-messages');
        this.inputEl    = document.getElementById('copilot-input');
        this.sendBtn    = document.getElementById('copilot-send-btn');
        this.closeBtn   = document.getElementById('close-copilot');
        this.chipsEl    = document.getElementById('quick-chips');
        this.openBtn    = document.getElementById('open-copilot-btn');

        this.tripContext = null;
        this.isOpen     = false;
        this.isBusy     = false;

        this._bind();
        this._setDefaultChips();
    }

    // ── Public ───────────────────────────────────────────────────────────

    open() {
        this.isOpen = true;
        this.panel.hidden = false;
        this.panel.setAttribute('aria-hidden', 'false');
        this.fab.hidden = true;
        this.inputEl.focus();
    }

    close() {
        this.isOpen = false;
        this.panel.hidden = true;
        this.panel.setAttribute('aria-hidden', 'true');
        // Only restore FAB if we're on the results page (context has been set)
        if (this.fab && this.tripContext) this.fab.hidden = false;
    }

    toggle() { this.isOpen ? this.close() : this.open(); }

    setContext(ctx) {
        this.tripContext = ctx;
        if (ctx) this._setContextChips(ctx);
    }

    showFab() {
        if (this.fab) { this.fab.hidden = false; delete this.fab.dataset.hidden; }
    }

    // ── Private ──────────────────────────────────────────────────────────

    _bind() {
        this.fab?.addEventListener('click',     () => this.toggle());
        this.closeBtn?.addEventListener('click', () => this.close());
        this.openBtn?.addEventListener('click',  () => this.open());
        this.sendBtn?.addEventListener('click',  () => this._send());

        this.inputEl?.addEventListener('input', () => {
            // Auto-grow textarea
            this.inputEl.style.height = 'auto';
            this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 120) + 'px';
            // Enable/disable send button
            this.sendBtn.disabled = !this.inputEl.value.trim();
        });

        this.inputEl?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._send(); }
        });
    }

    _setDefaultChips() {
        const defaults = ['How do I choose a destination?', 'What budget do I need?', 'Best time to travel?', 'Required travel documents?'];
        this._renderChips(defaults);
    }

    _setContextChips(ctx) {
        const dest = ctx.destination_city || 'my destination';
        this._renderChips([
            `Top attractions in ${dest}?`,
            'How can I save money?',
            `What to pack for ${dest}?`,
            'Any visa requirements?',
        ]);
    }

    _renderChips(actions) {
        if (!this.chipsEl) return;
        this.chipsEl.innerHTML = actions.map(a =>
            `<button class="quick-chip" type="button">${a}</button>`
        ).join('');
        this.chipsEl.querySelectorAll('.quick-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                if (this.inputEl) { this.inputEl.value = chip.textContent; this.inputEl.dispatchEvent(new Event('input')); }
                this._send();
            });
        });
    }

    async _send() {
        const msg = this.inputEl?.value.trim();
        if (!msg || this.isBusy) return;

        this._addMessage('user', msg);
        this.inputEl.value = '';
        this.inputEl.style.height = 'auto';
        this.sendBtn.disabled = true;
        this._showTyping();
        this.isBusy = true;

        try {
            const { reply, suggested_actions } = await sendCopilotMessage(msg, this.tripContext);
            this._hideTyping();
            this._addMessage('bot', reply);
            if (suggested_actions?.length) this._renderChips(suggested_actions);
        } catch (err) {
            this._hideTyping();
            this._addMessage('bot', '⚠️ Connection error. Please try again.');
        } finally {
            this.isBusy = false;
        }
    }

    _addMessage(role, text) {
        if (!this.messagesEl) return;
        const el = document.createElement('div');
        el.className = `message ${role}`;
        el.innerHTML = `
            <div class="message-avatar">${role === 'bot' ? '🤖' : '🧑'}</div>
            <div class="message-bubble">${this._escHtml(text)}</div>`;
        this.messagesEl.appendChild(el);
        this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    }

    _showTyping() {
        if (!this.messagesEl) return;
        const el = document.createElement('div');
        el.id = 'typing-indicator';
        el.className = 'message bot';
        el.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-bubble typing-indicator">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>`;
        this.messagesEl.appendChild(el);
        this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    }

    _hideTyping() {
        document.getElementById('typing-indicator')?.remove();
    }

    _escHtml(s) {
        return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
                .replace(/\n/g,'<br>');
    }
}

// Instantiated in app.js after DOM ready
let copilot;
