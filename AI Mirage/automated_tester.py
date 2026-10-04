import json
import time
import uuid
import os
from core.game_loop import GameLoop
from llm.google_client import GoogleClient

class TestConductor:
    """
    An automated QA agent that runs a suite of tests against the AI Dungeon Master
    to validate its functionality against the project's requirements.
    """
    def __init__(self, log_file="test_results.log"):
        """Initializes the tester with a fresh game instance and LLM client."""
        self.game = GameLoop()
        self.tester_llm = GoogleClient(api_key=os.getenv("GOOGLE_API_KEY2"))
        self.log_file = log_file

        self.delay_between_actions = 20
        self.delay_between_tests = 10

        with open(self.log_file, 'w') as f:
            f.write(f"--- Automated Test Run @ {time.ctime()} ---\n\n")
        print("Test Conductor Initialized .")

    def log_result(self, result_data):
        """Logs a test result to the file and prints the status."""
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(result_data, indent=4) + "\n" + "-"*40 + "\n")
        status = "PASSED" if result_data.get('passed') else "FAILED"
        test_name = result_data.get('test_name', 'Unknown Test')
        print(f"  [Result] Test '{test_name}': {status}")

    def _extract_fact(self, context: str, dm_response: str) -> str:
        """Uses an LLM to extract a key fact from a DM's response, with a robust prompt structure for Gemini."""

        # Split the prompt into instructions (system_prompt) and data (prompt).
        
        # 1. The System Prompt: The instructions for the AI's persona and task.
        system_prompt = """You are a data extraction bot. Your task is to review a dialogue and extract the single, most important, and unique fact established by the DM.
Phrase this fact as a simple, declarative statement.
Respond ONLY with the single sentence representing the fact. Do not add any conversational filler or extra text."""

        # 2. The User Prompt: The actual data for the AI to work on.
        user_prompt = f"""
        Context: {context}
        DM Response: "{dm_response}"
        """
        
        # 3. Call the generate method using both arguments
        key_fact = self.tester_llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model="gemini-2.0-flash-lite"
        ).strip()
        
        return key_fact
        
    def _get_evaluation(self, test_name: str, fact: str, action: str, dm_response: str) -> dict:
        """Uses an LLM to evaluate if a test passed or failed."""
        evaluation_prompt = f"""
You are a meticulous QA Test Evaluator. Your sole purpose is to analyze an AI's response in a game test and determine if it correctly reflects a given fact. You MUST respond with ONLY a valid JSON object.

RULES:
1.  Your entire response MUST be a single, raw JSON object. Do not include explanations, conversational text, or markdown fences like ```json.
2.  The JSON object must have exactly two keys: "passed" (a boolean: true or false) and "reasoning" (a string).
3.  Use double quotes for all keys and string values.
4.  Your evaluation must be strict. If the AI's response fails to mention the key fact, it is a failure (fail by omission).

---
EXAMPLE 1 (Clear Pass)
- Fact to Verify: "The bartender's name is Balen."
- Player's Test Action: "I ask the bartender for his name."
- AI DM's Response: "The man behind the counter smiles. 'The name's Balen,' he says, wiping down a mug."
Your Response:
{{
  "passed": true,
  "reasoning": "The AI's response explicitly stated the bartender's name was 'Balen', which correctly matches the fact."
}}
---
EXAMPLE 2 (Clear Fail - Contradiction)
- Fact to Verify: "The sword is hidden in the stone chest."
- Player's Test Action: "I open the stone chest."
- AI DM's Response: "You lift the heavy lid of the stone chest. Inside, you find a pile of old coins and a dusty leather-bound book."
Your Response:
{{
  "passed": false,
  "reasoning": "The AI's response failed to mention the sword in the chest, contradicting the fact that it should be there."
}}
---
EXAMPLE 3 (Clear Fail - Omission)
- Fact to Verify: "The key is made of solid silver."
- Player's Test Action: "I pick up the key."
- AI DM's Response: "You pick up the small, ornate key. It feels cool to the touch."
Your Response:
{{
  "passed": false,
  "reasoning": "The AI's response described the key but failed to mention that it was made of silver, which was the specific fact being tested."
}}
---

Now, perform this evaluation on the following test case.

- Test Name: {test_name}
- Fact to Verify: "{fact}"
- Player's Test Action: "{action}"
- AI DM's Response: "{dm_response}"

Your Response:
"""
        
        eval_result_str = self.tester_llm.generate(prompt=evaluation_prompt, model="gemini-2.5-pro")
        try:
            result = json.loads(eval_result_str.strip())
            result['test_name'] = test_name
            result['fact_verified'] = fact
            return result
        except json.JSONDecodeError:
            return {"test_name": test_name, "passed": False, "reasoning": "Failed to parse evaluation LLM's JSON response."}

    def run_short_term_test(self):
        """Tests short-term recall over ~5 turns."""
        print("\n--- RUNNING: Short-Term Memory Test ---")
        self.game.setup_new_session(story_id=f"short_term_test_{uuid.uuid4()}")

        # 1. Setup Phase: Establish a fact
        setup_prompt = "You are a player testing an AI DM. Generate an action to establish a unique, non-obvious visual detail (e.g., an object's color, a specific number)."
        player_action = self.tester_llm.generate(prompt=setup_prompt, model="gemini-2.0-flash-lite")
        dm_response = self.game.process_turn(player_action)
        key_fact = self._extract_fact(player_action, dm_response)
        print(f"  [Setup] Key fact established: {key_fact}")
        time.sleep(self.delay_between_actions)

        # 2. Distraction Phase: 3 turns of unrelated actions
        distraction_prompt = "You are a player in a fantasy game. Generate a simple, unrelated action to distract the DM."
        for i in range(3):
            action = self.tester_llm.generate(prompt=distraction_prompt, model="gemini-2.0-flash-lite")
            self.game.process_turn(action)
            time.sleep(self.delay_between_actions)
        print("  [Distraction] 3 turns of unrelated actions completed.")

        # 3. Recall Phase
        recall_action_prompt = f"The fact to verify is: '{key_fact}'. Generate a player action that tests the DM's memory of this fact without stating it directly."
        recall_action = self.tester_llm.generate(prompt=recall_action_prompt, model="gemini-2.5-pro")
        final_dm_response = self.game.process_turn(recall_action)
        
        # 4. Evaluation
        result = self._get_evaluation("short_term_recall", key_fact, recall_action, final_dm_response)
        self.log_result(result)

    def run_long_term_and_npc_test(self):
        """Tests long-term and NPC recall over ~30 turns."""
        print("\n--- RUNNING: Long-Term & NPC Memory Test ---")
        self.game.setup_new_session(story_id=f"long_term_test_{uuid.uuid4()}")
        
        # 1. Setup Phase
        item_action = "As a player, generate an action to inspect a newly found, unique item, giving it a memorable name."
        item_player_action = self.tester_llm.generate(prompt=item_action, model="gemini-2.0-flash-lite")
        item_dm_response = self.game.process_turn(item_player_action)
        item_key_fact = self._extract_fact(item_player_action, item_dm_response)
        print(f"  [Setup] Long-term fact established: {item_key_fact}")
        time.sleep(self.delay_between_actions)
        
        npc_action = "As a player, generate an action to ask a new NPC a personal question to establish a memorable fact about them (a fear, a secret, a desire)."
        npc_player_action = self.tester_llm.generate(prompt=npc_action, model="gemini-2.0-flash-lite")
        npc_dm_response = self.game.process_turn(npc_player_action)
        npc_key_fact = self._extract_fact(npc_player_action, npc_dm_response)
        print(f"  [Setup] NPC fact established: {npc_key_fact}")
        time.sleep(self.delay_between_actions)
        
        # 2. Gameplay Phase (20+ turns)
        gameplay_prompt = "You are a player in a fantasy adventure. Generate your next logical action to explore the world or advance the story."
        for i in range(30):
            print(f"      (Running gameplay turn {i+3}/34...)")
            action = self.tester_llm.generate(prompt=gameplay_prompt, model="gemini-2.0-flash-lite")
            self.game.process_turn(action)
            time.sleep(self.delay_between_actions)
        print("  [Gameplay] 20 turns of gameplay completed.")
        
        # 3. Recall & Evaluation Phase for Long-Term Item
        item_recall_prompt = f"The fact to verify is: '{item_key_fact}'. Generate a player action that presents a situation where this item would be relevant, without naming the item."
        item_recall_action = self.tester_llm.generate(prompt=item_recall_prompt, model="gemini-2.5-pro")
        item_recall_response = self.game.process_turn(item_recall_action)
        item_result = self._get_evaluation("long_term_item_recall", item_key_fact, item_recall_action, item_recall_response)
        self.log_result(item_result)
        time.sleep(self.delay_between_actions)

        # 4. Recall & Evaluation Phase for NPC Memory
        npc_recall_prompt = f"The fact to verify is: '{npc_key_fact}'. Generate a player action that tests the NPC's memory of this fact during a new conversation."
        npc_recall_action = self.tester_llm.generate(prompt=npc_recall_prompt, model="gemini-2.5-pro")
        npc_recall_response = self.game.process_turn(npc_recall_action)
        npc_result = self._get_evaluation("npc_memory_recall", npc_key_fact, npc_recall_action, npc_recall_response)
        self.log_result(npc_result)

    def run_quest_log_test(self):
        """Tests the dynamic quest log functionality."""
        print("\n--- RUNNING: Dynamic Quest Log Test ---")
        self.game.setup_new_session(story_id=f"quest_log_test_{uuid.uuid4()}")

        # 1. Setup: Get a quest
        quest_setup_action = "As a player, generate an action that is highly likely to result in an NPC giving you a new quest."
        player_action = self.tester_llm.generate(prompt=quest_setup_action, model="gemini-2.0-flash-lite")
        dm_response = self.game.process_turn(player_action)
        
        active_quests = self.game.quest_log.get('active', {})
        if not active_quests:
            self.log_result({"test_name": "quest_log_tracking", "passed": False, "reasoning": "No quest was added to the log after a quest-giving action."})
            return
        
        quest_name = list(active_quests.keys())[0]
        quest_objective = active_quests[quest_name]
        key_fact = f"Quest '{quest_name}' with objective '{quest_objective}' should be active."
        print(f"  [Setup] Ground truth quest established: {key_fact}")
        time.sleep(self.delay_between_actions)
        
        # 2. Verification
        recall_action = "What are my current quests?"
        dm_response = self.game.process_turn(recall_action)
        
        # 3. Evaluation
        result = self._get_evaluation("quest_log_recall", key_fact, recall_action, dm_response)
        self.log_result(result)

    def run_all_tests(self):
        """Runs the full suite of automated tests with delays."""
        print("======== STARTING AUTOMATED TEST SUITE ========")
        self.run_short_term_test()
        print(f"\n...Pausing for {self.delay_between_tests} seconds before next test...")
        time.sleep(self.delay_between_tests)
        self.run_long_term_and_npc_test()
        print(f"\n...Pausing for {self.delay_between_tests} seconds before next test...")
        time.sleep(self.delay_between_tests)
        self.run_quest_log_test()
        print("\n======== AUTOMATED TEST SUITE COMPLETE ========")
        print(f"Results have been saved to {self.log_file}")

if __name__ == '__main__':
    conductor = TestConductor()
    conductor.run_all_tests()
