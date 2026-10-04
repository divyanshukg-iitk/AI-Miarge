# The persistent memory logic will be written here
# This will be used to store the long-term memory of the game
# and will be used to provide context to the LLM for generating responses

# We will be using ChromaDB as our vector database to store the long-term memory
# We will use the sentence-transformers library to generate embeddings for the text
# We will use the retriever from ChromaDB to fetch relevant context from the long-term memory

import chromadb
import json
import uuid 
import logging
from sentence_transformers import SentenceTransformer
from chromadb.utils import embedding_functions
import pandas as pd

class PersistentMemory:
    """
    Manages the long-term memory of the game, including both a RAG-based
    event store and a recursive narrative summary.
    """
    def __init__(self, persist_directory: str = "./data/vector_store", summary_file_path: str = "./data/summary.txt", model_name: str = 'all-MiniLM-L6-v2', event_log_file: str = 'logs/events.log', npc_log_file: str = 'logs/npcs.log'):
        """
        Initializes the persistent memory components and sets up logging.
        """
        # --- A dedicated logger for this class ---
        self.event_logger = self._setup_logger('EventLogger', event_log_file)
        self.npc_logger = self._setup_logger('NpcLogger', npc_log_file)

        self.event_logger.info("PersistentMemory initializing...")
        self.event_logger.info("Vector store directory: %s", persist_directory)
        self.event_logger.info("Summary file path: %s", summary_file_path)

        # --- RAG Setup ---
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
        
        self.event_collection = self.client.get_or_create_collection(name="game_events", embedding_function=self.embedding_function)
        self.npc_collection = self.client.get_or_create_collection(name="npc_interactions", embedding_function=self.embedding_function)
        self.event_logger.info("Created/loaded ChromaDB collections: 'game_events' and 'npc_interactions'.")

        self.summary_file_path = summary_file_path
        self.event_logger.info("PersistentMemory initialized successfully.")

    def _setup_logger(self, name: str, log_file: str) -> logging.Logger:
        """A helper method to configure and return a logger."""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        if not logger.handlers:
            logger.addHandler(handler)
            
        return logger


    def add_event(self, event_data: dict):
        """
        Adds a new structured event to the vector store and logs the action.
        """
        if 'summary' not in event_data or 'turn' not in event_data:
            self.event_logger.error("Attempted to add event without 'summary' or 'turn' keys: %s", json.dumps(event_data))
            return
        
        metadata_to_store = event_data.copy()

        for key in list(metadata_to_store.keys()):
            if metadata_to_store[key] is None:
                self.event_logger.warning("Sanitizing event metadata: Removing key '%s' because its value was None.", key)
                del metadata_to_store[key]

        for key, value in metadata_to_store.items():
            if isinstance(value, (list, dict)):
                metadata_to_store[key] = json.dumps(value)

        event_summary = event_data['summary']
        event_id = f"event_turn_{event_data['turn']}_{uuid.uuid4()}"

        self.event_collection.add(
            documents=[event_summary],
            metadatas=[metadata_to_store], 
            ids=[event_id]
        )
        self.event_logger.info("Added event ID '%s' to RAG store. Data: %s", event_id, json.dumps(event_data))

    def retrieve_relevant_events(self, query_text: str, n_results: int = 4, distance_threshold: float = 0.8) -> list:
        """
        Retrieves the top N most semantically similar events from the vector store and logs the process.
        """
        self.event_logger.info("Retrieving up to %d events for query: '%s'", n_results, query_text)
        results = self.event_collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["metadatas", "distances"]
        )

        metadatas_list = results.get('metadatas', [[]])[0]
        distances_list = results.get('distances', [[]])[0]
        self.event_logger.info("ChromaDB returned %d potential events before filtering.", len(metadatas_list))

        if not metadatas_list:
            self.event_logger.warning("Query returned no results from ChromaDB.")
            return []

        relevant_metadata = []
        for metadata, distance in zip(metadatas_list, distances_list):
            if distance < distance_threshold:
                relevant_metadata.append(metadata)
            else:
                break 

        for event in relevant_metadata:
            for key, value in event.items():
                if isinstance(value, str) and value.startswith(('[', '{')):
                    try: event[key] = json.loads(value)
                    except json.JSONDecodeError: pass
                        
        self.event_logger.info("Returning %d events after applying distance threshold of %s.", len(relevant_metadata), distance_threshold)
        return relevant_metadata

    def add_npc_interaction(self, interaction_data: dict):
        """Adds a new structured NPC interaction and logs the action."""
        if 'summary' not in interaction_data or 'turn' not in interaction_data or 'canonical_name' not in interaction_data:
            self.npc_logger.error("NPC interaction_data must contain 'summary', 'turn', and 'canonical_name' keys. Data: %s", json.dumps(interaction_data))
            return

        metadata_to_store = interaction_data.copy()
        for key in list(metadata_to_store.keys()):
            if metadata_to_store[key] is None:
                self.npc_logger.warning("Sanitizing NPC metadata: Removing key '%s' because its value was None.", key)
                del metadata_to_store[key]

        for key, value in metadata_to_store.items():
            if isinstance(value, (list, dict)):
                metadata_to_store[key] = json.dumps(value)

        interaction_summary = interaction_data['summary']
        interaction_id = f"npc_{interaction_data['turn']}_{interaction_data['canonical_name']}_{uuid.uuid4()}"

        self.npc_collection.add(documents=[interaction_summary], metadatas=[metadata_to_store], ids=[interaction_id])
        self.npc_logger.info("Added NPC interaction ID '%s'. Data: %s", interaction_id, json.dumps(interaction_data))

    def get_all_known_npcs(self) -> list[dict]:
        """Retrieves a de-duplicated list of all known NPCs and logs the action."""
        self.npc_logger.info("Retrieving all known NPCs from the database...")
        try:
            results = self.npc_collection.get(include=["metadatas"])
            metadata_list = results.get('metadatas', [])
            self.npc_logger.info("Found %d total NPC interaction records.", len(metadata_list))

            if not metadata_list:
                return []

            df = pd.DataFrame(metadata_list)
            if 'canonical_name' not in df.columns or 'descriptor' not in df.columns:
                self.npc_logger.warning("NPC records are missing 'canonical_name' or 'descriptor' columns for de-duplication.")
                return []
            
            unique_npcs_df = df.drop_duplicates(subset=['canonical_name', 'descriptor'])
            self.npc_logger.info("De-duplicated to %d unique NPCs.", len(unique_npcs_df))
            
            return unique_npcs_df[['canonical_name', 'descriptor']].to_dict('records')

        except Exception as e:
            self.npc_logger.error("Error getting all known NPCs: %s", e)
            return []

    def retrieve_npc_interactions(self, canonical_name: str, descriptor: str, query_text: str, n_results: int = 5) -> list:
        """Retrieves memories for a specific NPC using metadata filters and logs the action."""
        self.npc_logger.info("Retrieving up to %d interactions for NPC '%s (%s)' with query: '%s'", n_results, canonical_name, descriptor, query_text)
        
        # The 'where' clause now filters on BOTH fields for a precise match
        where_clause = {
    "$and": [
        {"canonical_name": {"$eq": canonical_name}},
        {"descriptor": {"$eq": descriptor}}
    ]
}
        
        results = self.npc_collection.query(
            query_texts=[query_text], 
            n_results=n_results, 
            where=where_clause
        )
        
        retrieved_metadata = results.get('metadatas', [[]])[0]
        
        for interaction in retrieved_metadata:
            for key, value in interaction.items():
                if isinstance(value, str) and value.startswith(('[', '{')):
                    try: interaction[key] = json.loads(value)
                    except json.JSONDecodeError: pass
        
        self.npc_logger.info("Retrieved %d interactions for NPC '%s (%s)'.", len(retrieved_metadata), canonical_name, descriptor)
        return retrieved_metadata
    
    def read_summary(self) -> str:
        """
        Reads the current master summary from the summary file and logs the action.
        """
        self.event_logger.info("Reading narrative summary from %s", self.summary_file_path)
        try:
            with open(self.summary_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.event_logger.warning("Summary file not found at %s. Returning empty string.", self.summary_file_path)
            return ""

    def write_summary(self, new_summary: str):
        """
        Overwrites the summary file and logs the action.
        """
        with open(self.summary_file_path, 'w', encoding='utf-8') as f:
            f.write(new_summary)
        print(f"[Persistent Memory] Narrative summary has been updated in '{self.summary_file_path}'.")
        self.event_logger.info("Narrative summary updated in '%s'. New summary starts with: '%s...'", self.summary_file_path, new_summary[:80])

    def log_all_events(self):
        """
        Retrieves all events from the collection and writes them to the log file.
        """
        self.event_logger.info("--- Dumping All Events in Long-Term Memory ---")
        try:
            # The .get() method with no IDs retrieves everything.
            all_events = self.event_collection.get(include=["metadatas"])
            count = len(all_events['ids'])
            if count == 0:
                self.event_logger.info("The RAG store is currently empty.")
            else:
                self.event_logger.info("Found %d total events in the RAG store:", count)
                # The metadata is what we care about.
                for metadata in all_events['metadatas']:
                    self.event_logger.info(json.dumps(metadata, indent=2))
        except Exception as e:
            self.event_logger.error("Failed to dump events from ChromaDB: %s", e)
        self.event_logger.info("---------------------------------------------")


### DUMMY TESTING CODE BELOW ###
if __name__ == '__main__':
    import os
    if not os.path.exists('logs'):
        os.makedirs('logs')

    print("Testing PersistentMemory module...")
    memory = PersistentMemory(persist_directory="./data/test_vector_store")
    
    print("\n--- Testing RAG Store ---")
    event_to_add = { "turn": 15, "summary": "The party defeats the goblin chieftain..." }
    memory.add_event(event_to_add)

    event_with_multiple_lists = { "turn": 16, "summary": "The player talks to the bartender..."}
    memory.add_event(event_with_multiple_lists)

    retrieved = memory.retrieve_relevant_events(query_text="what did we find in the goblin cave?")

    print("\nDumping final database state to the log file...")
    memory.log_all_events()

    print("\nPersistentMemory module test complete. Check 'logs/persistent_memory.log' for details.")