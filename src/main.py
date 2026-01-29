"""
MY_BRAIN - Personal Memory System
Main application for processing daily audio and managing memory
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config
from src.core.llm_client import GeminiClient
from src.core.embeddings import EmbeddingGenerator
from src.database.chroma_db import ChromaVectorStore
from src.database.hybrid_search import HybridSearchEngine
from src.memory.primary_context import PrimaryContextManager
from src.memory.summary_manager import SummaryManager
from src.memory.short_term_memory import ShortTermMemory


class MyBrain:
    """Main application class for MY_BRAIN"""

    def __init__(self):
        Config.ensure_directories()

        # Initialize components
        self.llm_client = GeminiClient()
        self.embedding_gen = EmbeddingGenerator()
        self.vector_store = ChromaVectorStore()
        self.context_manager = PrimaryContextManager()
        self.summary_manager = SummaryManager()
        self.short_term_memory = ShortTermMemory()

        # Initialize hybrid search (BM25 + Vector)
        self.hybrid_search = HybridSearchEngine(self.vector_store, self.embedding_gen)

        print("[OK] MY_BRAIN initialized successfully")

    def process_audio(self, audio_path: str, date: Optional[datetime] = None) -> dict:
        """
        Process a single audio file through the entire pipeline

        Args:
            audio_path: Path to audio file
            date: Date of the audio (defaults to today)

        Returns:
            Processing results
        """
        if date is None:
            date = datetime.now()

        print(f"\n{'='*60}")
        print(f"Processing audio: {Path(audio_path).name}")
        print(f"Date: {date.strftime('%Y-%m-%d')}")
        print(f"{'='*60}\n")

        # Step 1: Transcribe audio
        print("→ Transcribing audio...")
        transcription_result = self.llm_client.transcribe_audio(audio_path)
        transcription = transcription_result['transcription']
        language = transcription_result['language']

        print(f"✓ Transcription complete")
        print(f"  Language: {language}")
        print(f"  Length: {len(transcription.split())} words")

        # Save transcription
        transcript_path = Config.TRANSCRIPTS_DIR / f"{date.strftime('%Y-%m-%d')}.txt"
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"Language: {language}\n")
            f.write(f"Date: {date.isoformat()}\n")
            f.write(f"Audio: {audio_path}\n")
            f.write(f"\n{'='*60}\n\n")
            f.write(transcription)
        print(f"✓ Saved transcription to {transcript_path}")

        # Step 2: Create daily summary
        print("\n→ Generating daily summary...")
        daily_summary = self.summary_manager.create_daily_summary(
            date=date,
            transcription=transcription,
            language=language,
            audio_path=audio_path
        )
        print(f"✓ Daily summary created")
        print(f"  Summary length: {len(daily_summary['summary'].split())} words")

        # Step 3: Chunk transcription and generate embeddings
        print("\n→ Generating embeddings...")
        chunks = self._chunk_text(transcription, max_chunk_size=800)
        print(f"  Created {len(chunks)} chunks")

        embeddings = []
        for i, chunk in enumerate(chunks):
            embedding = self.embedding_gen.generate_embedding(chunk)
            embeddings.append(embedding)

        print(f"✓ Generated {len(embeddings)} embeddings")

        # Step 4: Store in vector database
        print("\n→ Storing in vector database...")
        metadata = [
            {
                "date": date.isoformat(),
                "language": language,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "audio_path": audio_path,
                "type": "transcription_chunk"
            }
            for i in range(len(chunks))
        ]

        doc_ids = self.hybrid_search.add_documents(
            texts=chunks,
            embeddings=embeddings,
            metadata=metadata
        )
        print(f"[OK] Stored {len(doc_ids)} chunks in ChromaDB + BM25 index")

        # Step 5: Update primary context
        print("\n>> Updating primary context...")
        updated_context = self.context_manager.update_context(
            new_daily_summary=daily_summary['summary'],
            transcription=transcription
        )
        print(f"[OK] Primary context updated")
        print(f"  Current word count: {updated_context['word_count']}/500")

        # Step 6: Update short-term memory
        print("\n>> Updating short-term memory...")
        short_term = self.short_term_memory.update(reference_date=date)
        print(f"[OK] Short-term memory updated")
        print(f"  Word count: {short_term['word_count']}/8000")
        print(f"  Contains last 14 days + all important user facts")

        # Summary
        print(f"\n{'='*60}")
        print("[OK] Processing complete!")
        print(f"{'='*60}")

        return {
            "transcription": transcription,
            "language": language,
            "daily_summary": daily_summary,
            "chunks_stored": len(doc_ids),
            "primary_context_words": updated_context['word_count']
        }

    def _chunk_text(self, text: str, max_chunk_size: int = 500, overlap: int = 80) -> list:
        """
        Chunk text into smaller pieces for embedding with overlap

        Args:
            text: Input text
            max_chunk_size: Maximum words per chunk
            overlap: Number of words to overlap between chunks

        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []

        if len(words) <= max_chunk_size:
            return [text]

        step = max_chunk_size - overlap
        for i in range(0, len(words), step):
            chunk = ' '.join(words[i:i + max_chunk_size])
            chunks.append(chunk)

            # Stop if we've covered all words
            if i + max_chunk_size >= len(words):
                break

        return chunks

    def query_memory(self, query: str, limit: int = 5, use_hybrid: bool = True) -> list:
        """
        Query the memory system using hybrid search (BM25 + Vector)

        Args:
            query: Search query
            limit: Number of results
            use_hybrid: Use hybrid search (BM25+Vector) vs vector only

        Returns:
            List of relevant memories
        """
        print(f"\nQuerying memory: '{query}'")

        if use_hybrid:
            # Use hybrid search (BM25 + Vector)
            results = self.hybrid_search.search(
                query=query,
                limit=limit,
                vector_weight=0.7,  # 70% semantic
                bm25_weight=0.3     # 30% keyword
            )
            print(f"Found {len(results)} results (hybrid search: BM25 + Vector)\n")
        else:
            # Use vector search only
            query_embedding = self.embedding_gen.generate_query_embedding(query)
            results = self.vector_store.search(
                query_embedding=query_embedding,
                limit=limit
            )
            print(f"Found {len(results)} results (vector search only)\n")

        return results

    def get_primary_context(self) -> str:
        """Get current primary context"""
        return self.context_manager.get_context()

    def get_short_term_memory(self) -> str:
        """Get short-term memory (last 14 days + user facts)"""
        return self.short_term_memory.get_memory()

    def get_summary(self, period: str, date: datetime):
        """Get summary for a specific period"""
        if period == "daily":
            return self.summary_manager.get_daily_summary(date)
        # Add weekly/monthly when needed
        return None


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='MY_BRAIN - Personal Memory System')
    parser.add_argument('--audio', type=str, help='Path to audio file to process')
    parser.add_argument('--query', type=str, help='Query to search memories')
    parser.add_argument('--context', action='store_true', help='Show primary context')

    args = parser.parse_args()

    # Initialize MY_BRAIN
    brain = MyBrain()

    if args.audio:
        # Process audio file
        audio_path = Path(args.audio)
        if not audio_path.exists():
            print(f"Error: Audio file not found: {audio_path}")
            return

        brain.process_audio(str(audio_path))

    elif args.query:
        # Query memory
        results = brain.query_memory(args.query)

        for i, result in enumerate(results, 1):
            print(f"{i}. [Date: {result['metadata'].get('date', 'Unknown')}]")
            print(f"   {result['text'][:200]}...")
            print()

    elif args.context:
        # Show primary context
        context = brain.get_primary_context()
        print("\nPRIMARY CONTEXT:")
        print("=" * 60)
        print(context if context else "Empty")
        print("=" * 60)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
