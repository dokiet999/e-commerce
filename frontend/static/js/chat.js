/**
 * Chat Module — AI consultation chatbot UI logic
 */
const chatModule = {
    sessionId: null,
    isOpen: false,
    isLoading: false,

    init() {
        this.widget = document.getElementById('chatWidget');
        this.toggle = document.getElementById('chatToggle');
        this.closeBtn = document.getElementById('chatClose');
        this.messages = document.getElementById('chatMessages');
        this.input = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('chatSend');

        if (!this.widget) return;

        this.toggle.addEventListener('click', () => this.toggleChat());
        this.closeBtn.addEventListener('click', () => this.toggleChat());
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Load existing session
        this.sessionId = localStorage.getItem('chat_session_id');
        if (this.sessionId) {
            this.loadHistory();
        }
    },

    toggleChat() {
        this.isOpen = !this.isOpen;
        this.widget.classList.toggle('open', this.isOpen);
        this.toggle.classList.toggle('hidden', this.isOpen);
        if (this.isOpen) {
            this.input.focus();
            this.scrollToBottom();
        }
    },

    async sendMessage() {
        const message = this.input.value.trim();
        if (!message || this.isLoading) return;

        this.input.value = '';
        this.addMessage('user', message);
        this.setLoading(true);

        try {
            const data = await api.sendChatMessage(message, this.sessionId);
            this.sessionId = data.chat_session_id;
            localStorage.setItem('chat_session_id', this.sessionId);
            this.addMessage('assistant', data.response, data.sources);
        } catch (e) {
            this.addMessage('assistant', 'Xin lỗi, đã xảy ra lỗi. Vui lòng thử lại.');
        }

        this.setLoading(false);
    },

    addMessage(role, content, sources = null) {
        const div = document.createElement('div');
        div.className = `chat-msg chat-msg-${role}`;

        let html = `<div class="chat-msg-content">${this.formatContent(content)}</div>`;

        // Show product cards from sources
        if (sources && sources.length > 0) {
            const productSources = sources
                .filter(s => s.source_type === 'product' && s.product_name);
            const graphSources = sources
                .filter(s => s.source_type === 'graph_qa');

            if (productSources.length > 0) {
                const cards = productSources.map(s => {
                    const link = s.product_id ? `/product/${s.product_id}/` : '#';
                    return `<a href="${link}" class="chat-product-card">
                        <span class="chat-product-icon">📦</span>
                        <span class="chat-product-name">${s.product_name}</span>
                    </a>`;
                }).join('');
                html += `<div class="chat-product-list">${cards}</div>`;
            }

            if (graphSources.length > 0 && graphSources[0].cypher) {
                html += `<div class="chat-graph-badge" title="Cypher: ${graphSources[0].cypher}">
                    <span class="chat-graph-icon">🔗</span> Knowledge Graph
                </div>`;
            }
        }

        div.innerHTML = html;
        this.messages.appendChild(div);
        this.scrollToBottom();
    },

    formatContent(text) {
        // Basic markdown: bold, italic, lists
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n- /g, '\n• ')
            .replace(/\n/g, '<br>');
    },

    setLoading(loading) {
        this.isLoading = loading;
        this.sendBtn.disabled = loading;
        if (loading) {
            const loader = document.createElement('div');
            loader.className = 'chat-msg chat-msg-assistant chat-loading';
            loader.innerHTML = '<div class="chat-msg-content"><span class="chat-dots"><span>.</span><span>.</span><span>.</span></span></div>';
            loader.id = 'chatLoader';
            this.messages.appendChild(loader);
            this.scrollToBottom();
        } else {
            document.getElementById('chatLoader')?.remove();
        }
    },

    scrollToBottom() {
        this.messages.scrollTop = this.messages.scrollHeight;
    },

    async loadHistory() {
        try {
            const data = await api.getChatHistory(this.sessionId);
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    this.addMessage(msg.role, msg.content);
                });
            }
        } catch (e) {
            // No history, that's fine
        }
    },

    clearSession() {
        this.sessionId = null;
        localStorage.removeItem('chat_session_id');
        if (this.messages) {
            this.messages.innerHTML = `
                <div class="chat-msg chat-msg-assistant">
                    <div class="chat-msg-content">
                        Xin chào! 👋 Tôi là trợ lý tư vấn mua sắm AI của eCommerceStore.
                        Bạn cần tôi hỗ trợ gì?
                    </div>
                </div>`;
        }
    },
};

document.addEventListener('DOMContentLoaded', () => {
    chatModule.init();
});
