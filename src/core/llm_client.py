from google import genai
from typing import Optional, List, Dict, Any
from src.utils.config import Config

class GeminiClient:
    """Wrapper for Google Gemini API using new genai SDK"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY in .env")

        self.client = genai.Client(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using Gemini

        Args:
            prompt: User prompt
            system_instruction: System instruction/context
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        try:
            # Build config
            config = genai.types.GenerateContentConfig(
                temperature=temperature,
            )
            if max_tokens:
                config.max_output_tokens = max_tokens
            if system_instruction:
                config.system_instruction = system_instruction

            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=config
            )

            return response.text

        except Exception as e:
            raise Exception(f"Gemini generation error: {str(e)}")

    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Gemini

        Args:
            audio_path: Path to audio file

        Returns:
            Dict with transcription and detected language
        """
        try:
            # Upload audio file to Gemini
            import mimetypes
            from pathlib import Path

            # Detect mime type
            mime_type, _ = mimetypes.guess_type(audio_path)
            if not mime_type:
                mime_type = "audio/mpeg"

            # Upload file
            file = self.client.files.upload(
                file=audio_path,
                config={"mime_type": mime_type}
            )

            # Transcribe with language detection
            prompt = """Transcribe this audio accurately.
Detect the language(s) used (Hindi, English, or Hinglish mix).
Return in this format:

LANGUAGE: <detected language(s)>
TRANSCRIPTION:
<full transcription>
"""

            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=[prompt, file]
            )

            result_text = response.text.strip()

            # Parse response - check if it follows the expected format
            lines = result_text.split('\n')
            language = "Unknown"
            transcription = ""

            if "LANGUAGE:" in result_text and "TRANSCRIPTION:" in result_text:
                # Expected format found
                for i, line in enumerate(lines):
                    if line.startswith("LANGUAGE:"):
                        language = line.replace("LANGUAGE:", "").strip()
                    elif line.startswith("TRANSCRIPTION:"):
                        transcription = '\n'.join(lines[i+1:]).strip()
                        break
            else:
                # Gemini didn't follow format - use full text as transcription
                transcription = result_text
                # Try to detect language from content
                if any(word in result_text.lower() for word in ['the', 'is', 'are', 'was', 'were']):
                    language = "English"
                elif any(char in result_text for char in ['क', 'ख', 'ग', 'घ', 'च']):
                    language = "Hindi"
                else:
                    language = "Mixed/Unknown"

            return {
                "transcription": transcription if transcription else result_text,
                "language": language,
                "audio_path": audio_path
            }

        except Exception as e:
            raise Exception(f"Audio transcription error: {str(e)}")
