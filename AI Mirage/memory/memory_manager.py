from .working_memory import WorkingMemory
from .persistent_memory import PersistentMemory
import os
import logging 
from llm.llm_interface import LLMInterface

class MemoryManager:
    """
    Orchestrates the short-term (WorkingMemory) and long-term (PersistentMemory) modules.
    This class provides a single, clean interface for the main game loop to interact with.
    """

    def __init__(self, llm_client_for_summaries: LLMInterface, persist_directory: str, summary_file_path: str, short_term_window: int = 5, log_file: str = 'logs/memory_manager.log'):
        """
        Initializes all underlying memory modules.

        Args:
            short_term_window (int): The size of the sliding window for recent history.
        """
        base_dir = os.path.dirname(__file__)
        db_path = os.path.join(base_dir, "data", "vector_store")

        self.logger = logging.getLogger(f"{__name__}.MemoryManager")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        self.short_term_window = short_term_window
        # Create the persistent memory object ONCE with the correct path.
        self.turn_count = 1
        self.persistent_memory = PersistentMemory(
            persist_directory=persist_directory,
            summary_file_path=summary_file_path
        )
        
        # Initialize working memory
        self.working_memory = WorkingMemory(
            llm_client=llm_client_for_summaries, 
            window_size=self.short_term_window
        )
        
        self.logger.info("MemoryManager initialized with short-term window of %d turns.", self.short_term_window)

    def add_turn_to_memory(self, player_input: str, dm_output: str, events_list: list, npc_interactions: list):
        """
        Updates all relevant memory modules after a turn is complete.

        Args:
            player_input (str): The player's input for the turn.
            dm_output (str): The DM's generated output for the turn.
            event_data (dict): The structured event data extracted from the turn's output.
        """
        # 1. Add the raw exchange to short-term working memory
        self.logger.info("--- Processing Turn %d ---", self.turn_count)
        self.logger.info("Adding player/DM exchange to short-term memory.")
        self.working_memory.add_exchange(player_input, dm_output)

        # 2. Loop through the list of events and add each one to long-term memory
        self.logger.info("Received %d general events and %d NPC interactions.", len(events_list), len(npc_interactions))
        if not events_list:
            self.logger.info("No significant general events were extracted for this turn.")
        else:
            for event in events_list:
                # Add the turn number to each event before saving
                event['turn'] = self.turn_count 
                self.persistent_memory.add_event(event)

        for interaction in npc_interactions:
            interaction['turn'] = self.turn_count
            self.persistent_memory.add_npc_interaction(interaction)
        previous_turn = self.turn_count
        self.turn_count += 1
        self.logger.info("--- Turn %d complete. Advancing to turn %d. ---", previous_turn, self.turn_count)
        

    def get_context_for_prompt(self, player_input: str) -> dict:
        """
        Gathers all necessary context from memory to build the next prompt.
        
        This now includes a post-retrieval filter to prevent retrieving events
        that are already in the short-term memory window.

        Args:
            player_input (str): The player's latest input.
            current_turn (int): The current turn number of the game.

        Returns:
            dict: A dictionary containing all pieces of context for the Prompt Assembler.
        """
        current_turn = self.turn_count
        self.logger.info("--- Assembling Context for Turn %d ---", current_turn)
        self.logger.info("Player Input: '%s'", player_input)

        self.logger.info("Retrieving recent history from working memory...")
        recent_history = self.working_memory.get_summarized_history()
        augmented_query = recent_history + "\nPlayer: " + player_input

        self.logger.info("Retrieving relevant events from persistent memory...")
        
        # 1. Retrieve MORE documents than needed (e.g., 10) to have a larger pool to filter from.
        initial_retrieval = self.persistent_memory.retrieve_relevant_events(
            query_text=augmented_query, 
            n_results=10
        )

        # 2. Filter out events that are too recent (i.e., within the short-term window).
        # We check if the event's turn is older than the start of our working memory window.
        filtered_events = []
        window_start_boundary = current_turn - self.short_term_window
        for event in initial_retrieval:
            event_turn = event.get('turn')
            if event_turn is not None and event_turn <= window_start_boundary:
                filtered_events.append(event)
        
        # 3. Take the top N (e.g., 3) from the *filtered* list.
        final_relevant_events = filtered_events[:3]
        self.logger.info("Filtered long-term memory to %d relevant events.", len(final_relevant_events))

        self.logger.info("Reading narrative summary...")
        narrative_summary = self.persistent_memory.read_summary()

        context_package = {
            "narrative_summary": narrative_summary,
            "relevant_events": final_relevant_events,
            "recent_history": recent_history
        }
        
        self.logger.info("Context package assembled. Summary Present: %s, History Turns: %d, Relevant Events: %d",
                        bool(narrative_summary), len(self.working_memory.history), len(final_relevant_events))
        
        return context_package

# --- Example Usage ---
# This demonstrates how the main game loop would use the MemoryManager.
if __name__ == '__main__':
    import json
    import shutil

    base_dir = os.path.dirname(__file__)
    db_path = os.path.join(base_dir, "data", "vector_store")

    print("--- Preparing for a clean test run ---")
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    print("Testing MemoryManager module...")
    manager = MemoryManager() # Turn count is now 1

    # --- Simulate Turn 1 ---
    p_input1 = "I enter the ancient library."
    dm_output1 = "The air is thick... On it rests the 'Chronicle of Whispers'."
    event1 = {
        "summary": "The player discovered the 'Chronicle of Whispers' in the ancient library."
    }
    manager.add_turn_to_memory(p_input1, dm_output1, [event1]) # Turn count becomes 2
    
    # --- Simulate a few more turns to populate memory ---
    manager.add_turn_to_memory("I talk to the bartender.", "He has no new quests.", [{"summary": "Player talks to bartender."}]) # Turn count -> 3
    manager.add_turn_to_memory("I go to the market.", "You buy some rations.", [{"summary": "Player buys rations."}]) # Turn count -> 4
    manager.add_turn_to_memory("I travel east.", "You arrive at a dark forest.", [{"summary": "Player travels east."}]) # Turn count -> 5

    # --- Now, simulate the start of Turn 5 ---
    current_player_input = "What was the name of that book I found in the library?"
    print(f"\n--- Getting context for player input at start of Turn {manager.turn_count} ---")
    
    full_context = manager.get_context_for_prompt(current_player_input)

    print("\n--- Context package received from MemoryManager ---")
    print(f"\n[Narrative Summary]: {full_context.get('narrative_summary', '<empty>')}")
    print(f"\n[Recent History (Short-Term)]:\n{full_context.get('recent_history')}")
    print(f"\n[Relevant Events (Long-Term)]:\n{json.dumps(full_context.get('relevant_events'), indent=2)}")
    print("\n-------------------------------------------------")
    
    assert len(full_context['relevant_events']) == 0
    print("\nTest passed: No events were retrieved because the 'book' event is too recent (within the 5-turn short-term memory window).")
    
    # --- Simulate another turn to push the book event out of the window ---
    manager.add_turn_to_memory("I wait for a day.", "A day passes.", []) # Turn count -> 6
    
    print(f"\n--- Getting context for player input at start of Turn {manager.turn_count} ---")
    full_context__after_wait = manager.get_context_for_prompt(current_player_input)
    
    print("\n[Relevant Events (Long-Term) after waiting]:")
    print(json.dumps(full_context__after_wait.get('relevant_events'), indent=2))

    assert len(full_context__after_wait['relevant_events']) > 0
    assert "Chronicle of Whispers" in full_context__after_wait['relevant_events'][0]['summary']
    print("\nMemoryManager test complete. It now correctly filters recent events and retrieves older ones.")