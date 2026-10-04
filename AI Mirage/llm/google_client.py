# In llm/google_client.py
import os
import google.generativeai as genai
from .llm_interface import LLMInterface

class GoogleClient(LLMInterface):
    """
    LLM client for the Google Gemini API.
    """
    def __init__(self, api_key: str = None):
        """Initializes the GoogleClient and configures the API key."""
        # FIX: Add an instance variable to track initialization status
        self.initialized = False
        try:
            if not api_key:
                # Raise an error if the key is missing entirely
                raise ValueError("GOOGLE_API_KEY environment variable not found.")
            
            genai.configure(api_key=api_key)
            self.initialized = True
            print("[Google Client] Initialized successfully.")
        except Exception as e:
            print(f"[Google Client] Error during initialization: {e}")

    def generate(self, prompt: str, system_prompt: str = "", model: str = "gemini-1.5-pro-latest") -> str:
        """Generates content using the specified Gemini model."""
        # FIX: Check the instance's 'initialized' status instead of the incorrect 'genai.conf'
        if not self.initialized:
            return "Error: Google client was not initialized. Check API key."

        try:
            # FIX: Initialize the model on each call to ensure the correct system_prompt is always used.
            # This is safer and avoids bugs related to caching.
            llm_model = genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt
            )
            
            response = llm_model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error during Google API call: {e}"