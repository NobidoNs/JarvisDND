from models import db, Prompt

class PromptService:
    @staticmethod
    def get_user_prompts(user_id):
        """Get all prompts for a user"""
        return Prompt.query.filter_by(user_id=user_id).all()
    
    @staticmethod
    def create_prompt(user_id, title, content):
        """Create a new prompt"""
        prompt = Prompt(
            title=title,
            content=content,
            user_id=user_id
        )
        db.session.add(prompt)
        db.session.commit()
        return prompt
    
    @staticmethod
    def update_prompt(prompt_id, user_id, title, content):
        """Update an existing prompt"""
        prompt = Prompt.query.filter_by(id=prompt_id, user_id=user_id).first()
        if prompt:
            prompt.title = title
            prompt.content = content
            db.session.commit()
        return prompt
    
    @staticmethod
    def delete_prompt(prompt_id, user_id):
        """Delete a prompt"""
        prompt = Prompt.query.filter_by(id=prompt_id, user_id=user_id).first()
        if prompt:
            db.session.delete(prompt)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_prompt_by_id(prompt_id, user_id):
        """Get prompt by ID"""
        return Prompt.query.filter_by(id=prompt_id, user_id=user_id).first() 