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