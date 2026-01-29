import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.utils.config import Config
from src.core.llm_client import GeminiClient

class SummaryManager:
    """Manages hierarchical summaries (daily, weekly, monthly)"""

    def __init__(self, summaries_dir: Optional[Path] = None):
        self.summaries_dir = summaries_dir or Config.SUMMARIES_DIR
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.llm_client = GeminiClient()

        (self.summaries_dir / "daily").mkdir(exist_ok=True)
        (self.summaries_dir / "weekly").mkdir(exist_ok=True)
        (self.summaries_dir / "monthly").mkdir(exist_ok=True)

    def _get_summary_path(self, period: str, date: datetime) -> Path:
        """Get file path for a summary"""
        if period == "daily":
            filename = f"{date.strftime('%Y-%m-%d')}.json"
            return self.summaries_dir / "daily" / filename
        elif period == "weekly":
            filename = f"{date.strftime('%Y-W%W')}.json"
            return self.summaries_dir / "weekly" / filename
        elif period == "monthly":
            filename = f"{date.strftime('%Y-%m')}.json"
            return self.summaries_dir / "monthly" / filename
        else:
            raise ValueError(f"Invalid period: {period}")

    def create_daily_summary(
        self,
        date: datetime,
        transcription: str,
        language: str,
        audio_path: str
    ) -> Dict[str, Any]:
        """Create daily summary from transcription"""
        day_str = date.strftime('%A, %Y-%m-%d')

        summary_prompt = f"""Summarize this daily audio ({language}) - {day_str}

TRANSCRIPTION:
{transcription}

CREATE STRUCTURED SUMMARY (300-400 words):

**OVERVIEW**: One-sentence summary
**ACTIVITIES**: What happened (chronological, with times if mentioned)
**WORK**: Projects, progress, decisions, blockers
**PEOPLE**: Name - what was discussed/done
**THOUGHTS**: Key insights, realizations, decisions
**MOOD**: Energy levels, emotional state, what drove it
**HEALTH**: Exercise, sleep, meals, symptoms
**GOALS**: Progress made, new goals, obstacles
**MENTIONS**: Books, tools, places, concepts discussed

GUIDELINES:
- Be specific: "Debugged payment API rate limiting bug" not "worked on code"
- Include names, numbers, metrics, times
- Note sentiment: "frustrated with", "excited about"
- Skip empty sections
- Make it searchable (use specific keywords)

Return ONLY the structured summary:"""

        try:
            summary_text = self.llm_client.generate(summary_prompt, temperature=0.5)

            summary_data = {
                "date": date.isoformat(),
                "language": language,
                "audio_path": audio_path,
                "summary": summary_text,
                "transcription": transcription,
                "word_count": len(transcription.split()),
                "created_at": datetime.now().isoformat()
            }

            summary_path = self._get_summary_path("daily", date)
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)

            return summary_data

        except Exception as e:
            raise Exception(f"Error creating daily summary: {str(e)}")

    def get_daily_summary(self, date: datetime) -> Optional[Dict[str, Any]]:
        """Get daily summary for a specific date"""
        summary_path = self._get_summary_path("daily", date)
        if summary_path.exists():
            with open(summary_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def get_daily_summaries_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get all daily summaries within a date range"""
        summaries = []
        current_date = start_date

        while current_date <= end_date:
            summary = self.get_daily_summary(current_date)
            if summary:
                summaries.append(summary)
            current_date += timedelta(days=1)

        return summaries

    def create_weekly_summary(self, week_start_date: datetime) -> Dict[str, Any]:
        """Create weekly summary from daily summaries"""
        week_end_date = week_start_date + timedelta(days=6)
        daily_summaries = self.get_daily_summaries_in_range(week_start_date, week_end_date)

        if not daily_summaries:
            raise ValueError(f"No daily summaries found for week starting {week_start_date.date()}")

        combined_summaries = "\n\n".join([
            f"Day {i+1} ({s['date'][:10]}):\n{s['summary']}"
            for i, s in enumerate(daily_summaries)
        ])

        week_str = f"Week {week_start_date.strftime('%W, %Y')}"

        weekly_prompt = f"""Create WEEKLY SUMMARY for {week_str}

DAILY SUMMARIES:
{combined_summaries}

CREATE SUMMARY (400-600 words):

**WEEK OVERVIEW**: 2-3 sentences capturing the essence
**WORK**: Projects worked on, progress, wins, blockers
**PATTERNS**: Recurring themes, energy/mood trends
**ACHIEVEMENTS**: Key wins, completions, breakthroughs
**CHALLENGES**: Problems, frustrations, obstacles
**SOCIAL**: Key people, important conversations
**INSIGHTS**: Major learnings, decisions, realizations
**HEALTH**: Physical/mental trends, habits
**FORWARD**: What's carrying into next week

GUIDELINES:
- Synthesize, don't repeat: "Entire week on Project X - shipped feature Y" not "Mon worked on X, Tue worked on X"
- Find patterns: "Mentioned burnout 3x → mid-week energy crash"
- Track trajectories: mood improving? declining?
- Be specific: use actual names, projects, tech
- Note contradictions: "wanted to exercise daily, only did Monday"

Return ONLY the summary:"""

        try:
            summary_text = self.llm_client.generate(weekly_prompt, temperature=0.5)

            weekly_data = {
                "week_start": week_start_date.isoformat(),
                "week_end": week_end_date.isoformat(),
                "week_number": week_start_date.strftime('%W'),
                "year": week_start_date.year,
                "summary": summary_text,
                "daily_count": len(daily_summaries),
                "created_at": datetime.now().isoformat()
            }

            summary_path = self._get_summary_path("weekly", week_start_date)
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(weekly_data, f, indent=2, ensure_ascii=False)

            return weekly_data

        except Exception as e:
            raise Exception(f"Error creating weekly summary: {str(e)}")

    def create_monthly_summary(self, month_date: datetime) -> Dict[str, Any]:
        """Create monthly summary from daily summaries"""
        first_day = month_date.replace(day=1)
        if month_date.month == 12:
            last_day = month_date.replace(day=31)
        else:
            last_day = (month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1))

        daily_summaries = self.get_daily_summaries_in_range(first_day, last_day)

        if not daily_summaries:
            raise ValueError(f"No daily summaries found for {month_date.strftime('%Y-%m')}")

        combined_summaries = "\n\n".join([
            f"{s['date'][:10]}:\n{s['summary']}"
            for s in daily_summaries
        ])

        month_name = month_date.strftime('%B %Y')

        monthly_prompt = f"""Create MONTHLY SUMMARY for {month_name}

DAILY SUMMARIES ({len(daily_summaries)} days):
{combined_summaries[:12000]}{"...[truncated]" if len(combined_summaries) > 12000 else ""}

CREATE SUMMARY (600-1000 words):

**MONTH ESSENCE**: 3-4 sentences - what was this month about? Main theme?

**WORK**: Major projects, accomplishments, skills developed, challenges
**PERSONAL GROWTH**: Insights, behavioral changes, mindset shifts
**HEALTH**: Physical/mental trends, habits formed/broken
**RELATIONSHIPS**: Significant people, developments, social patterns
**GOALS**: Progress made, new goals, abandoned goals (why?)

**PATTERNS**:
- Behavioral: What's consistent? What's a struggle?
- Emotional: Mood trajectory, stress triggers
- Time: How was time allocated? Energy patterns?

**KEY MOMENTS**: 3-7 most important events with dates
**WINS**: Concrete accomplishments
**STRUGGLES**: Major obstacles, what didn't work
**EVOLUTION**: How did they change this month?

**NUMBERS** (if applicable):
- Days logged, projects active, people mentioned
- Books/resources, locations visited

GUIDELINES:
- Tell a story with arc and progression
- Quantify: "mentioned anxiety 12x, mostly work-related"
- Connect dots: "poor sleep → increased work irritability"
- Be honest: this is for self-growth
- Note turning points: "first 2 weeks on X, pivoted to Y mid-month"

Return ONLY the summary:"""

        try:
            summary_text = self.llm_client.generate(monthly_prompt, temperature=0.5)

            monthly_data = {
                "month": month_date.strftime('%Y-%m'),
                "month_start": first_day.isoformat(),
                "month_end": last_day.isoformat(),
                "summary": summary_text,
                "daily_count": len(daily_summaries),
                "created_at": datetime.now().isoformat()
            }

            summary_path = self._get_summary_path("monthly", month_date)
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(monthly_data, f, indent=2, ensure_ascii=False)

            return monthly_data

        except Exception as e:
            raise Exception(f"Error creating monthly summary: {str(e)}")

    def get_weekly_summaries_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get all weekly summaries within a date range"""
        weekly_dir = self.summaries_dir / "weekly"

        if not weekly_dir.exists():
            return []

        summaries = []

        for file_path in sorted(weekly_dir.glob("*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    weekly_data = json.load(f)

                week_start = datetime.fromisoformat(weekly_data['week_start'])

                # Check if this weekly summary falls within the range
                if start_date <= week_start <= end_date:
                    summaries.append(weekly_data)

            except Exception as e:
                print(f"[WARNING] Failed to load {file_path.name}: {e}")
                continue

        return summaries
