// Model selection functionality
let availableModels = {
    text_models: {},
    image_models: {}
};

// Fetch available models when the page loads
async function fetchAvailableModels() {
    try {
        const response = await fetch('/api/available-models');
        const data = await response.json();
        availableModels = data;
        updateModelSelectors();
    } catch (error) {
        console.error('Error fetching available models:', error);
    }
}

// Update model selectors in the UI
function updateModelSelectors() {
    // Update text model selector
    const textModelSelect = document.getElementById('text-model-select');
    if (textModelSelect) {
        textModelSelect.innerHTML = '';
        Object.entries(availableModels.text_models).forEach(([value, label]) => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = label;
            textModelSelect.appendChild(option);
        });
    }

    // Update image model selector
    const imageModelSelect = document.getElementById('image-model-select');
    if (imageModelSelect) {
        imageModelSelect.innerHTML = '';
        Object.entries(availableModels.image_models).forEach(([value, label]) => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = label;
            imageModelSelect.appendChild(option);
        });
    }
}

// Initialize model selection when the page loads
document.addEventListener('DOMContentLoaded', fetchAvailableModels);

// Export functions for use in other files
window.modelUtils = {
    getSelectedTextModel: () => document.getElementById('text-model-select')?.value || 'gpt-4',
    getSelectedImageModel: () => document.getElementById('image-model-select')?.value || 'flux'
}; 