import os
import io
import wave
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()


class RubySTT:
    """
    Ruby Speech-to-Text (STT) Module.

    Priority chain (all FREE):
    1. Google Speech Recognition via `speech_recognition` lib (FREE, no key needed for basic use)
    2. Gemini audio transcription (free tier, if GEMINI_API_KEY is set)
    3. Returns empty string if all fail
    """

    def __init__(
        self,
        language_code: str = "en",
        sample_rate: int = 16_000,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        max_duration: float = 15.0,
    ):
        self.language_code = language_code
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_chunks = int(silence_duration * sample_rate / 1024)
        self.max_chunks = int(max_duration * sample_rate / 1024)

    def update_language(self, language_code: str):
        """Update the recognition language dynamically."""
        self.language_code = language_code.split("-")[0]

    def _record_audio(self) -> np.ndarray:
        """
        Record audio from microphone until silence is detected or max duration reached.
        """
        print("STT: Listening... (speak now)")
        frames = []
        silent_chunks = 0
        chunk_size = 1024
        started_speaking = False

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=chunk_size,
        ) as stream:
            for _ in range(self.max_chunks):
                data, _ = stream.read(chunk_size)
                rms = float(np.sqrt(np.mean(data ** 2)))

                if rms > self.silence_threshold:
                    started_speaking = True
                    silent_chunks = 0
                    frames.append(data.copy())
                elif started_speaking:
                    frames.append(data.copy())
                    silent_chunks += 1
                    if silent_chunks >= self.silence_chunks:
                        break

        if not frames:
            return np.zeros((0,), dtype="float32")

        return np.concatenate(frames, axis=0).flatten()

    def _audio_to_wav_bytes(self, audio: np.ndarray) -> bytes:
        """Convert float32 numpy array to WAV bytes."""
        audio_int16 = (audio * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
        buf.seek(0)
        return buf.read()

    def _convert_webm_to_wav(self, webm_bytes: bytes) -> bytes:
        """Convert WebM audio bytes to 16kHz mono WAV using imageio-ffmpeg."""
        import tempfile
        import subprocess
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f_in:
                f_in.write(webm_bytes)
                in_path = f_in.name
            out_path = in_path.replace(".webm", ".wav")
            subprocess.run([ffmpeg_exe, "-y", "-i", in_path, "-ac", "1", "-ar", "16000", out_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(out_path, "rb") as f_out:
                wav_bytes = f_out.read()
            os.remove(in_path)
            os.remove(out_path)
            return wav_bytes
        except Exception as e:
            print(f"STT: WebM to WAV conversion failed: {e}")
            return webm_bytes

    def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """
        Transcribe audio bytes (WAV or WebM).
        
        Tries these FREE services in order:
        1. Google Speech Recognition (speech_recognition library) - FREE, no key needed
        2. Gemini audio transcription - FREE tier with GEMINI_API_KEY
        """
        if "webm" in mime_type:
            audio_bytes = self._convert_webm_to_wav(audio_bytes)
            mime_type = "audio/wav"  # Now it's a standard WAV file

        # Method 0: Sarvam AI STT (REST API — reliable, tested)
        sarvam_key = os.getenv("SARVAM_API_KEY")
        if sarvam_key and "your_" not in sarvam_key:
            try:
                import io as _io
                from sarvamai import SarvamAI

                # Map internal language code to Sarvam BCP-47
                lang_map = {
                    "en": "en-IN", "hi": "hi-IN", "ta": "ta-IN",
                    "ml": "ml-IN", "te": "te-IN", "kn": "kn-IN",
                    "bn": "bn-IN", "gu": "gu-IN", "mr": "mr-IN",
                    "pa": "pa-IN",
                }
                sarvam_lang = lang_map.get(self.language_code, "en-IN")

                client = SarvamAI(api_subscription_key=sarvam_key)

                # Pass as a (filename, fileobj, mimetype) tuple — REST file upload
                ext = "webm" if "webm" in mime_type else "wav"
                response = client.speech_to_text.transcribe(
                    file=(f"audio.{ext}", _io.BytesIO(audio_bytes), mime_type),
                    model="saaras:v3",
                    mode="transcribe",
                    language_code=sarvam_lang,
                )

                transcript = getattr(response, "transcript", "") or ""
                if transcript:
                    print(f"STT (Sarvam REST): {transcript}")
                    return transcript.strip()

            except Exception as e:
                print(f"STT Sarvam REST Error: {e}")

        # Method 1: Google Speech Recognition (speech_recognition library) — completely FREE
        try:
            import speech_recognition as sr
            import io as _io
            
            recognizer = sr.Recognizer()
            audio_file = _io.BytesIO(audio_bytes)
            
            with sr.AudioFile(audio_file) as source:
                audio_data = recognizer.record(source)
            
            # Map language code to Google's format
            lang_map = {
                "en": "en-IN",
                "ta": "ta-IN",
                "ml": "ml-IN",
            }
            google_lang = lang_map.get(self.language_code, "en-IN")
            
            transcript = recognizer.recognize_google(audio_data, language=google_lang)
            print(f"STT (Google Free): {transcript}")
            return transcript
            
        except Exception as e:
            print(f"STT Google Free Error: {e}")
        
        # Method 2: Gemini transcription (free tier)
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and "your_" not in gemini_key:
            try:
                from google import genai
                from google.genai import types
                
                client = genai.Client(api_key=gemini_key)
                
                contents = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text="Transcribe this audio exactly. Output ONLY the transcription text and nothing else."),
                            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                        ],
                    ),
                ]
                
                # Use the correct model name
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=contents
                )
                
                transcript = response.text.strip()
                if ":" in transcript and len(transcript.split(":")[0]) < 20:
                    transcript = transcript.split(":")[-1].strip()
                
                print(f"STT (Gemini): {transcript}")
                return transcript
                
            except Exception as e:
                print(f"STT Gemini Error: {e}")
        
        return ""

    def listen(self) -> str:
        """
        Record audio from the microphone and transcribe it.
        Uses completely FREE speech recognition.
        """
        audio = self._record_audio()

        if len(audio) == 0:
            return ""

        wav_bytes = self._audio_to_wav_bytes(audio)
        return self.transcribe_audio(wav_bytes, mime_type="audio/wav")
