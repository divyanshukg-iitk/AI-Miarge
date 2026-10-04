from collections import deque
import logging
import json
from llm.llm_interface import LLMInterface

class WorkingMemory:
    """
    Manages the short-term memory of the conversation using a rolling,
    just-in-time LLM-powered summary.
    """
    def __init__(self, llm_client: LLMInterface, window_size: int = 5, log_file: str = 'logs/working_memory.log'):
        """
        Initializes the working memory and its logger.
        """
        self.llm_client = llm_client
        self.history = deque(maxlen=window_size)
        
        # --- A dedicated logger for this class ---
        self.logger = logging.getLogger(f"{__name__}.WorkingMemory")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            self.logger.propagate = False
            handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.logger.info("Summarized WorkingMemory initialized with window size %s.", self.history.maxlen)
        self.logger.info("Using LLM client: %s", self.llm_client.__class__.__name__)
        # --- End of logging setup ---

    def add_exchange(self, player_input: str, dm_output: str):
        """
        Adds a new raw player-DM exchange to the history buffer and logs the action.
        """
        self.history.append({"player": player_input, "dm": dm_output})
        self.logger.info("Added raw exchange to buffer. History size is now %d/%d.", len(self.history), self.history.maxlen)

    def get_summarized_history(self) -> str:
        """
        Generates a condensed summary of the recent conversational history and logs the process.
        """
        if not self.history:
            return "The adventure has just begun."
        
        self.logger.info("Generating summarized history for the last %d turns...", len(self.history))
        
        raw_text_history = "\n\n".join([f"Player: {ex['player']}\nDM: {ex['dm']}" for ex in self.history])
        self.logger.info("--- Raw text for summarization ---\n%s\n---------------------------------", raw_text_history)
        
        summarization_prompt = f"""
        You are a memory assistant. Your task is to create a concise, present-tense summary of the following recent conversation from a role-playing game.
        Capture all important actions, discoveries, character mentions, and key dialogue. The summary should be 2-3 cohesive paragraphs.

        CONVERSATION TO SUMMARIZE:
        {raw_text_history}

        CONCISE SUMMARY:
        """

        model_to_use = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.logger.info("Calling LLM for summarization using model '%s'...", model_to_use)
        
        summary = self.llm_client.generate(
            prompt=summarization_prompt,
            model=model_to_use
        )
        
        self.logger.info("Received summary from LLM: \"%s\"", summary.strip())
        
        return summary.strip()
    
    def get_history_as_string(self) -> str:
        """
        Retrieves the entire conversational history as a single, formatted string.
        """
        if not self.history:
            return "The adventure has just begun."
        
        formatted_history = []
        for exchange in self.history:
            formatted_history.append(f"Player: {exchange['player']}\nDM: {exchange['dm']}")
        
        return "\n\n".join(formatted_history)

### DUMMY TESTING CODE BELOW ###
if __name__ == '__main__':
    import os
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Create a dummy LLM client for testing purposes, since the class now requires one.
    class DummyLLMClient(LLMInterface):
        def generate(self, prompt: str, system_prompt: str = "", model: str = None) -> str:
            # Simulate a summary generation
            return "The player entered a tavern, approached a mysterious old man, and accepted a quest to find the Amulet of Yendor in the goblin caves."

    print("Testing Summarized WorkingMemory module...")
    
    # Instantiate the dummy client and the memory
    dummy_client = DummyLLMClient()
    memory = WorkingMemory(llm_client=dummy_client, window_size=3)

    memory.add_exchange("I enter the tavern.", "You see a dark, smoke-filled room. A mysterious figure sits in the corner.")
    memory.add_exchange("I approach the figure.", "The figure looks up. It's an old man with a long grey beard. 'What do you want?' he rasps.")
    memory.add_exchange("I ask him for a quest.", "He sighs, 'Very well. I need you to retrieve the Amulet of Yendor from the goblin caves.'")

    print("\n--- Generating Summary ---")
    final_summary = memory.get_summarized_history()
    print("Final Summary returned by the method:")
    print(final_summary)
    print("--------------------------\n")
    
    print("Test complete. Check 'logs/working_memory.log' for detailed output of the summarization process.")