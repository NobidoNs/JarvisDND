// Add event listeners when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.querySelector('.chat-input button');

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

async function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
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
                model: window.modelUtils.getSelectedTextModel()
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            appendMessage('error', data.error);
        } else {
            // Append AI's text response
            appendMessage('assistant', data.response);
            
            // Append both images if they exist
            if (data.user_image_url) {
                appendImage(data.user_image_url);
            }
            if (data.ai_image_url) {
                appendImage('AI:', data.user_image_url);
            }
        }
    } catch (error) {
        console.error('Error:', error);
        appendMessage('error', 'Failed to send message. Please try again.');
    }
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

function appendMessage(role, content) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    // Convert URLs to clickable links
    const contentWithLinks = content.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    
    messageDiv.innerHTML = contentWithLinks;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function appendImage(caption, imageUrl) {
    const messagesContainer = document.getElementById('chat-messages');
    const imageDiv = document.createElement('div');
    imageDiv.className = 'message image';
    imageDiv.innerHTML = `
        <div class="image-caption">${caption}</div>
        <img src="${imageUrl}" alt="Generated image" class="img-fluid">
    `;
    messagesContainer.appendChild(imageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
} 