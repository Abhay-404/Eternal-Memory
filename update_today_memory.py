"""
Update Today's Memory
Main script to sync audio from Drive and update all memory tiers
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from src.main import MyBrain
from src.services.drive_sync import DriveSync
from src.utils.config import Config


def check_and_create_weekly_summary(brain: MyBrain, date: datetime) -> bool:
    """Check if week is complete and create weekly summary if needed"""
    # A week is complete if we have a Sunday
    if date.weekday() != 6:  # Not Sunday
        return False

    # Get Monday of this week
    week_start = date - timedelta(days=6)
    week_key = week_start.strftime('%Y-W%W')

    # Check if summary already exists
    weekly_file = brain.summary_manager.summaries_dir / "weekly" / f"{week_key}.json"
    if weekly_file.exists():
        return False

    print(f"\n[Week completed! Creating weekly summary for {week_key}...]")

    try:
        weekly_data = brain.summary_manager.create_weekly_summary(week_start)

        # Embed in vector database
        embedding = brain.embedding_gen.generate_embedding(weekly_data['summary'])
        brain.hybrid_search.add_documents(
            texts=[weekly_data['summary']],
            embeddings=[embedding],
            metadata=[{
                "date": week_start.isoformat(),
                "week": week_key,
                "type": "weekly_summary"
            }]
        )

        print(f"[OK] Weekly summary created ({len(weekly_data['summary'].split())} words)")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to create weekly summary: {e}")
        return False


def check_and_create_monthly_summary(brain: MyBrain, date: datetime) -> bool:
    """Check if month is complete and create monthly summary if needed"""
    # Check if next day is first of month (current day is last of month)
    next_day = date + timedelta(days=1)
    if next_day.day != 1:
        return False

    month_start = date.replace(day=1)
    month_key = month_start.strftime('%Y-%m')

    # Check if summary already exists
    monthly_file = brain.summary_manager.summaries_dir / "monthly" / f"{month_key}.json"
    if monthly_file.exists():
        return False

    print(f"\n[Month completed! Creating monthly summary for {month_start.strftime('%B %Y')}...]")

    try:
        monthly_data = brain.summary_manager.create_monthly_summary(month_start)

        # Embed in vector database
        embedding = brain.embedding_gen.generate_embedding(monthly_data['summary'])
        brain.hybrid_search.add_documents(
            texts=[monthly_data['summary']],
            embeddings=[embedding],
            metadata=[{
                "date": month_start.isoformat(),
                "month": month_key,
                "type": "monthly_summary"
            }]
        )

        print(f"[OK] Monthly summary created ({len(monthly_data['summary'].split())} words)")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to create monthly summary: {e}")
        return False


def process_day_audio(brain: MyBrain, date_str: str, audio_files: list) -> bool:
    """
    Process audio files for a specific day

    Args:
        brain: MyBrain instance
        date_str: Date string (YYYY-MM-DD)
        audio_files: List of audio file paths

    Returns:
        True if processing successful
    """
    date = datetime.strptime(date_str, '%Y-%m-%d')

    print(f"\n[Processing {date_str} - {len(audio_files)} audio file(s)]")

    # Step 1: Transcribe all audio files
    all_transcriptions = []
    combined_language = "Unknown"

    for i, audio_path in enumerate(audio_files, 1):
        print(f"  [{i}/{len(audio_files)}] Transcribing {Path(audio_path).name}...")

        try:
            result = brain.llm_client.transcribe_audio(audio_path)
            all_transcriptions.append(result['transcription'])
            combined_language = result['language']
            print(f"      [OK] {len(result['transcription'].split())} words")

        except Exception as e:
            print(f"      [ERROR] Transcription failed: {e}")
            return False

    # Combine all transcriptions
    combined_transcription = "\n\n".join(all_transcriptions)

    print(f"  [Total transcription: {len(combined_transcription.split())} words]")

    # Step 2: Create daily summary
    print(f"  [Creating daily summary...]")
    try:
        daily_summary = brain.summary_manager.create_daily_summary(
            date=date,
            transcription=combined_transcription,
            language=combined_language,
            audio_path=audio_files[0]  # Reference first file
        )
        print(f"  [OK] Daily summary: {len(daily_summary['summary'].split())} words")

    except Exception as e:
        print(f"  [ERROR] Summary creation failed: {e}")
        return False

    # Step 3: Update primary context
    print(f"  [Updating primary context...]")
    try:
        brain.context_manager.update_context(daily_summary['summary'])
        print(f"  [OK] Primary context updated")

    except Exception as e:
        print(f"  [ERROR] Primary context update failed: {e}")
        return False

    # Step 4: Update short-term memory
    print(f"  [Updating short-term memory...]")
    try:
        brain.short_term_memory.update(reference_date=date)
        print(f"  [OK] Short-term memory updated")

    except Exception as e:
        print(f"  [ERROR] Short-term memory update failed: {e}")
        return False

    # Step 5: Embed in vector database
    print(f"  [Embedding in vector database...]")
    try:
        # 5a. Embed Daily Summary
        embedding = brain.embedding_gen.generate_embedding(daily_summary['summary'])
        brain.hybrid_search.add_documents(
            texts=[daily_summary['summary']],
            embeddings=[embedding],
            metadata=[{
                "date": date.isoformat(),
                "type": "daily_summary",
                "language": combined_language
            }]
        )
        print(f"     -> Daily summary embedded")

        # 5b. Embed Raw Transcription Chunks
        # Chunk the text
        def chunk_text(text, max_chunk_size=1000, overlap=80):
            words = text.split()
            chunks = []
            if len(words) <= max_chunk_size:
                return [text]
            step = max_chunk_size - overlap
            for i in range(0, len(words), step):
                chunk = ' '.join(words[i:i + max_chunk_size])
                chunks.append(chunk)
                if i + max_chunk_size >= len(words):
                    break
            return chunks

        chunks = chunk_text(combined_transcription)
        print(f"     -> Chunking transcription into {len(chunks)} parts...")

        chunk_embeddings = []
        for chunk in chunks:
            chunk_embeddings.append(brain.embedding_gen.generate_embedding(chunk))
        
        chunk_metadata = [
            {
                "date": date.isoformat(),
                "type": "transcription_chunk",
                "language": combined_language,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            for i in range(len(chunks))
        ]

        brain.hybrid_search.add_documents(
            texts=chunks,
            embeddings=chunk_embeddings,
            metadata=chunk_metadata
        )
        print(f"     -> {len(chunks)} raw transcription chunks embedded")
        
        print(f"  [OK] All data embedded successfully")

    except Exception as e:
        print(f"  [ERROR] Embedding failed: {e}")
        return False

    # Step 6: Check if week/month completed
    check_and_create_weekly_summary(brain, date)
    check_and_create_monthly_summary(brain, date)

    print(f"  [OK] {date_str} processing complete!")
    return True


def main():
    """Main entry point"""

    print("=" * 80)
    print("MY_BRAIN - Update Today's Memory")
    print("=" * 80)

    # Configuration
    CREDENTIALS_PATH = str(Path(__file__).parent / "credentials.json")
    TOKEN_PATH = str(Path(__file__).parent / "token.json")
    FOLDER_ID = "15DiULoMdAweFs9_PFE5yKUAnaQSwi7JP"
    AUDIO_DIR = Config.DATA_DIR / "audio"

    # Check credentials
    if not Path(CREDENTIALS_PATH).exists():
        print("\n[ERROR] credentials.json not found!")
        print("Please set up Google Drive API first (see DRIVE_SETUP.md)")
        return

    # Initialize
    print("\n[Initializing...]")
    brain = MyBrain()
    drive_sync = DriveSync(CREDENTIALS_PATH, TOKEN_PATH, FOLDER_ID)

    # Authenticate
    print("[Authenticating with Google Drive...]")
    drive_sync.authenticate()

    # List audio files
    print("[Listing audio files from Drive...]")
    files = drive_sync.list_audio_files()

    if not files:
        print("[OK] No audio files found in Drive")
        return

    print(f"[OK] Found {len(files)} audio file(s)")

    # Organize by date
    files_by_date = drive_sync.organize_by_date(files)
    print(f"[OK] Organized into {len(files_by_date)} day(s)")

    for date_str, day_files in sorted(files_by_date.items()):
        print(f"  {date_str}: {len(day_files)} file(s)")

    # Process each day
    print("\n" + "=" * 80)
    print("Processing Audio")
    print("=" * 80)

    processed_days = 0
    failed_days = 0

    for date_str, day_files in sorted(files_by_date.items()):
        # Download files
        downloaded_paths = []
        day_audio_dir = AUDIO_DIR / date_str
        day_audio_dir.mkdir(parents=True, exist_ok=True)

        for file in day_files:
            destination = str(day_audio_dir / file['name'])
            if drive_sync.download_file(file['id'], destination):
                downloaded_paths.append(destination)

        if not downloaded_paths:
            print(f"\n[SKIP] No files downloaded for {date_str}")
            failed_days += 1
            continue

        # Process day
        if process_day_audio(brain, date_str, downloaded_paths):
            # Delete from Drive after successful processing
            print(f"  [Deleting from Drive...]")
            for file in day_files:
                if drive_sync.delete_file(file['id']):
                    print(f"    [OK] Deleted {file['name']}")

            processed_days += 1

        else:
            print(f"  [WARNING] Processing failed - files kept in Drive")
            failed_days += 1

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"  Days processed: {processed_days}")
    print(f"  Days failed: {failed_days}")

    if processed_days > 0:
        print("\n[OK] Memory updated successfully!")
        print("\nQuery your memories: python query.py")


if __name__ == "__main__":
    main()
