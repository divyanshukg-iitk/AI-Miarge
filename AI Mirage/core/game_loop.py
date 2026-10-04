import json
import re
import logging
from pathlib import Path
import os
from collections import deque
from dotenv import load_dotenv
load_dotenv()

from memory.memory_manager import MemoryManager
from llm.groq_client import GroqClient
from llm.google_client import GoogleClient
from .prompt_manager import assemble_prompt

class GameLoop:
    def __init__(self):
        """Initializes all necessary components for the game."""
        self.logger = logging.getLogger(f"{__name__}.GameLoop")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        handler = logging.FileHandler('logs/game_loop.log', mode='w', encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        
        self.logger.info("Initializing Game Loop...")
        self.groq_llm = GroqClient()
        self.google_llm = GoogleClient(api_key=os.getenv("GOOGLE_API_KEY"))
        #self.google_llm2 = GoogleClient(api_key=os.getenv("GOOGLE_API_KEY2"))
        self.memory = None
        self.story_id = None
        self.turn_count = 1
        self.persona = None 
        self.quest_log = {
            "active": {},
            "completed": []
        }
        self.logger.info("Game Loop initialized successfully.")

    def _save_game_state(self):
        """Gathers critical data and writes it to game_state.json."""
        if not self.story_id:
            return

        state = {
            "turn_count": self.turn_count, #
            "quest_log": self.quest_log, #
            "persona": self.persona, #
            # Convert the deque to a list to save it as JSON
            "working_memory_history": list(self.memory.working_memory.history) #
        }
        save_path = f"saves/{self.story_id}/game_state.json"
        with open(save_path, 'w') as f:
            json.dump(state, f, indent=4) #
        # self.logger.info("Game state for '%s' saved successfully.", self.story_id)
        print(f"[Game Loop] Game state for '{self.story_id}' saved.")

    def _start_new_game(self):
        """Handles the logic for starting a new game."""
        self.story_id = input("Enter a unique ID for your new story (e.g., dragon_quest_123): ") #
        
        # Create folder structure
        save_path = f"saves/{self.story_id}"
        db_path = f"{save_path}/data" #
        Path(db_path).mkdir(parents=True, exist_ok=True)
        summary_path = f"{save_path}/summary.txt" #

        # Initialize MemoryManager with new paths
        self.memory = MemoryManager(
            llm_client_for_summaries=self.groq_llm,
            persist_directory=db_path,
            summary_file_path=summary_path
        )
        self.turn_count = 1 
        self._setup_game_theme() # Proceed with theme selection
        return True

    def _load_existing_game(self):
        """Handles the logic for loading a saved game."""
        saves_dir = "saves"
        if not os.path.exists(saves_dir) or not os.listdir(saves_dir):
            print("No saved games found.")
            return False

        # List all available story_ids
        available_saves = [d for d in os.listdir(saves_dir) if os.path.isdir(os.path.join(saves_dir, d))]
        print("Available saves:")
        for i, story_id in enumerate(available_saves):
            print(f"{i + 1}: {story_id}")

        choice = int(input("Choose a game to load: ")) - 1
        if 0 <= choice < len(available_saves):
            self.story_id = available_saves[choice] #
            
            # Initialize MemoryManager with loaded game paths
            save_path = f"saves/{self.story_id}"
            db_path = f"{save_path}/data"
            summary_path = f"{save_path}/summary.txt"
            self.memory = MemoryManager(
                llm_client_for_summaries=self.groq_llm,
                persist_directory=db_path,
                summary_file_path=summary_path
            )

            # Load game_state.json and restore variables
            state_path = f"{save_path}/game_state.json"
            with open(state_path, 'r') as f:
                state = json.load(f) #
            
            self.turn_count = state['turn_count'] #
            self.quest_log = state['quest_log'] #
            self.persona = state['persona'] #
            self.memory.working_memory.history = deque(state['working_memory_history'], maxlen=self.memory.working_memory.history.maxlen) #

            print(f"Game '{self.story_id}' loaded. Resuming at turn {self.turn_count}.") #
            return True
        else:
            print("Invalid choice.")
            return False
        
    def _setup_game_theme(self):
        """Presents a theme choice to the player and sets the DM persona."""
        themes = {
            "1": {
                "name": "Classic Fantasy",
                "persona": "You are a Dungeon Master for a classic fantasy role-playing game in a world of swords, sorcery, and ancient ruins. Your tone is epic and descriptive, like Tolkien or D&D. Describe vibrant settings, embody mythical creatures, and create heroic quests."
            },
            "2": {
                "name": "Cyberpunk Noir",
                "persona": "You are a Game Master for a cyberpunk noir RPG set in a rain-slicked, neon-drenched metropolis. Your tone is gritty, cynical, and descriptive, like Blade Runner or Neuromancer. Describe high-tech gadgets, shadowy corporations, and morally ambiguous characters."
            },
            "3": {
                "name": "Cosmic Horror",
                "persona": "You are the Keeper of Arcane Lore for a cosmic horror investigation game. Your tone is ominous, unsettling, and focused on psychological dread, like H.P. Lovecraft. Describe sanity-shattering entities, forbidden texts, and the creeping sense that humanity is insignificant."
            }
        }
        
        print("Choose a theme for your adventure:")
        for key, theme in themes.items():
            print(f"{key}: {theme['name']}")
            
        choice = ""
        while choice not in themes:
            choice = input("Enter the number of your choice: ")
        
        self.persona = themes[choice]['persona']
        self.logger.info("Player chose theme: '%s'", themes[choice]['name'])
        print(f"\nStarting a '{themes[choice]['name']}' adventure...\n")
    def setup_new_session(self, story_id: str, theme_choice: str = "1"):
        """Initializes a clean game session for a new game or a test run."""
        self.story_id = story_id
        save_path = f"saves/{self.story_id}"
        db_path = f"{save_path}/data"
        summary_path = f"{save_path}/summary.txt"
        Path(db_path).mkdir(parents=True, exist_ok=True)
        
        self.memory = MemoryManager(
            llm_client_for_summaries=self.groq_llm,
            persist_directory=db_path,
            summary_file_path=summary_path
        )
        self.turn_count = 1
        self.quest_log = {"active": {}, "completed": []}
        self._set_theme(theme_choice)
    def _set_theme(self, choice: str):
        """Presents a theme choice to the player and sets the DM persona."""
        themes = {
            "1": {
                "name": "Classic Fantasy",
                "persona": "You are a Dungeon Master for a classic fantasy role-playing game in a world of swords, sorcery, and ancient ruins. Your tone is epic and descriptive, like Tolkien or D&D. Describe vibrant settings, embody mythical creatures, and create heroic quests."
            },
            "2": {
                "name": "Cyberpunk Noir",
                "persona": "You are a Game Master for a cyberpunk noir RPG set in a rain-slicked, neon-drenched metropolis. Your tone is gritty, cynical, and descriptive, like Blade Runner or Neuromancer. Describe high-tech gadgets, shadowy corporations, and morally ambiguous characters."
            },
            "3": {
                "name": "Cosmic Horror",
                "persona": "You are the Keeper of Arcane Lore for a cosmic horror investigation game. Your tone is ominous, unsettling, and focused on psychological dread, like H.P. Lovecraft. Describe sanity-shattering entities, forbidden texts, and the creeping sense that humanity is insignificant."
            }
        }
        
        print("Choose a theme for your adventure:")
        for key, theme in themes.items():
            print(f"{key}: {theme['name']}")

        self.persona = themes[choice]['persona']
        self.logger.info("Player chose theme: '%s'", themes[choice]['name'])
        print(f"\nStarting a '{themes[choice]['name']}' adventure...\n")
    def process_turn(self, player_input: str) -> str:
        """Processes a single turn of the game and returns the DM's output."""
        if not self._check_safety(player_input):
            return "I cannot respond to that. Please try something else."

        context = self.memory.get_context_for_prompt(player_input)
        
        known_npcs = self.memory.persistent_memory.get_all_known_npcs()
        identified_npc = self._identify_npc_in_context(known_npcs, player_input, context['recent_history'])
        
        npc_memories = []
        if identified_npc:
            npc_memories = self.memory.persistent_memory.retrieve_npc_interactions(
                canonical_name=identified_npc['canonical_name'],
                descriptor=identified_npc['descriptor'],
                query_text=player_input
            )

        game_prompt = assemble_prompt(
            system_persona=self.persona,
            narrative_summary=context['narrative_summary'],
            relevant_events=context['relevant_events'],
            recent_history=context['recent_history'],
            player_input=player_input,
            npc_memories=npc_memories,
            quest_log=self.quest_log
        )

        dm_output = self.groq_llm.generate(prompt=game_prompt, model="llama-3.3-70b-versatile")

        if not self._check_safety(dm_output):
            dm_output = "My apologies, I seem to have lost my train of thought. Could you repeat your action?"
            general_events, npc_interactions = [], []
        else:
            general_events = self._extract_events_from_turn(player_input, dm_output)
            npc_interactions = self._extract_npc_interactions_from_turn(player_input, dm_output)

        self.memory.add_turn_to_memory(player_input, dm_output, general_events, npc_interactions)
        self._analyze_and_update_quests(dm_output)
        self._update_summary_if_needed()
        self.turn_count += 1
        
        return dm_output

    def _check_safety(self, text_to_check: str) -> bool:
        """
        Uses the Llama Guard model to check if a given text is safe.

        Returns:
            bool: True if the text is safe, False otherwise.
        """
        # Llama Guard uses a specific, structured prompt format.
        guard_prompt = f"""
<|begin_of_text|><|start_header_id|>user<|end_header_id|>
Task: Check if there is unsafe content in the text below.

<|begin_of_text|><|start_header_id|>model<|end_header_id|>
{text_to_check}<|eot_id|>
"""
        self.logger.info("Checking text for safety with Llama Guard...")
        response = self.groq_llm.generate(
            prompt=guard_prompt,
            model="meta-llama/Llama-Guard-4-12b"
        )
        
        # The model's output is simple: "safe" or "unsafe".
        if "unsafe" in response.lower():
            self.logger.warning("Llama Guard detected unsafe content. Response: %s", response)
            return False
        self.logger.info("Safety check passed.")
        return True
    
    def _extract_events_from_turn(self, player_input: str, dm_output: str, max_retries: int = 1) -> list:
        """
        Uses an LLM to extract a list of structured events from the turn.
        """
        extraction_prompt = f"""
You are an expert data extraction bot. Your sole purpose is to extract significant game events from text and respond ONLY with a valid JSON list of objects.

RULES:
1.  You MUST respond with ONLY a valid JSON list. Do not include explanations or any text outside of the JSON.
2.  Each object MUST have a 'summary'. Other descriptive keys are optional.
3.  Do NOT include a 'turn' key in the objects.
4.  Use double quotes for all keys and string values.
5.  If no significant events occurred, you MUST return an empty list: [].

---
EXAMPLE 1
CONVERSATION:
Player: I approach the bartender and ask if he's heard any interesting rumors lately.
DM: The tavernkeeper, Balen, leans in. "Aye," he whispers, "A hooded figure was just in here, asking about the old ruins near the Whispering Woods. Said something about disappearances."
Your Response:
[
  {{
    "type": "information",
    "summary": "The tavernkeeper Balen revealed that a hooded figure is investigating old ruins and local disappearances.",
    "details": {{
      "npc_name": "Balen",
      "subject": "hooded figure",
      "plot_hooks": ["old ruins", "disappearances"]
    }}
  }}
]
---
EXAMPLE 2
CONVERSATION:
Player: I wait by the fire.
DM: You warm your hands by the fire. An hour passes uneventfully.
Your Response:
[]
---

Now, perform this task on the following conversation.

CONVERSATION:
Player: {player_input}
DM: {dm_output}

Your Response:
"""
        self.logger.info("Starting event extraction...")
        for attempt in range(max_retries + 1):
            response_str = self.groq_llm.generate(
                prompt=extraction_prompt, 
                model="llama-3.1-8b-instant"
            )
            
            try:
                match = re.search(r'\[.*\]', response_str, re.DOTALL)
                if match:
                    clean_json_str = match.group(0)
                else:
                    clean_json_str = response_str 

                events_list = json.loads(clean_json_str)
                
                if isinstance(events_list, list):
                    # SUCCESS!
                    if attempt > 0:
                        self.logger.info("Successfully extracted %d events.", len(events_list))
                    return events_list
                else:
                    # The JSON is valid but not a list, which is an error
                    self.logger.warning("Failed to decode JSON for event list on attempt %d. Error: %s", attempt + 1, e)
                    # We can add the error to the prompt for the next attempt
                    extraction_prompt += f"\n\nPREVIOUS FAILED RESPONSE:\n{response_str}\n\nERROR: The response was valid JSON but not a list. Please correct the output and provide ONLY a valid JSON list."


            except json.JSONDecodeError as e:
                self.logger.warning("Failed to decode JSON for event list on attempt %d. Error: %s", attempt + 1, e)
                if attempt < max_retries:
                    # If we have retries left, build the self-correction prompt
                    self.logger.info("Attempting self-correction for event extraction...")
                    correction_instruction = f"""
                    PREVIOUS FAILED RESPONSE:
                    {response_str}

                    ERROR: The previous response was not valid JSON. Please fix the syntax and provide ONLY the corrected, raw JSON list of objects. Do not add any conversational text.
                    """
                    extraction_prompt += correction_instruction
                else:
                    self.logger.error("Max retries reached. Failed to extract events.")
                    return [] # Failed after all retries

        return []

    def _update_summary_if_needed(self):
        """Triggers the recursive summarization process every 5 turns."""
        # The trigger condition remains the same
        if self.turn_count > 1 and self.turn_count % 5 == 0:
            self.logger.info("Turn %d reached. Triggering recursive narrative summary update.", self.turn_count)
            
            previous_summary = self.memory.persistent_memory.read_summary()
            recent_history = self.memory.working_memory.get_history_as_string()
            
            # 1. The System Prompt: The instructions for the AI's persona and task.
            system_prompt = """You are a master storyteller and historian for a role-playing game. 
Your task is to integrate the 'Most Recent Events' into the 'Previous Summary' to create a new, cohesive, and updated summary of the entire story so far.
The new summary should be written in a narrative, past-tense style.
Capture all major plot developments, character introductions, and key discoveries.
Respond ONLY with the new, updated summary text. Do not add any conversational filler."""

            # 2. The User Prompt: The actual data for the AI to work on.
            user_prompt = f"""
            Previous Summary:
            {previous_summary if previous_summary else "The story has just begun."}
            
            Most Recent Events:
            {recent_history}

            ---
            New, Updated Summary:
            """
            
            # 3. Call the generate method using both arguments
            self.logger.info("Calling Google LLM to generate new summary...")
            new_summary = self.google_llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                model="gemini-2.5-pro"
            )
            
            self.memory.persistent_memory.write_summary(new_summary.strip())
            self.logger.info("Narrative summary updated successfully.")


    def _extract_npc_interactions_from_turn(self, player_input: str, dm_output: str, max_retries: int = 1) -> list:
        """
        Uses an LLM to extract structured NPC interactions from the turn.
        """
        self.logger.info("Starting NPC interaction extraction...")
        
        extraction_prompt = f"""
    You are an expert data extraction bot. Your ONLY job is to extract significant NPC interactions from text and respond with a valid JSON list of objects.

    RULES:
    1.  You MUST respond with ONLY a valid JSON list. Do not include explanations or any text outside of the JSON.
    2.  Each object MUST have the keys 'canonical_name', 'descriptor', and 'summary'.
    3.  Use double quotes for all keys and string values.
    4.  If no NPCs were involved, or the interaction was trivial (e.g., just buying a generic item), you MUST return an empty list: [].

    ---
    EXAMPLE 1
    CONVERSATION:
    Player: I approach the bartender and ask about the disappearances.
    DM: The tavernkeeper, a stout man with a bushy beard named Balen, leans in. "Aye," he whispers, "Things haven't been right since the moon turned red. A cloaked figure was asking about the old ruins, too."
    Your Response:
    [
    {{
        "canonical_name": "Balen",
        "descriptor": "the stout tavernkeeper with a bushy beard",
        "summary": "Balen mentioned that things have been strange since the red moon and that a cloaked figure was asking about the old ruins."
    }}
    ]
    ---
    EXAMPLE 2
    CONVERSATION:
    Player: I walk through the forest.
    DM: The path is quiet. The only sound is the wind in the trees.
    Your Response:
    []
    ---

    Now, perform this task on the following conversation.

    CONVERSATION:
    Player: {player_input}
    DM: {dm_output}

    Your Response:
    """
        
        for attempt in range(max_retries + 1):
            response_str = self.groq_llm.generate(
            prompt=extraction_prompt,
            model="openai/gpt-oss-20b"
        )
            
            try:
                match = re.search(r'\[.*\]', response_str, re.DOTALL)
                if match:
                    clean_json_str = match.group(0)
                else:
                    clean_json_str = response_str 

                interactions_list = json.loads(clean_json_str)
                
                if isinstance(interactions_list, list):
                    # SUCCESS!
                    if attempt > 0:
                        self.logger.info("Self-correction for NPC extraction succeeded on attempt %d.", attempt + 1)
                    self.logger.info("Successfully extracted %d NPC interactions.", len(interactions_list))
                    return interactions_list
                else:
                    self.logger.warning("LLM returned valid JSON for NPC extraction, but it was not a list on attempt %d.", attempt + 1)
                    extraction_prompt += f"\n\nPREVIOUS FAILED RESPONSE:\n{response_str}\n\nERROR: The response was valid JSON but not a list. Please correct it."

            except json.JSONDecodeError as e:
                self.logger.warning("Failed to decode JSON for NPC interactions on attempt %d. Error: %s", attempt + 1, e)
                if attempt < max_retries:
                    self.logger.info("Attempting self-correction for NPC extraction...")
                    correction_instruction = f"""
                    PREVIOUS FAILED RESPONSE:
                    {response_str}

                    ERROR: The previous response was not valid JSON. Please fix the syntax and provide ONLY the corrected, raw JSON list of objects.
                    """
                    extraction_prompt += correction_instruction
                else:
                    self.logger.error("Max retries reached. Failed to extract NPC interactions.")
                    return [] # Failed after all retries

        return []

    def _identify_npc_in_context(self, known_npcs: list, player_input: str, recent_history: str, max_retries: int = 1) -> dict | None:
        """
        Uses an LLM to identify the primary NPC from a known list within the current context.
        Includes a self-correction loop to retry on JSON parsing failure.
        """
        if not known_npcs:
            return None 
        self.logger.info("Attempting to identify a known NPC in the current context...")

        npc_list_str = "\n".join([f"- Name: {npc['canonical_name']}, Description: {npc['descriptor']}" for npc in known_npcs])

        identification_prompt = f"""
    You are an expert entity linking system. Your task is to identify which NPC from a known list is the primary focus of the current interaction and respond ONLY with a valid JSON object.

    RULES:
    1.  You MUST respond with ONLY a single valid JSON object. Do not include explanations or any text outside of the JSON.
    2.  If a clear match is found, the JSON object must contain the 'canonical_name' and 'descriptor' of that NPC from the known list.
    3.  If no specific NPC from the list is the focus, or if it's ambiguous, you MUST respond with an empty JSON object: {{}}.
    4.  Use double quotes for all keys and string values.

    ---
    EXAMPLE 1 (Match Found)
    KNOWN NPC LIST:
    - Name: Balen, Description: the stout tavernkeeper with a bushy beard
    - Name: Elara, Description: the enigmatic sorceress
    CURRENT INTERACTION:
    Player: I ask the blacksmith about the disappearances.
    Your Response:
    {{
    "canonical_name": "Balen",
    "descriptor": "the stout tavernkeeper with a bushy beard"
    }}
    ---
    EXAMPLE 2 (No Match Found)
    KNOWN NPC LIST:
    - Name: Balen, Description: the stout tavernkeeper with a bushy beard
    - Name: Elara, Description: the enigmatic sorceress
    CURRENT INTERACTION:
    Player: I think I'll head east towards the mountains.
    Your Response:
    {{}}
    ---

    Now, perform this task.

    KNOWN NPC LIST:
    {npc_list_str}

    CURRENT INTERACTION:
    {recent_history}
    Player: {player_input}

    Your Response:
    """
        
        for attempt in range(max_retries + 1):
            response_str = self.groq_llm.generate(
            prompt=identification_prompt,
            model="openai/gpt-oss-20b"
        )
            try:
                match = re.search(r'\{.*\}', response_str, re.DOTALL)
                if match:
                    clean_json_str = match.group(0)
                else:
                    clean_json_str = response_str

                npc_data = json.loads(clean_json_str)
                
                if isinstance(npc_data, dict):
                    # SUCCESS! Check if it's a valid NPC or an empty object.
                    if 'canonical_name' in npc_data and 'descriptor' in npc_data:
                        self.logger.info("Identified NPC in context: %s", npc_data['canonical_name'])
                    else:
                        self.logger.info("No specific known NPC identified in the context.")
                    
                    if attempt > 0:
                        self.logger.info("Self-correction for NPC identification succeeded on attempt %d.", attempt + 1)
                    
                    # Return the dict if it has keys, otherwise return None
                    return npc_data if npc_data else None
                else:
                    self.logger.warning("LLM returned valid JSON for NPC ID, but it was not a dictionary on attempt %d.", attempt + 1)
                    identification_prompt += f"\n\nPREVIOUS FAILED RESPONSE:\n{response_str}\n\nERROR: The response was not a JSON object. Please correct it."

            except (json.JSONDecodeError, TypeError) as e:
                self.logger.warning("Failed to decode JSON for NPC identification on attempt %d. Error: %s", attempt + 1, e)
                if attempt < max_retries:
                    self.logger.info("Attempting self-correction for NPC identification...")
                    correction_instruction = f"""
                    PREVIOUS FAILED RESPONSE:
                    {response_str}

                    ERROR: The previous response was not valid JSON. Please fix the syntax and provide ONLY the corrected, raw JSON object.
                    """
                    identification_prompt += correction_instruction
                else:
                    self.logger.error("Max retries reached. Failed to identify NPC.")
                    return None # Failed after all retries

        return None # Fallback
        
    def _analyze_and_update_quests(self, dm_output: str, max_retries: int = 1):
        """
        Analyzes the DM's output for quest updates and modifies the quest log.
        Includes a self-correction loop to retry on JSON parsing failure.
        """
        self.logger.info("Analyzing DM output for quest updates...")
        analysis_prompt = f"""
    You are a Quest Log Manager. Your sole purpose is to analyze game text and respond with a single JSON object indicating a quest status change.

    RULES:
    1.  You MUST respond with ONLY a single valid JSON object. Do not include explanations or any text outside of the JSON.
    2.  Use double quotes for all keys and string values.
    3.  If a new quest is given, use: {{"status": "new", "name": "Quest Name", "objective": "Quest Objective"}}
    4.  If a quest is completed, use: {{"status": "completed", "name": "Quest Name"}}
    5.  If NO quest was given, updated, or completed, you MUST return an empty JSON object: {{}}

    ---
    EXAMPLE 1 (New Quest)
    GAME TEXT: The old man nods. "Thank you, traveler. Please, retrieve the Sunstone from the goblin chieftain. I will reward you handsomely."
    Your Response:
    {{"status": "new", "name": "Retrieve the Sunstone", "objective": "Retrieve the Sunstone from the goblin chieftain for the old man."}}
    ---
    EXAMPLE 2 (Completed Quest)
    GAME TEXT: You hand the Sunstone to the old man. He gasps with joy. "You've done it! The village is safe. Your quest, 'Retrieve the Sunstone', is complete."
    Your Response:
    {{"status": "completed", "name": "Retrieve the Sunstone"}}
    ---
    EXAMPLE 3 (No Update)
    GAME TEXT: You enter the tavern and order an ale. The room is bustling with chatter.
    Your Response:
    {{}}
    ---

    Now, perform this task on the following game text.

    GAME TEXT:
    {dm_output}

    Your Response:
    """
        
        for attempt in range(max_retries + 1):
            response_str = self.groq_llm.generate(
                prompt=analysis_prompt, 
                model="llama-3.1-8b-instant"
            )
            
            try:
                self.logger.info("LLM response for quest analysis: %s", response_str)
                match = re.search(r'\{.*\}', response_str, re.DOTALL)
                if match:
                    clean_json_str = match.group(0)
                else:
                    clean_json_str = response_str

                update_data = json.loads(clean_json_str)
                
                if isinstance(update_data, dict):
                    # SUCCESS!
                    if attempt > 0:
                        self.logger.info("Self-correction for quest analysis succeeded on attempt %d.", attempt + 1)
                    
                    if not update_data:
                        self.logger.info("No quest updates found.")
                        return # No quest update

                    status = update_data.get("status")
                    name = update_data.get("name")

                    if status == "new" or status == "updated":
                        objective = update_data.get("objective")
                        if name and objective:
                            self.logger.info("New/Updated Quest: '%s' -> '%s'", name, objective)
                            self.quest_log["active"][name] = objective
                    
                    elif status == "completed":
                        if name and name in self.quest_log["active"]:
                            self.logger.info("Completed Quest: '%s'", name)
                            del self.quest_log["active"][name]
                            self.quest_log["completed"].append(name)
                    
                    return 

                else:
                    self.logger.warning("LLM returned valid JSON for quest analysis, but it was not a dictionary on attempt %d.", attempt + 1)
                    analysis_prompt += f"\n\nPREVIOUS FAILED RESPONSE:\n{response_str}\n\nERROR: The response was not a JSON object. Please correct it."

            except (json.JSONDecodeError, TypeError) as e:
                self.logger.warning("Failed to decode JSON for quest update on attempt %d. Error: %s", attempt + 1, e)
                if attempt < max_retries:
                    self.logger.info("Attempting self-correction for quest update...")
                    correction_instruction = f"""
                    PREVIOUS FAILED RESPONSE:
                    {response_str}

                    ERROR: The previous response was not valid JSON. Please fix the syntax and provide ONLY the corrected, raw JSON object.
                    """
                    analysis_prompt += correction_instruction
                else:
                    self.logger.error("Max retries reached. Failed to analyze quest updates.")
                    return # Failed after all retries

    def run(self):
        """Starts and runs the main game loop."""
        while True:
            # Create a "Main Menu"
            print("\n--- AI Dungeon Master ---")
            print("1: Start a New Game")
            print("2: Load an Existing Game")
            print("3: Exit")
            choice = input("Choose an option: ")

            game_started = False
            if choice == "1":
                game_started = self._start_new_game()
            elif choice == "2":
                game_started = self._load_existing_game()
            elif choice == "3":
                break
            else:
                print("Invalid option, please try again.")

            if not game_started:
                continue

            while True:
                self.logger.info("--- Starting Turn %d ---", self.turn_count)
                player_input = input("Player: ")
                if player_input.lower() == 'quit':
                    print("Quitting to main menu...")
                    self._save_game_state()
                    self.logger.info("Player quit the game. Exiting loop.")
                    break
                self.logger.info("Player Input: '%s'", player_input)
                if not self._check_safety(player_input):
                    print("DM: I cannot respond to that. Please try something else.")
                    continue
                self.logger.info("Getting context from memory...")
                context = self.memory.get_context_for_prompt(player_input)
                self.logger.info("Getting all known NPCs from persistent memory...")
                known_npcs = self.memory.persistent_memory.get_all_known_npcs()
                identified_npc = self._identify_npc_in_context(known_npcs, player_input, context['recent_history'])
                
                npc_memories = []
                if identified_npc:
                    self.logger.info("Retrieving specific memories for NPC: %s", identified_npc['canonical_name'])
                    npc_memories = self.memory.persistent_memory.retrieve_npc_interactions(
                        canonical_name=identified_npc['canonical_name'],
                        descriptor=identified_npc['descriptor'],
                        query_text=player_input
                    )
                self.logger.info("Assembling final prompt for main generation...")
                game_prompt = assemble_prompt(
                    system_persona=self.persona,
                    narrative_summary=context['narrative_summary'],
                    relevant_events=context['relevant_events'],
                    recent_history=context['recent_history'],
                    player_input=player_input,
                    npc_memories=npc_memories,
                    quest_log=self.quest_log
                )
                self.logger.info("Calling main generation LLM (llama-3.3-70b-versatile)...")
                dm_output = self.groq_llm.generate(prompt=game_prompt, model="llama-3.3-70b-versatile")
                if not self._check_safety(dm_output):
                    # If the AI's output is unsafe, provide a generic, safe response instead.
                    dm_output = "My apologies, I seem to have lost my train of thought. Could you repeat your action?"
                    print(f"\nDM: {dm_output}\n")
                    # We still save a basic turn to memory to avoid breaking continuity
                    events_list = [], npc_interactions = []
                else:
                    # If the output is safe, print it and extract events normally.
                    print(f"\nDM: {dm_output}\n")
                    events_list = self._extract_events_from_turn(player_input, dm_output)
                    npc_interactions = self._extract_npc_interactions_from_turn(player_input, dm_output)

                self.logger.info("Updating memory with turn data...")
                self.memory.add_turn_to_memory(player_input, dm_output, events_list, npc_interactions)
                
                self._analyze_and_update_quests(dm_output)
                
                self._update_summary_if_needed()
                self.turn_count += 1
                self._save_game_state()
                
        self.logger.info("Game loop finished.")
        print("Ending game. Goodbye!")
