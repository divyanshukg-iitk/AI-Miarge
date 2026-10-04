# The working memory logic will be written here
# This will be used to store the recent interactions with the user
# and will be used to provide context to the LLM for generating responses

# Currently we will be using Sliding Window Buffer strategy
# later we can implement other strategy - Summarised window buffer

# We would like to store about last 7 interactions with the user
# Each interaction is an output from the LLM along with the user input
# We will store these interactions in a queue, easier to implement sliding window buffer

from collections import deque
import logging 
import json 

class WorkingMemory:
    """
    Manages the short-term memory of the conversation using a sliding window buffer.
    """
    def __init__(self, window_size: int = 7, log_file: str = 'logs/working_memory.log'):
        """
        Initializes the working memory and sets up logging.
        
        Args:
            window_size (int): The number of recent turns to keep in memory.
            log_file (str): The file path for the log.
        """
        self.history = deque(maxlen=window_size)
        
        # --- A dedicated logger for this class ---
        # This ensures logs from this module are clearly identified.
        self.logger = logging.getLogger(f"{__name__}.WorkingMemory")
        self.logger.setLevel(logging.INFO)
        
        # Prevent logs from propagating to the root logger if you have a global setup
        self.logger.propagate = False
        
        # Create a file handler to write logs to a file.
        # mode='w' will clear the log file each time the script starts, which is good for testing.
        # For a persistent log across game sessions, you would use mode='a' (append).
        handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        
        # Define the format for the log messages.
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Add the handler to the logger, but only if it doesn't have one already
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        
        self.logger.info("WorkingMemory initialized with window size %s. Logging to %s", self.history.maxlen, log_file)
        # --- End of logging setup ---

    def add_exchange(self, player_input: str, dm_output: str):
        """
        Adds a new player-DM exchange to the conversational history and logs the change.
        """
        exchange_data = {"player": player_input, "dm": dm_output}
        self.history.append(exchange_data)
        
        self.logger.info("Added new exchange to memory: %s", json.dumps(exchange_data))
        self.log_current_state()

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

    def log_current_state(self):
        """
        Writes the entire current state of the memory buffer to the log.
        """
        self.logger.info("--- Current Working Memory State (Size: %d/%d) ---", len(self.history), self.history.maxlen)
        # We convert the deque to a list for safe iteration and numbering
        history_list = list(self.history)
        for i, exchange in enumerate(history_list):
            self.logger.info("  [Turn %d]: Player: %s", i + 1, exchange['player'])
            self.logger.info("  [Turn %d]: DM: %s", i + 1, exchange['dm'])
        self.logger.info("-------------------------------------------------")


### DUMMY TESTING CODE BELOW ###
if __name__ == '__main__':
    import os
    if not os.path.exists('logs'):
        os.makedirs('logs')

    print("Testing WorkingMemory module...")
    memory = WorkingMemory(window_size=3) # Using a smaller size for a quick test

    memory.add_exchange("I enter the tavern.", "You see a dark, smoke-filled room. A mysterious figure sits in the corner.")
    memory.add_exchange("I approach the figure.", "The figure looks up. It's an old man with a long grey beard. 'What do you want?' he rasps.")
    memory.add_exchange("I ask him for a quest.", "He sighs, 'Very well. I need you to retrieve the Amulet of Yendor from the goblin caves.'")

    # This next turn will push the first turn out of the memory
    memory.add_exchange("Where are these caves?", "They are to the east, a day's journey from here. Be careful.")

    print("\nTest complete. Check the 'logs/working_memory.log' file for the detailed output.")