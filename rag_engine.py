import os, warnings, chromadb, threading, re, pandas as pd
from chromadb.config import Settings
from functools import lru_cache
warnings.filterwarnings("ignore", category=UserWarning, module="google.rpc")
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
try:
    from langchain_community.llms import LlamaCpp
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
try:
    from langchain_classic.chains.retrieval_qa.base import RetrievalQA
    from langchain_core.prompts import PromptTemplate
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    try:
        from langchain.chains import RetrievalQA
        from langchain_core.prompts import PromptTemplate
        from langchain_community.vectorstores import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        RetrievalQA = PromptTemplate = Chroma = HuggingFaceEmbeddings = None
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        RetrievalQA = PromptTemplate = Chroma = HuggingFaceEmbeddings = None

from src.context_manager import (
    detect_city_in_query, 
    KNOWN_CITIES_SET, 
    extract_context_from_history, 
    detect_unknown_city, 
    detect_seasonal_intent
)

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/llama32/Llama-3.2-1B-Instruct-Q4_K_M.gguf"))
EMBEDDING_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/all-MiniLM-L6-v2"))
CHROMA_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../chroma_db"))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))

class RAGEngine:
    def __init__(self):
        self._embedding_function = None
        self._vector_store = None
        self.llm = None
        self.model_loaded = False
        self._load_lock = threading.Lock()

    @property
    def embedding_function(self):
        if not self._embedding_function and LANGCHAIN_AVAILABLE:
            model = EMBEDDING_MODEL_PATH if os.path.exists(EMBEDDING_MODEL_PATH) else "sentence-transformers/all-MiniLM-L6-v2"
            self._embedding_function = HuggingFaceEmbeddings(model_name=model)
        return self._embedding_function

    @property
    def vector_store(self):
        if not self._vector_store and self.embedding_function:
            client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
            self._vector_store = Chroma(client=client, collection_name="tripease_collection", embedding_function=self.embedding_function)
        return self._vector_store

    def load_model(self):
        # Trigger embedding and vector store load in the background thread
        _ = self.vector_store 
        if self.model_loaded: return
        with self._load_lock:
            if self.model_loaded: return
            if LLAMA_CPP_AVAILABLE and os.path.exists(MODEL_PATH):
                try:
                    self.llm = LlamaCpp(model_path=MODEL_PATH, temperature=0.1, max_tokens=150, n_ctx=2048, n_threads=6, n_batch=512, streaming=False, verbose=False, repeat_penalty=1.2)
                    self.model_loaded = True
                except Exception as e: print(f"Error loading model: {e}")
            else: print(f"Warning: Model not found at {MODEL_PATH}")

    def analyze_query_intent(self, query):
        if not self.llm: return "GENERAL", None
        p = f"""<|start_header_id|>system<|end_header_id|>Travel Chatbot NLU. Classify into: SMALL_TALK, SPECIFIC_LOCATION, SEASONAL, GENERAL. Output EXACTLY: TYPE: [T] ENTITY: [E]
Examples: "Hi" -> TYPE: SMALL_TALK, ENTITY: None; "Trip to Hyderabad" -> TYPE: SPECIFIC_LOCATION, ENTITY: Hyderabad<|eot_id|><|start_header_id|>user<|end_header_id|>{query}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
        try:
            res = str(self.llm.invoke(p)).strip(); intent, entity = "GENERAL", None
            for l in res.split('\n'):
                if "TYPE:" in l: intent = l.split("TYPE:")[1].strip()
                if "ENTITY:" in l: entity = l.split("ENTITY:")[1].strip(); entity = None if entity in ["None", ""] else entity
            return intent, entity
        except: return "GENERAL", None

    def query(self, prompt, history=[]):
        if not self.model_loaded: self.load_model()
        if not (self.vector_store and self.llm): return "RAG not ready."
        try:
            h_str = "".join([f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}\n" for m in history[-5:]])
            is_harmful = any(w in prompt.lower() for w in ["harm", "kill", "murder", "weapon", "bomb", "abuse", "violent", "illegal", "suicide", "hurt"])
            city = detect_city_in_query(prompt); unknown = detect_unknown_city(prompt) if not city else None
            intent, entity = (None, None) if city or unknown else self.analyze_query_intent(prompt)
            if intent == "SPECIFIC_LOCATION" and entity and entity.lower() not in KNOWN_CITIES_SET: unknown = entity
            if not city and not unknown and intent != "SMALL_TALK" and history: city = extract_context_from_history(history).get('city')
            
            if intent == "SMALL_TALK" and not is_harmful:
                return self.llm.invoke(f"<|start_header_id|>system<|end_header_id|>You are Nidhi, TripEase AI buddy. Reply warmly and concisely. Do not echo context. Respond to: {prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>")
            if is_harmful: return "I'm sorry, I cannot help with harmful activities. Try asking about travel in India! 😊"
            if unknown: return f"I currently specialize in Indian destinations and don't have data for {unknown.title()}. Try Goa or Jaipur! 😊"
            
            season = detect_seasonal_intent(prompt)
            if season and not detect_city_in_query(prompt):
                df = pd.read_csv(os.path.join(DATA_DIR, 'cities.csv'), encoding='latin1')
                matches = df[df['best_season'].str.lower().str.contains(season, na=False)] if 'best_season' in df.columns else pd.DataFrame()
                if not matches.empty:
                    cities = ", ".join(matches['city_name'].head(8).tolist())
                    return f"__SEASONAL__{season}|{cities}|Best cities for {season}: {cities}. Want a plan? 😊"
            
            if city and any(w in prompt.lower() for w in ["plan", "itinerary", "days", "schedule"]):
                return f"✨ Updated your dashboard with a {city} itinerary! Check the center panel. ✈️"

            docs = self.vector_store.similarity_search(prompt, k=5)
            ctx = "\n\n".join([d.page_content for d in docs]) if docs else "No context."
            template = """<|start_header_id|>system<|end_header_id|>You are Nidhi, TripEase AI. 
Rules:
1. Provide a friendly, natural response based ONLY on the Context provided below.
2. If the answer is not in the Context, politely say you don't know and suggest asking about travel in India.
3. NEVER repeat raw keys like "Place:", "Category:", or "City ID:". 
4. Translate data into natural sentences (e.g., "Visit Talakaveri temple in Coorg" instead of "Place: Talakaveri").
5. Keep it conversational.

History: {h}
Context: {c}<|eot_id|><|start_header_id|>user<|end_header_id|>{p}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
            raw_response = self.llm.invoke(template.format(h=h_str, c=ctx, p=prompt))
            # Clean up potential model artifacts
            return str(raw_response).split("<|eot_id|>")[0].strip()
        except Exception as e: return f"Error: {e}"

rag_engine = RAGEngine()
