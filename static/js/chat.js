// Add event listeners when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.querySelector('.chat-input button');
    const newChatBtn = document.getElementById('newChatBtn');
    let currentChatId = null;

    // Load chat history when the history tab is shown
    document.getElementById('history-tab').addEventListener('shown.bs.tab', loadChatHistory);

    // Handle new chat button click
    newChatBtn.addEventListener('click', startNewChat);

    // Send message when Enter is pressed (without Shift)
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Send message when button is clicked
    sendButton.addEventListener('click', sendMessage);
});

// Function to load chat history
async function loadChatHistory() {
    try {
        const response = await fetch('/api/chat-history');
        const data = await response.json();
        
        const historyList = document.getElementById('chatHistoryList');
        historyList.innerHTML = '';
        
        data.chats.forEach(chat => {
            const chatElement = document.createElement('div');
            chatElement.className = 'chat-history-item';
            chatElement.dataset.chatId = chat.id;
            
            // Get first message or use default text
            const firstMessage = chat.messages[0]?.content || 'Empty chat';
            const date = new Date(chat.created_at).toLocaleString();
            
            chatElement.innerHTML = `
                <div class="chat-preview">
                    <div class="chat-preview-content">
                        <h6 class="mb-1">${firstMessage}</h6>
                        <small class="text-muted">${date}</small>
                    </div>
                    <div class="chat-actions">
                        <button class="btn btn-sm btn-outline-danger delete-chat" title="Delete chat">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            `;
            
            // Add click event to load chat
            chatElement.addEventListener('click', (e) => {
                if (!e.target.closest('.delete-chat')) {
                    loadChat(chat.id);
                }
            });
            
            historyList.appendChild(chatElement);
        });
        
        // Add delete chat handlers
        document.querySelectorAll('.delete-chat').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const chatId = e.target.closest('.chat-history-item').dataset.chatId;
                await deleteChat(chatId);
            });
        });
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

// Function to load a specific chat
async function loadChat(chatId) {
    try {
        const response = await fetch(`/api/chat/${chatId}`);
        const data = await response.json();
        
        // Clear current chat
        const chatContainer = document.getElementById('chatContainer');
        chatContainer.innerHTML = '';
        
        // Set current chat ID
        currentChatId = chatId;
        
        // Load messages
        data.messages.forEach(message => {
            appendMessage(message.role, message.content);
        });
        
        // Switch to chat tab
        const chatTab = document.getElementById('chat-tab');
        bootstrap.Tab.getOrCreateInstance(chatTab).show();
    } catch (error) {
        console.error('Error loading chat:', error);
    }
}

// Function to start a new chat
function startNewChat() {
    currentChatId = null;
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.innerHTML = `
        <div class="welcome-message text-center">
            <i class="bi bi-stars"></i>
            <h3>Welcome to your AI DM Assistant!</h3>
            <p>Ask me anything about D&D, from rules to story ideas.</p>
        </div>
    `;
}

// Function to delete a chat
async function deleteChat(chatId) {
    if (!confirm('Are you sure you want to delete this chat?')) return;
    
    try {
        await fetch(`/api/chat/${chatId}`, {
            method: 'DELETE'
        });
        
        // Reload chat history
        loadChatHistory();
        
        // If the deleted chat was the current one, start a new chat
        if (currentChatId === chatId) {
            startNewChat();
        }
    } catch (error) {
        console.error('Error deleting chat:', error);
    }
}

// Modified sendMessage function to handle chat history
async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Get selected prompts
    const selectedPrompts = [];
    document.querySelectorAll('.prompt-selector input[type="checkbox"]:checked').forEach(checkbox => {
        const promptId = checkbox.value;
        const promptTitle = checkbox.nextElementSibling.textContent.trim();
        const promptContent = document.querySelector(`#promptsList .prompt-card[data-id="${promptId}"] p`)?.textContent.trim();
        selectedPrompts.push({
            id: promptId,
            title: promptTitle,
            content: promptContent
        });
    });
    
    // Add user message to chat
    appendMessage('user', message);
    messageInput.value = '';
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                selected_prompts: selectedPrompts,
                chat_id: currentChatId
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            appendMessage('error', data.error);
        } else {
            // Update current chat ID if this is a new chat
            if (!currentChatId && data.chat_id) {
                currentChatId = data.chat_id;
            }
            
            // Append AI's text response
            appendMessage('assistant', data.response);
            
            // Append images if they exist
            if (data.user_image_url) {
                appendImage('User prompt:', data.user_image_url);
            }
            if (data.ai_image_url) {
                appendImage('AI response:', data.ai_image_url);
            }
        }
    } catch (error) {
        console.error('Error:', error);
        appendMessage('error', 'Failed to send message. Please try again.');
    }
}

// Helper function to append messages
function appendMessage(role, content) {
    const messagesContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    // Convert URLs to clickable links
    const contentWithLinks = content.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    
    messageDiv.innerHTML = `
        <div class="message-content">
            ${contentWithLinks}
        </div>
    `;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Helper function to append images
function appendImage(caption, imageUrl) {
    const messagesContainer = document.getElementById('chatContainer');
    const imageDiv = document.createElement('div');
    imageDiv.className = 'message image-message';
    imageDiv.innerHTML = `
        <div class="message-content">
            <div class="image-caption">${caption}</div>
            <img src="${imageUrl}" alt="Generated image" class="img-fluid">
        </div>
    `;
    messagesContainer.appendChild(imageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function generateImage() {
    const promptInput = document.getElementById('image-prompt');
    const prompt = promptInput.value.trim();
    
    if (!prompt) return;
    
    const imageContainer = document.getElementById('generated-image');
    imageContainer.innerHTML = '<div class="loading">Generating image...</div>';
    
    try {
        const response = await fetch('/api/generate-image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: prompt,
                model: window.modelUtils.getSelectedImageModel()
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            imageContainer.innerHTML = `<div class="error">${data.error}</div>`;
        } else {
            imageContainer.innerHTML = `<img src="${data.image_url}" alt="Generated image" class="img-fluid">`;
        }
    } catch (error) {
        console.error('Error:', error);
        imageContainer.innerHTML = '<div class="error">Failed to generate image. Please try again.</div>';
    }
}