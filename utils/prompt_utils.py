import sys
from typing import Dict, List, Optional

def get_system_prompt():
    """Read system prompt from prompts/system.txt file"""
    try:
        with open('prompts/system.txt', 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        print(f"Error reading system prompt: {e}")
        return ""

def get_user_prompt():
    """Read user prompt from prompts/user_prompt.txt file"""
    try:
        with open('prompts/user_prompt.txt', 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        print(f"Error reading user prompt: {e}")
        return "" 

def enhance_image_prompt(
        prompt: str, selected_prompts: Optional[List[Dict]] = None
    ) -> str:

        with open('image_promt.txt', 'r') as file:
            system_context = file.read()

        enhanced_prompt = prompt
        if selected_prompts:
            prompt_contents = [p.get("content", "") for p in selected_prompts if p.get("content")]
            if prompt_contents:
                enhanced_prompt = f"Style and details: {' '.join(prompt_contents)}. {enhanced_prompt}"

        enhanced_prompt = f"{system_context}. {enhanced_prompt}"
        return enhanced_prompt