from g4f.client import Client
from models import db, ChatSession, ChatMessage, GeneratedImage
from utils.prompt_utils import get_system_prompt, get_user_prompt

class ChatService:
    def __init__(self):
        self.client = Client()
    
    def process_chat_message(self, user_id, message, selected_prompts=None, session_id=None):
        """Process chat message and generate AI response"""
        try:
            # Handle chat session
            if session_id:
                session = ChatSession.query.filter_by(id=session_id, user_id=user_id).first()
            else:
                session_name = message[:50] if message else None
                session = ChatSession(user_id=user_id, session_name=session_name)
                db.session.add(session)
                db.session.commit()
            
            # Save user message
            user_msg = ChatMessage(
                session_id=session.id,
                user_id=user_id,
                role='user',
                content=message
            )
            db.session.add(user_msg)
            db.session.commit()
            
            # Generate AI response
            ai_response = self._generate_ai_response(message, selected_prompts, session.id)
            
            # Save AI message
            ai_msg = ChatMessage(
                session_id=session.id,
                user_id=user_id,
                role='assistant',
                content=ai_response
            )
            db.session.add(ai_msg)
            db.session.commit()
            
            # Generate images asynchronously
            images = self._generate_chat_images(user_id, message, ai_response, selected_prompts)
            
            return {
                "response": ai_response,
                "session_id": session.id,
                **images
            }
            
        except Exception as e:
            print(f"Chat service error: {str(e)}")
            raise
    
    def _generate_ai_response(self, message, selected_prompts=None, session_id=None):
        """Generate AI response using g4f with conversation history"""
        system_message = get_system_prompt()
        user_prompt = get_user_prompt()
        
        combined_prompt = f"{system_message}\n\n{user_prompt}"
        
        if selected_prompts:
            prompt_contents = [p.get('content', '') for p in selected_prompts if p.get('content')]
            if prompt_contents:
                combined_prompt += f"\n\nVery important context: {' '.join(prompt_contents)}"
        
        # Build messages array with conversation history
        messages = [{"role": "system", "content": combined_prompt}]
        
        # Add conversation history if session_id is provided
        if session_id:
            # Get previous messages from this session (excluding the current user message)
            previous_messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at).all()
            
            # Add previous messages to the conversation
            for msg in previous_messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        if not response.choices:
            raise Exception("No response generated")
        
        return response.choices[0].message.content
    
    def _generate_chat_images(self, user_id, user_message, ai_response, selected_prompts=None):
        """Generate images for chat messages"""
        try:
            # Generate user message image
            user_image_prompt = self._enhance_image_prompt(user_message, selected_prompts)
            user_image_response = self.client.images.generate(
                model="sdxl-1.0",
                prompt=user_image_prompt,
                response_format="url"
            )
            
            user_image = GeneratedImage(
                url=user_image_response.data[0].url,
                prompt=user_image_prompt,
                user_id=user_id,
                source='chat'
            )
            db.session.add(user_image)
            
            # Generate AI response image
            ai_image_prompt = self._enhance_image_prompt(f"Dungeons and Dragons scene: {ai_response}", selected_prompts)
            ai_image_response = self.client.images.generate(
                model="sdxl-1.0",
                prompt=ai_image_prompt,
                response_format="url"
            )
            
            ai_image = GeneratedImage(
                url=ai_image_response.data[0].url,
                prompt=ai_image_prompt,
                user_id=user_id,
                source='chat'
            )
            db.session.add(ai_image)
            db.session.commit()
            
            return {
                "user_image_url": user_image_response.data[0].url,
                "ai_image_url": ai_image_response.data[0].url
            }
            
        except Exception as e:
            print(f"Image generation error: {str(e)}")
            return {}
    
    def _enhance_image_prompt(self, prompt, selected_prompts=None):
        """Enhance image prompt with D&D context and selected prompts"""
        enhanced_prompt = prompt
        
        if selected_prompts:
            prompt_contents = [p.get('content', '') for p in selected_prompts if p.get('content')]
            if prompt_contents:
                enhanced_prompt = f"Style and details: {' '.join(prompt_contents)}. {enhanced_prompt}"
        
        # Add D&D context
        system_context = get_system_prompt()
        if "D&D" in system_context or "Dungeons and Dragons" in system_context:
            enhanced_prompt = f"Use a color palette and rich colors. Dungeons and Dragons themed scene, fantasy RPG style: {enhanced_prompt}"
        
        return enhanced_prompt 
