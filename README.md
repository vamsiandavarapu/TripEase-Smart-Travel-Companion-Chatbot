# TripEase 🌍✈️

**TripEase** is an intelligent, AI-powered travel assistant and trip planner. It leverages advanced natural language processing and retrieval-augmented generation (RAG) to provide personalized, context-aware travel recommendations, route optimizations, and efficient conversational planning for users. 

## Features ✨
- **Intelligent Recommendations:** Locally executed Llama 3.2 for personalized advice.
- **RAG Integration:** ChromaDB & Sentence-BERT for accurate geographical data retrieval.
- **Interactive UI:** Streamlit frontend offering an intuitive chat interface.
- **Robust Backend:** FastAPI server managing conversational state and LLM orchestration.
- **Route Optimization:** Utilizes the Haversine formula to optimize travel sequences.
- **Context Management:** Maintains conversational memory for seamless follow-up questions.

## Architecture 🏗️
- **Frontend:** Streamlit (`src/app.py`, `src/ui_components.py`)
- **Backend API:** FastAPI application (`src/api.py`, `src/api_client.py`)
- **AI Core:** RAG Engine & NLP (`src/rag_engine.py`, `src/context_manager.py`)
- **Database & Auth:** SQLite & ChromaDB (`src/database.py`, `src/auth_manager.py`)

## Getting Started 🚀

### Prerequisites
- Python 3.9+, [Ollama](https://ollama.ai/) (Llama 3.2 local), Windows PowerShell

### Installation
1. Clone the repository and navigate to the root:
   ```bash
   git clone <repository-url> && cd "Capstone -final"
   ```
2. Setup virtual environment:
   ```bash
   python -m venv venv_new
   .\venv_new\Scripts\Activate.ps1
   ```
3. Install the dependencies and pull the Llama model:
   ```bash
   pip install -r current_requirements.txt
   ollama pull llama3.2
   ```

### Running the Application
Use the provided PowerShell script to start both Backend (port 8000) and Frontend (port 8501):
```bash
.\start_both_servers.ps1
```
Alternatively, start only the backend: `.\start_backend.ps1`

## Project Structure 📂
- `src/` - Core API, UI, RAG logic, and context management.
- `chroma_db/` - Vector DB storage for RAG.
- `Document/` & `data/` - Source files dataset for embeddings.
- `tripease_user_data.db` & `auth_users.db` - SQLite local databases.
- `start_both_servers.ps1` - Execution script to boot up the entire application stack.

## Technologies Used 💻
FastAPI, Streamlit, Llama 3.2, Sentence-BERT (SentenceTransformers), ChromaDB, SQLite.


