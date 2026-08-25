"""
Loads config from .env file (or real env vars, e.g.  in github Actions.).
One source of truth for settings, so nothing else re-reads env vars.
"""

""" Imports """

import os
from dotenv import load_dotenv

""" The Loader Call """
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_MODEL = "gemini-3.1-flash-lite"

SCANNABLE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".rs",
    ".php",
    ".rb",
    ".go",
}

SKIP_DIRS = {".git", "node_modules", "venv", "__pycache__", "dist", "build"}


# --- RAG SETTINGS --- #

EMBEDDING_MODEL = "all-MiniLM-L6-v2" # from sentence-transformers

CHROMA_PERSIST_DIR = "./chroma_db"
CHROMA_COLLECTION = "codebase"

# --- No of related chunks to inject per file under review --- #

RETRIEVAL_TOP_K = 5

# --- FallBack for chunking when AST Parsing isn't available for a lamguage --- #

FALLBACK_CHUNK_LINES = 60
FALLBACK_CHUNK_OVERLAP = 10

