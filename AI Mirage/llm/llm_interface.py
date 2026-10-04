from abc import ABC, abstractmethod

class LLMInterface(ABC):
    """
    An abstract base class that defines the standard interface for LLM clients.
    
    This ensures that any LLM client we create (Groq, Google, etc.) will have a 
    consistent `generate` method, making them interchangeable in the main application.
    """
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "", model: str = None) -> str:
        """
        The core method for generating a text response from a prompt.

        Args:
            prompt (str): The main user prompt.
            system_prompt (str, optional): A system-level instruction for the model's persona.
            model (str, optional): The specific model to use for the generation.

        Returns:
            str: The LLM's generated text response.
        """
        pass