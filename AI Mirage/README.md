# AI Mirage – The Dungeon Master Game

**AI Mirage** is an advanced, text-based role-playing game powered by Large Language Models (LLMs). The core of this application is an intelligent memory system designed to overcome the typical limitations of LLMs, enabling long-term narrative consistency and a truly persistent world where character choices have lasting consequences.

The system features a **modular architecture** that separates memory management, LLM interaction, and game logic, making it robust and extensible. It leverages a **multi-provider LLM strategy**, using different models for tasks based on their strengths in speed, quality, and context window size.

---

## Test Results

All artifacts demonstrating the project's functionality, including automated test results, gameplay transcripts, and detailed memory logs, are located within the `test_results/` directory in this repository.

**[Browse the Test Results Directory](./test_results/)**

### Key Files in the Directory

Here is a guide to the most important files found inside `test_results/`:

-   **`test_results.log`**
    -   **What it is:** The primary summary output from the `automated_tester.py` script.
    -   **What it shows:** This file contains the final pass/fail judgment for each test case (e.g., 'short_term_recall', 'npc_memory_recall'). It includes the JSON evaluation from the QA Assessor LLM, which provides a `"passed": true/false` status and a detailed `"reasoning"` for each outcome. This is the main proof of the system's memory capabilities.

-   **`terminal_text.txt`**
    -   **What it is:** A full transcript of an interactive game session, showing the text exactly as it appears in the terminal.
    -   **What it shows:** The player's inputs, the rich narrative responses from the AI DM, and the step-by-step flow of a story. This demonstrates the creative and interactive quality of the game.

-   **`short_term_test_summary.txt`** and **`long_term_test_summary.txt`**
    -   **What they are:** These files are snapshots of the game's master recursive summary, captured at the end of the short-term and long-term automated tests, respectively.
    -   **What they show:** These documents demonstrate the **evolution of the long-term narrative memory**. The `short_term_test_summary.txt` file shows the recursive summary after a brief (~5 turn) adventure, while the `long_term_test_summary.txt` file shows how that summary has grown and integrated nearly 30 turns of gameplay. By comparing them, you can see how the system recursively condenses and retains the overarching plot over time.
      
-   **`logs/` (sub-directory)**
    -   **What it is:** A folder containing the verbose, timestamped logs from each individual system module (`game_loop.log`, `memory_manager.log`, `events.log`, `npcs.log`, etc.).
    -   **What it shows:** These files provide a granular, behind-the-scenes look at the system's internal operations. They are essential for in-depth debugging and verifying the flow of data between components.

---

## System Overview

This project is an intelligent narrative system that combines creativity with consistency, designed to emulate a human Dungeon Master.

---

## Core Features

### Hybrid Memory System
Implements a dual-memory architecture to ensure both short-term conversational flow (**Working Memory**) and long-term plot consistency (**Persistent Memory**).

### Summarized Working Memory
Uses an LLM to create token-efficient summaries of the most recent turns (≈5 turns).

### RAG-Powered Persistent Memory
A **Retrieval-Augmented Generation (RAG)** system using **ChromaDB** stores and retrieves key events from the entire history of the adventure (≈30 turns).

### Dynamic NPC Memory (Bonus Feature)
Characters (NPCs) have their own dedicated memory, allowing them to recall prior interactions and evolve accordingly. This is powered by an **LLM-based entity resolution system**.

### Automated Quest Log (Bonus Feature)
The system dynamically analyzes the narrative to identify, track, and reference player quests.

### Multi-Provider LLM Core
Intelligently routes tasks to the best-suited LLM API for optimal performance:

- **Groq API:** Used for high-speed tasks like gameplay generation, safety checks, and structured data extraction (Llama 3.1, Llama Guard).  
- **Google Gemini API:** Used for high-context tasks like recursive summarization (Gemini 1.5 Pro).

### Content Safety
Integrates a guard model to check both player input and AI-generated output, ensuring a safe and appropriate conversational experience.

### Save/Load System
Players can save their adventure at any time and resume it later, ensuring continuity across multiple sessions.

### Automated QA Suite
Includes an `automated_tester.py` script that uses an LLM-powered "Test Conductor" to automatically validate the AI DM's memory and features against the project's evaluation criteria.

---

## Technology Stack

- **Backend:** Python 3.10+  
- **LLM APIs:** Groq, Google AI (Gemini)  
- **Vector Database:** ChromaDB  
- **Embeddings:** sentence-transformers  
- **Data Handling:** pandas  

---

## Project Structure

```
.
├── core/
│   ├── game_loop.py
│   └── prompt_manager.py
├── llm/
│   ├── google_client.py
│   ├── groq_client.py
│   └── llm_interface.py
├── memory/
│   ├── memory_manager.py
│   ├── persistent_memory.py
│   └── working_memory.py
├── saves/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── main.py
├── README.md
├── requirements.txt
└── automated_tester.py
```

---

## Setup Guide

Follow these steps to get the project running on your local machine.

### 1. Clone the Repository

```bash
git clone https://github.com/m-saket/AI-Mirage
cd AI-Mirage
```

### 2. Create and Activate a Virtual Environment

```bash
# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

Install all the required Python libraries from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

You need to provide your API keys for the LLM services.  
Create a file named `.env` in the root directory and add your keys:

```ini
GROQ_API_KEY="your_groq_api_key_here"
GOOGLE_API_KEY="your_google_api_key_here"
GOOGLE_API_KEY2="your_second_google_api_key_here"
```

---

## Usage Instructions

The project has two main entry points: one for playing the game and one for running the automated tests.

### To Play the Game (Interactive Mode)

Run the `main.py` script.  
This will launch the game with a main menu where you can start a new adventure or load a saved one.

```bash
python main.py
```

### To Run the Automated Tester

Run the `automated_tester.py` script.  
This will execute the full suite of automated tests for short-term, long-term, NPC, and quest memory.  
The results will be saved to `test_results.log`.

```bash
python automated_tester.py
```

---
