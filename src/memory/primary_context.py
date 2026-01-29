import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from src.utils.config import Config
from src.core.llm_client import GeminiClient

class PrimaryContextManager:
    """Manages the primary context (max 500 words) that goes with every LLM call"""

    def __init__(self, context_file: Optional[Path] = None):
        self.context_file = context_file or (Config.DATA_DIR / "primary_context.json")
        self.llm_client = GeminiClient()
        self._ensure_context_file()

    def _ensure_context_file(self):
        """Create context file if it doesn't exist"""
        if not self.context_file.exists():
            initial_context = {
                "version": 1,
                "last_updated": datetime.now().isoformat(),
                "word_count": 0,
                "context": ""
            }
            self._save_context(initial_context)

    def _save_context(self, context_data: Dict[str, Any]):
        """Save context to file"""
        self.context_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.context_file, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, indent=2, ensure_ascii=False)

    def _load_context(self) -> Dict[str, Any]:
        """Load context from file"""
        with open(self.context_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_context(self) -> str:
        """Get the current primary context text"""
        context_data = self._load_context()
        return context_data.get("context", "")

    def get_full_context_data(self) -> Dict[str, Any]:
        """Get the full context data including metadata"""
        return self._load_context()

    def update_context(self, new_daily_summary: str) -> Dict[str, Any]:
        """Update primary context based on new daily summary"""
        current_data = self._load_context()
        current_context = current_data.get("context", "")
        today = datetime.now().strftime('%Y-%m-%d')

        update_prompt = f"""Update PRIMARY CONTEXT about the user(max 500 words) - goes with EVERY LLM call.

CURRENT CONTEXT ({current_data.get('word_count', 0)} words):
{current_context if current_context else "[Empty - first entry]"}

TODAY'S INFO ({today}):
Summary: {new_daily_summary}


WHAT TO KEEP:
- Identity (name, job, location, languages)
- Active goals & projects
- Key preferences
- Health info
- Important relationships
- Ongoing habits

UPDATE LOGIC:
ADD: New important facts
UPDATE: Changed info (new job, etc.)
REMOVE: Completed/outdated items
IGNORE: One-time events, trivial stuff

OUTPUT FORMAT:
**IDENTITY**: [name, job, location]
**WORK**: [role, projects, goals]
**HEALTH**: [conditions, habits]
**PEOPLE**: [key relationships]
**PREFERENCES**: [important likes/dislikes]
**ACTIVE**: [current focus areas]
**Other**: [Any other key]
Max 500 words. Be dense & specific. Return ONLY the updated context:"""

        try:
            updated_context = self.llm_client.generate(update_prompt, temperature=0.0)
            word_count = len(updated_context.split())

            # Compress if needed
            if word_count > 1000:
                compress_prompt = f"""Compress to max 500 words. Remove least important info.

{updated_context}

Keep: identity, active goals, health issues, key people
Remove: completed projects, redundant info
Use concise phrasing: "ML engineer at X" not "Works as ML engineer at X"

Return compressed version (max 500 words):"""

                updated_context = self.llm_client.generate(compress_prompt, temperature=0.3)
                word_count = len(updated_context.split())

            current_data["context"] = updated_context
            current_data["word_count"] = word_count
            current_data["last_updated"] = datetime.now().isoformat()
            self._save_context(current_data)

            return current_data

        except Exception as e:
            raise Exception(f"Error updating primary context: {str(e)}")

    def manual_update(self, new_context: str):
        """Manually set the primary context"""
        word_count = len(new_context.split())
        if word_count > 500:
            raise ValueError(f"Context exceeds 500 words ({word_count} words)")

        current_data = self._load_context()
        current_data["context"] = new_context
        current_data["word_count"] = word_count
        current_data["last_updated"] = datetime.now().isoformat()
        self._save_context(current_data)
        return current_data
