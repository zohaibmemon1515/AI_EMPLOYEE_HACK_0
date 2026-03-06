#!/usr/bin/env python3
"""
AI Draft Reply Generator - Using OpenAI Agent SDK with Gemini API.

Generates smart, context-aware draft replies for WhatsApp messages.
Supports both OpenAI and Google Gemini models.
"""

import os
from pathlib import Path
from typing import Optional
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Try to import required libraries
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AIDraftReplyGenerator:
    """Generates AI-powered draft replies using OpenAI SDK or Gemini API."""

    def __init__(self, provider: str = None):
        """
        Initialize AI draft generator.
        
        Args:
            provider: 'openai', 'gemini', or 'auto' (auto-detect)
        """
        # Auto-detect provider if not specified
        if provider is None or provider == 'auto':
            gemini_key = os.getenv('GEMINI_API_KEY')
            openai_key = os.getenv('OPENAI_API_KEY')
            
            if gemini_key:
                provider = 'gemini'
            elif openai_key:
                provider = 'openai'
            else:
                provider = 'template'
        
        self.provider = provider
        self.client = None
        self.model = None
        self.available = False
        
        # Initialize based on provider
        if provider == 'gemini' and GEMINI_AVAILABLE:
            self._init_gemini()
        elif provider == 'openai' and OPENAI_AVAILABLE:
            self._init_openai()
        else:
            print(f"   ⚠️  AI provider '{provider}' not available - using template fallback")
            print("      Install: pip install openai google-generativeai")
            print("      Or set GEMINI_API_KEY / OPENAI_API_KEY in .env")

    def _init_gemini(self):
        """Initialize Google Gemini API."""
        api_key = os.getenv('GEMINI_API_KEY')

        if not api_key:
            print("   ⚠️  GEMINI_API_KEY not found in .env")
            return

        try:
            genai.configure(api_key=api_key)

            # Try multiple model names in order of preference
            model_names = [
                'gemini-1.5-flash-latest',  # Latest flash model
                'gemini-1.5-pro-latest',    # Latest pro model
                'gemini-1.0-pro',           # Stable older model
                'gemini-pro',               # Legacy name
            ]

            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    # Test if model works
                    self.model.generate_content("Test")
                    self.client = self.model
                    self.available = True
                    print(f"   ✨ AI Draft Generator: ✅ Enabled (Gemini - {model_name})")
                    return
                except Exception as inner_e:
                    continue  # Try next model

            # If all models fail
            print(f"   ⚠️  No Gemini models available")
            print("      Check API key validity: https://makersuite.google.com/app/apikey")
            print("      Using template fallback mode")

        except Exception as e:
            print(f"   ⚠️  Gemini initialization failed: {e}")
            print("      Using template fallback mode")

    def _init_openai(self):
        """Initialize OpenAI API."""
        api_key = os.getenv('OPENAI_API_KEY')
        base_url = os.getenv('OPENAI_BASE_URL', None)
        
        if not api_key:
            print("   ⚠️  OPENAI_API_KEY not found in .env")
            return
        
        try:
            if base_url:
                self.client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                self.client = OpenAI(api_key=api_key)
            
            self.model = "gpt-4o-mini"
            self.available = True
            print(f"   ✨ AI Draft Generator: ✅ Enabled (OpenAI - {self.model})")
        except Exception as e:
            print(f"   ⚠️  OpenAI initialization failed: {e}")

    def generate_draft(self, message_text: str, sender_name: str, 
                      chat_name: str, is_group: bool = False) -> str:
        """
        Generate AI-powered draft reply.
        
        Args:
            message_text: Full incoming message text
            sender_name: Name of sender
            chat_name: Chat/group name
            is_group: Whether this is a group chat
            
        Returns:
            Generated draft reply text
        """
        if not self.available:
            return self._template_fallback(message_text, sender_name, is_group)
        
        try:
            # Create prompt
            prompt = self._create_prompt(message_text, sender_name, chat_name, is_group)
            
            if self.provider == 'gemini':
                return self._generate_with_gemini(prompt)
            elif self.provider == 'openai':
                return self._generate_with_openai(prompt)
            else:
                return self._template_fallback(message_text, sender_name, is_group)
            
        except Exception as e:
            print(f"   ⚠️  AI generation failed: {e}")
            return self._template_fallback(message_text, sender_name, is_group)

    def _create_prompt(self, message_text: str, sender_name: str, 
                      chat_name: str, is_group: bool) -> str:
        """Create AI prompt for draft generation."""
        chat_type = "Group" if is_group else "Individual"
        
        prompt = f"""You are a helpful assistant that drafts WhatsApp replies.

Generate a concise, natural reply for this message:

**Sender**: {sender_name}
**Chat Type**: {chat_type}
**Message**:
{message_text}

Guidelines:
- Keep it under 100 words
- Use appropriate tone (casual for personal, professional for business)
- Address the specific points mentioned
- Don't include placeholders like [Your Name]
- Don't repeat the original message
- Just write the reply text ready to send
- Make it sound human and conversational

Reply:"""
        return prompt

    def _generate_with_gemini(self, prompt: str) -> str:
        """Generate draft using Google Gemini."""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            raise Exception(f"Gemini error: {e}")

    def _generate_with_openai(self, prompt: str) -> str:
        """Generate draft using OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that drafts WhatsApp replies. Keep replies concise, natural, and under 100 words. Don't use placeholders."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=150,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI error: {e}")

    def _template_fallback(self, message_text: str, sender_name: str, 
                          is_group: bool) -> str:
        """Fallback to smart templates when AI not available."""
        message_lower = message_text.lower()
        
        # Detect intent
        if any(word in message_lower for word in ['problem', 'issue', 'error', 'not working', 'help']):
            return self._support_template(sender_name, message_text)
        elif any(word in message_lower for word in ['meeting', 'call', 'schedule', 'tomorrow', 'time']):
            return self._business_template(sender_name, message_text)
        elif '?' in message_text:
            return self._question_template(sender_name, message_text)
        else:
            return self._general_template(sender_name, message_text)

    def _support_template(self, sender_name: str, message_text: str) -> str:
        """Support reply template."""
        return f"""Hi {sender_name},

Thanks for reaching out. I understand you're facing an issue.

To help you better:
1. When did this start?
2. What steps have you tried?
3. Any error messages?

I'll help resolve this quickly.

Best regards,
[Your Name]"""

    def _business_template(self, sender_name: str, message_text: str) -> str:
        """Business reply template."""
        return f"""Hi {sender_name},

Thanks for your message. I'd be happy to help with this.

Could you share:
- Your preferred time slots
- Expected duration
- Any specific requirements?

Looking forward to connecting.

Best regards,
[Your Name]"""

    def _question_template(self, sender_name: str, message_text: str) -> str:
        """Question reply template."""
        return f"""Hi {sender_name},

Good question! Let me get back to you on this.

[Add your answer here]

Feel free to ask if you need clarification.

Best,
[Your Name]"""

    def _general_template(self, sender_name: str, message_text: str) -> str:
        """General reply template."""
        return f"""Hi {sender_name},

Thanks for your message! I'll review this and get back to you within 24-48 hours.

If this is urgent, please let me know.

Best regards,
[Your Name]"""


# Test the generator
if __name__ == "__main__":
    print("=" * 60)
    print("AI Draft Reply Generator - Test")
    print("=" * 60)
    
    generator = AIDraftReplyGenerator()
    
    test_message = "Hi! Can we schedule a meeting tomorrow at 3 PM to discuss the project timeline?"
    
    draft = generator.generate_draft(
        message_text=test_message,
        sender_name="Ahmed Khan",
        chat_name="Ahmed Khan",
        is_group=False
    )
    
    print(f"\nOriginal Message: {test_message}")
    print(f"\nGenerated Draft:\n{draft}")
    print("=" * 60)
