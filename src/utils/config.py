import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration manager for MY_BRAIN"""

    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    AUDIO_DIR = DATA_DIR / "audio"
    TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
    SUMMARIES_DIR = DATA_DIR / "summaries"

    # Memory Settings
    PRIMARY_CONTEXT_MAX_WORDS = 500
    SHORT_TERM_MEMORY_DAYS = 14
    SHORT_TERM_MEMORY_MAX_WORDS = 8000

    # ChromaDB Settings
    CHROMA_DB_PATH = str(DATA_DIR / "chroma_db")
    COLLECTION_NAME = "my_brain_memories"

    # Gemini Model Settings
    GEMINI_MODEL = "gemini-3-flash-preview"
    EMBEDDING_MODEL = "gemini-embedding-001"

    # Audio Settings
    SUPPORTED_AUDIO_FORMATS = [".mp3", ".wav", ".m4a", ".flac"]

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        for directory in [cls.AUDIO_DIR, cls.TRANSCRIPTS_DIR, cls.SUMMARIES_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
