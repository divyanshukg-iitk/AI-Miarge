import json

def assemble_prompt(system_persona: str, narrative_summary: str, relevant_events: list, recent_history: str, player_input: str, npc_memories: list = None, quest_log: dict = None) -> str:
    """
    Assembles the final, multi-part prompt to be sent to the core LLM.

    This function follows the structured template designed to provide the LLM with a
    persona, high-level context, specific memories, and recent conversational flow,
    ensuring a coherent and contextually-aware response.

    Args:
        system_persona (str): The base instruction that defines the LLM's role as a DM.
        narrative_summary (str): The high-level summary of the story so far.
        relevant_events (list): A list of structured event dictionaries from the RAG store.
        recent_history (str): A formatted string of the last few conversational turns.
        player_input (str): The player's most recent action or dialogue.

    Returns:
        str: The fully assembled prompt ready for the LLM.
    """
    # 1. System Prompt
    prompt = f"{system_persona}\n\n"

    # 2. Narrative Summary (from Recursive Summarizer)
    prompt += "--- STORY SUMMARY SO FAR ---\n"
    prompt += f"{narrative_summary}\n\n"

    # 3. Relevant Past Events (from RAG) 
    if relevant_events:
        prompt += "--- RELEVANT PAST EVENTS ---\n"
        for event in relevant_events:
            # Format the event dictionary for clear presentation to the LLM
            event_str = f"Turn {event.get('turn', 'N/A')}: {event.get('summary', 'No summary available.')}"
            prompt += f"{event_str}\n"
        prompt += "\n"

    # NPC interactions
    if npc_memories:
        # Assumes all memories are for the same NPC in this context
        npc_name = npc_memories[0].get('canonical_name', 'this person')
        npc_desc = npc_memories[0].get('descriptor', '')
        prompt += f"--- YOUR MEMORIES OF {npc_name.upper()} ({npc_desc}) ---\n"
        for mem in npc_memories:
            mem_str = f"Turn {mem.get('turn', 'N/A')}: {mem.get('summary', 'No summary available.')}"
            prompt += f"{mem_str}\n"
        prompt += "\n"

    # Quest log
    if quest_log and quest_log.get('active'):
        prompt += "--- CURRENT QUESTS ---\n"
        for name, objective in quest_log['active'].items():
            prompt += f"- {name}: {objective}\n"
        prompt += "\n"
        
    # 4. Recent Conversation (from Working Memory)
    prompt += "--- RECENT CONVERSATION ---\n"
    prompt += f"{recent_history}\n\n"

    # 5. Player Action and Instruction
    prompt += "--- CURRENT SITUATION ---\n"
    prompt += f"Player: {player_input}\n"
    prompt += "DM:"

    return prompt

# --- Example Usage ---
# This demonstrates how the main game loop would use this function.
if __name__ == '__main__':
    print("Testing Prompt Assembler...")

    # 1. Define the persona for the DM
    persona = "You are a Dungeon Master for a fantasy role-playing game. Your role is to describe the world, narrate events, and react to the player's actions. You must be creative but also consistent with the story summary and past events provided."

    # 2. Get a context package (this would come from the MemoryManager)
    mock_context = {
        "narrative_summary": "The party, consisting of a rogue and a wizard, has just cleared out a goblin cave and is returning to the town of Brightwater.",
        "relevant_events": [
            {
                "turn": 15,
                "summary": "The party defeated the goblin chieftain and discovered a treasure map in his chest.",
                "location": "Goblin Cave Chieftain's Lair"
            }
        ],
        "recent_history": "Player: We search the chieftain's body.\n\nDM: You find a small, intricately carved wooden bird. It feels strangely warm to the touch. You pocket the 'Sparrow of Whispers'."
    }
    
    player_action = "We head back to town. On the way, I inspect the treasure map we found."

    # 3. Assemble the prompt
    final_prompt = assemble_prompt(
        system_persona=persona,
        narrative_summary=mock_context["narrative_summary"],
        relevant_events=mock_context["relevant_events"],
        recent_history=mock_context["recent_history"],
        player_input=player_action
    )

    print("\n--- FINAL ASSEMBLED PROMPT ---")
    print(final_prompt)
    print("---------------------------------")