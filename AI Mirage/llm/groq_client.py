import os
from groq import Groq
from .llm_interface import LLMInterface


class GroqClient(LLMInterface):
    """
    LLM client for the Groq API.
    """
    def __init__(self):
        try:
            self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            print("[Groq Client] Initialized successfully.")
        except Exception as e:
            print(f"[Groq Client] Error during initialization: {e}")
            self.client = None

    def generate(self, prompt: str, system_prompt: str = "", model: str = "llama3-8b-8192") -> str:
        if not self.client:
            return "Error: Groq client not initialized."
            
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model=model,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error during Groq API call: {e}"