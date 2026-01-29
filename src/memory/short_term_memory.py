"""
Short-term Memory Manager
Stores everything major about user + last 14 days events (~8000 words max)
Updates daily using LLM to intelligently decide what to keep/update/remove
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from src.utils.config import Config
from src.memory.summary_manager import SummaryManager
from src.core.llm_client import GeminiClient


class ShortTermMemory:
    """
    Manages short-term memory: Everything major about user + last 14 days events
    Max ~8000 words
    Updates intelligently using LLM to decide what's relevant
    """

    def __init__(self, memory_file: Optional[Path] = None):
        self.memory_file = memory_file or (Config.DATA_DIR / "short_term_memory.json")
        self.summary_manager = SummaryManager()
        self.llm_client = GeminiClient()
        self._ensure_memory_file()
        self.last_processed_date = None

    def _ensure_memory_file(self):
        """Create memory file if it doesn't exist"""
        if not self.memory_file.exists():
            initial_memory = {
                "version": 1,
                "last_updated": datetime.now().isoformat(),
                "word_count": 0,
                "memory_text": "No memories yet. Awaiting first update."
            }
            self._save_memory(initial_memory)

    def _save_memory(self, memory_data: Dict[str, Any]):
        """Save memory to file"""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, indent=2, ensure_ascii=False)

    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from file"""
        with open(self.memory_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def update(self, reference_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Update short-term memory with new daily information

        Args:
            reference_date: Date to use as "now" (for testing with historical data)

        Returns:
            Updated memory data
        """
        # Determine the reference date
        if reference_date:
            current_date = reference_date
            self.last_processed_date = reference_date
        elif self.last_processed_date:
            current_date = self.last_processed_date
        else:
            # Get the most recent daily summary date
            all_summaries = self.summary_manager.get_daily_summaries_in_range(
                datetime(2000, 1, 1), datetime.now()
            )
            if all_summaries:
                current_date = datetime.fromisoformat(all_summaries[-1]['date'])
                self.last_processed_date = current_date
            else:
                current_date = datetime.now()

        # Load current short-term memory
        current_memory_data = self._load_memory()
        current_memory = current_memory_data.get("memory_text", "")
        current_word_count = current_memory_data.get("word_count", 0)

        # Get today's daily summary
        today_summary = self.summary_manager.get_daily_summary(current_date)
        if not today_summary:
            print(f"[WARNING] No daily summary found for {current_date.date()}")
            return current_memory_data

        # Get most recent weekly summary (for broader context)
        start_date = current_date - timedelta(days=14)
        weekly_summaries = self.summary_manager.get_weekly_summaries_in_range(
            start_date, current_date
        )

        recent_weekly = ""
        if weekly_summaries:
            # Get the most recent weekly summary
            recent_weekly = weekly_summaries[-1].get('summary', '')[:1000]  # First 1000 chars

        # Build update prompt for LLM
        update_prompt = f"""You are updating the SHORT-TERM MEMORY for a user.

SHORT-TERM MEMORY PURPOSE:
- Everything major about the user (goals, projects, relationships, health, patterns)
- Last 14 days of events and activities
- Max: 8000 words | Target: 6000-7000 words

CURRENT SHORT-TERM MEMORY ({current_word_count} words):
{current_memory if current_memory else "[Empty - first entry]"}

{'='*80}

TODAY'S NEW INFORMATION:
Date: {current_date.date()}

Daily Summary:
{today_summary['summary']}

Recent Weekly Context (for reference):
{recent_weekly if recent_weekly else "[No weekly summary available]"}

{'='*80}

UPDATE INSTRUCTIONS:

1. **KEEP & UPDATE**:
   - All major facts about user (identity, goals, projects, relationships)
   - Events from last 14 days (remove events older than {start_date.date()})
   - Recurring patterns and themes
   - Important health/emotional states

2. **ADD**:
   - New significant information from today
   - New patterns or changes you notice
   - Important events that should be remembered

3. **REMOVE**:
   - Events older than 14 days
   - Outdated information (completed projects, resolved issues)
   - One-time trivial details

4. **FORMAT**:
   - Start with "MAJOR USER INFO:" section (identity, ongoing projects, relationships, health)
   - Then "LAST 14 DAYS EVENTS:" section (chronological, with dates)
   - Use bullet points for clarity
   - Include dates for events: [YYYY-MM-DD]

5. **WORD COUNT**:
   - Target: 6000-7000 words
   - Max: 8000 words
   - If approaching limit, prioritize recent events and major user info

OUTPUT THE UPDATED SHORT-TERM MEMORY (ONLY the memory text, no meta-commentary):"""

        try:
            # Generate updated memory using LLM
            updated_memory = self.llm_client.generate(
                prompt=update_prompt,
                temperature=0.3,
                max_tokens=12000  # Allow space for 8000 words
            )

            # Clean up the response
            updated_memory = updated_memory.strip()

            # Calculate word count
            word_count = len(updated_memory.split())

            # If still exceeds 8000 words, ask LLM to compress
            if word_count > 8000:
                compress_prompt = f"""The short-term memory is too long ({word_count} words).

Compress it to MAX 8000 words while keeping:
1. All major user info (identity, goals, projects, relationships)
2. Most important events from last 14 days
3. Key patterns and themes

CURRENT MEMORY:
{updated_memory}

OUTPUT COMPRESSED VERSION (max 8000 words):"""

                updated_memory = self.llm_client.generate(
                    prompt=compress_prompt,
                    temperature=0.3,
                    max_tokens=12000
                )

                updated_memory = updated_memory.strip()
                word_count = len(updated_memory.split())

            # Save updated memory
            memory_data = {
                "version": 1,
                "last_updated": current_date.isoformat(),
                "word_count": word_count,
                "memory_text": updated_memory,
                "last_daily_summary_date": current_date.date().isoformat()
            }

            self._save_memory(memory_data)

            print(f"[OK] Short-term memory updated: {word_count} words")
            return memory_data

        except Exception as e:
            print(f"[ERROR] Failed to update short-term memory: {e}")
            return current_memory_data

    def get_memory(self) -> str:
        """
        Get the current short-term memory text

        Returns:
            Short-term memory text
        """
        memory_data = self._load_memory()
        return memory_data.get('memory_text', '')

    def get_memory_data(self) -> Dict[str, Any]:
        """Get full memory data with metadata"""
        return self._load_memory()
