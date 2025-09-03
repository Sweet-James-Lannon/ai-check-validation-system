/**
 * Chat.js - AI Chat Interface for Check Validation System
 * Handles real-time communication with Flask backend AI service
 */

class ChatInterface {
    constructor() {
        this.isWaitingForResponse = false;
        this.initializeElements();
        this.setupEventListeners();
        this.checkChatHealth();
        
        // Quick action mappings for realistic queries
        this.quickActions = {
            // === NL2SQL QUERIES (Structured Database Lookups) ===
            'Search by payee name': 'Show me all checks from ABC Corporation in the last 30 days',
            'Date range analysis': 'Find all transactions between $5,000-$50,000 processed in December 2024',
            'Amount threshold review': 'List the top 10 highest value checks that failed validation this quarter',
            'Transaction frequency': 'How many checks has Johnson & Associates submitted in the past 6 months?',
            
            // === VECTOR RAG QUERIES (Contextual Document Search) ===
            'Fraud pattern guidance': 'What are the key indicators of check fraud I should watch for in large transactions?',
            'Compliance best practices': 'What documentation is required when manually overriding a failed validation?',
            'Risk assessment help': 'How should I handle a check with unusual signatures but valid MICR encoding?',
            'Regulatory guidance': 'What are the current banking regulations for processing international corporate checks?'
        };
    }

    initializeElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendButton');
        this.charCount = document.getElementById('charCount');
        
        // Focus input on load
        if (this.chatInput) {
            this.chatInput.focus();
        }
    }

    setupEventListeners() {
        // Auto-resize textarea
        this.chatInput?.addEventListener('input', () => {
            this.chatInput.style.height = 'auto';
            this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
            this.charCount.textContent = `${this.chatInput.value.length}/500`;
        });

        // Send button click
        this.sendButton?.addEventListener('click', () => this.sendMessage());

        // Enter key to send (Shift+Enter for new line)
        this.chatInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Quick action buttons
        this.setupQuickActions();
    }

    setupQuickActions() {
        document.querySelectorAll('.btn-secondary').forEach(button => {
            button.addEventListener('click', () => {
                const text = button.textContent.trim();
                const suggestedQuery = this.quickActions[text] || `Help me ${text.toLowerCase()}`;
                
                this.chatInput.value = suggestedQuery;
                this.chatInput.focus();
                
                // Auto-resize textarea for longer queries
                this.chatInput.style.height = 'auto';
                this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
                this.charCount.textContent = `${this.chatInput.value.length}/500`;
            });
        });
    }

    addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'message-user' : 'message-assistant'}`;
        
        if (isUser) {
            messageDiv.innerHTML = `
                <div class="message-content">${this.escapeHtml(content)}</div>
                <div class="avatar avatar-user">
                    <i class="fa-solid fa-user w-4 h-4"></i>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="avatar avatar-assistant">
                    <i class="fa-solid fa-robot w-4 h-4"></i>
                </div>
                <div class="message-content">${this.formatAIResponse(content)}</div>
            `;
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    formatAIResponse(content) {
        // Convert markdown-style formatting to HTML
        let formatted = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
        
        return `<p>${formatted}</p>`;
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }

    addTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typingIndicator';
        typingDiv.className = 'message message-assistant';
        typingDiv.innerHTML = `
            <div class="avatar avatar-assistant">
                <i class="fa-solid fa-robot w-4 h-4"></i>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        this.chatMessages.appendChild(typingDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) indicator.remove();
    }

    showError(message) {
        this.addMessage(`⚠️ ${message}`, false);
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isWaitingForResponse) return;

        // Disable input while processing
        this.isWaitingForResponse = true;
        this.sendButton.disabled = true;
        this.sendButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin w-4 h-4"></i>';

        // Add user message to chat
        this.addMessage(message, true);
        
        // Clear input
        this.chatInput.value = '';
        this.chatInput.style.height = 'auto';
        this.charCount.textContent = '0/500';

        // Show typing indicator
        this.addTypingIndicator();

        try {
            // Send request to Flask backend
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();

            // Remove typing indicator
            this.removeTypingIndicator();

            if (response.ok && data.status === 'success') {
                // Add AI response
                this.addMessage(data.response, false);
            } else {
                // Handle error
                this.showError(data.error || 'Unable to process your request. Please try again.');
            }

        } catch (error) {
            console.error('Chat error:', error);
            this.removeTypingIndicator();
            this.showError('Connection error. Please check your internet connection and try again.');
        } finally {
            // Re-enable input
            this.isWaitingForResponse = false;
            this.sendButton.disabled = false;
            this.sendButton.innerHTML = '<i class="fa-solid fa-paper-plane w-4 h-4"></i>';
            this.chatInput.focus();
        }
    }

    async checkChatHealth() {
        try {
            const response = await fetch('/api/chat/health');
            const data = await response.json();
            
            if (!data.openai_connected) {
                console.warn('OpenAI connection issue detected');
            }
            
            console.log('Chat health status:', data.status);
        } catch (error) {
            console.error('Chat health check failed:', error);
        }
    }
}

// Initialize chat interface when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new ChatInterface();
});