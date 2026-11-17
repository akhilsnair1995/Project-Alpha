"""
Project Alpha: Live Background Microphone Listener & Voice Activity Detection (VAD).
Continuously samples audio from the onboard microphone in real time, detects human
speech using dynamic noise floor energy tracking, buffers spoken utterances, transcribes
via speech recognition / Gemini multimodal audio, and triggers autonomous companion
reactions with instant barge-in support.
"""

import io
import wave
import time
import queue
import threading
from typing import Optional, Callable, Dict, Any, List

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    class _MockNP:
        ndarray = Any
    np = _MockNP()
    HAS_NUMPY = False

from core.eye_animator import Emotion

class LiveMicrophoneListener:
    """
    Continuous background microphone listener for Project Alpha.
    Features:
    - Real-time RMS Voice Activity Detection (VAD) with adaptive noise floor.
    - Voice barge-in: interrupts Alpha's ongoing speech if user starts talking.
    - Dual transcription: Google Speech Recognition with cloud Gemini audio fallback.
    - Zero-latency eye reaction: eyes turn to ANALYZING/CURIOUS the moment user starts speaking.
    - Graceful fallback to standby mode if hardware microphone is unavailable.
    """

    SAMPLE_RATE = 16000
    BLOCK_SIZE = 1024  # ~64ms audio chunk per callback
    MIN_SPEECH_DURATION = 0.45  # Ignore transient pops, mouth clicks < 0.45s
    MAX_SPEECH_DURATION = 18.0  # Cap individual utterances at 18s
    SILENCE_TIMEOUT = 0.85      # End of sentence silence gap (850ms)

    def __init__(
        self,
        voice_engine: Optional[Any] = None,
        brain: Optional[Any] = None,
        eyes: Optional[Any] = None,
        motion: Optional[Any] = None,
        db: Optional[Any] = None,
        on_speech_detected: Optional[Callable[[], None]] = None,
        on_transcription: Optional[Callable[[str], None]] = None,
        device_index: Optional[int] = None
    ):
        self.voice_engine = voice_engine
        self.brain = brain
        self.eyes = eyes
        self.motion = motion
        self.db = db
        self.device_index = device_index

        self.on_speech_detected = on_speech_detected
        self.on_transcription = on_transcription

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stream = None
        self.is_active = False

        # VAD & Energy State
        self.ambient_energy = 80.0
        self.is_user_speaking = False
        self.speech_start_time = 0.0
        self.silence_start_time = 0.0
        self.audio_buffer: List[np.ndarray] = []
        self._lock = threading.Lock()

        # Queue for async transcription tasks
        self._transcribe_queue: queue.Queue = queue.Queue()
        self._transcribe_worker: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Starts the live microphone streaming loop in a background thread."""
        if self._running:
            return True

        self._running = True
        self._transcribe_worker = threading.Thread(target=self._process_transcriptions, daemon=True)
        self._transcribe_worker.start()

        self._thread = threading.Thread(target=self._run_audio_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Stops the microphone listener and cleans up audio streams."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self.is_active = False

    def _run_audio_loop(self) -> None:
        """Audio streaming thread using sounddevice."""
        try:
            import sounddevice as sd
        except ImportError:
            print("[LiveListener] sounddevice not available. Listener in standby mode.")
            return

        def _audio_callback(indata, frames, time_info, status):
            if not self._running:
                return
            self._process_audio_chunk(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype='int16',
                blocksize=self.BLOCK_SIZE,
                device=self.device_index,
                callback=_audio_callback
            )
            self._stream.start()
            self.is_active = True
            print("[LiveListener] Active! Live microphone ears open & listening for user voice.")
            while self._running:
                time.sleep(0.1)
        except Exception as e:
            print(f"[LiveListener] Microphone initialization notice: {e}. Standby mode active.")
            self.is_active = False

    def _process_audio_chunk(self, chunk: np.ndarray) -> None:
        """Processes incoming 64ms audio chunk for Voice Activity Detection."""
        samples = chunk.flatten()
        if len(samples) == 0:
            return

        # Compute Root Mean Square (RMS) energy
        rms = float(np.sqrt(np.mean(samples.astype(np.float64)**2)))
        now = time.time()

        # 1. Echo Suppression / Barge-in check:
        # If Alpha is actively speaking through speaker:
        if self.voice_engine and getattr(self.voice_engine, "is_speaking", False):
            # If user voice is significantly louder than speaker output (barge-in):
            if rms > max(350.0, self.ambient_energy * 4.0):
                print("[LiveListener] User voice barge-in detected! Interrupting Alpha speech.")
                if hasattr(self.voice_engine, "stop_speaking"):
                    self.voice_engine.stop_speaking()
                if self.eyes:
                    self.eyes.set_emotion(Emotion.SURPRISED)
            else:
                # Don't transcribe Alpha's own speaker sound
                return

        # 2. Dynamic threshold calculation
        speech_threshold = max(110.0, self.ambient_energy * 2.6)

        if not self.is_user_speaking:
            # Update ambient noise moving average
            self.ambient_energy = 0.96 * self.ambient_energy + 0.04 * rms

            if rms > speech_threshold:
                # Speech onset detected!
                self.is_user_speaking = True
                self.speech_start_time = now
                self.silence_start_time = 0.0
                self.audio_buffer = [samples]

                # Visual feedback: Alpha perks up and pays close attention
                if self.eyes:
                    self.eyes.set_emotion(Emotion.ANALYZING)
                if self.on_speech_detected:
                    try:
                        self.on_speech_detected()
                    except Exception:
                        pass
        else:
            # Currently buffering speech
            self.audio_buffer.append(samples)
            speech_dur = now - self.speech_start_time

            # Check if volume dropped below threshold (silence gap)
            if rms < speech_threshold:
                if self.silence_start_time == 0.0:
                    self.silence_start_time = now
                elif now - self.silence_start_time >= self.SILENCE_TIMEOUT:
                    # User finished speaking!
                    self._finalize_speech_segment()
            else:
                # Still talking
                self.silence_start_time = 0.0

            # Force cutoff if user spoke continuously longer than MAX_SPEECH_DURATION
            if speech_dur >= self.MAX_SPEECH_DURATION:
                self._finalize_speech_segment()

    def _finalize_speech_segment(self) -> None:
        """Converts collected audio chunks into WAV and enqueues for transcription."""
        self.is_user_speaking = False
        duration = len(self.audio_buffer) * self.BLOCK_SIZE / self.SAMPLE_RATE

        if duration < self.MIN_SPEECH_DURATION or not self.audio_buffer:
            self.audio_buffer = []
            return

        combined_samples = np.concatenate(self.audio_buffer).astype(np.int16)
        self.audio_buffer = []

        # Package as standard 16-bit PCM WAV
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(combined_samples.tobytes())
        wav_bytes = wav_buffer.getvalue()

        self._transcribe_queue.put(wav_bytes)

    def _process_transcriptions(self) -> None:
        """Background worker consuming finalized WAV audio and transcribing."""
        while self._running:
            try:
                wav_bytes = self._transcribe_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            transcript = self.transcribe_audio_bytes(wav_bytes)
            if transcript and transcript.strip():
                clean_transcript = transcript.strip()
                print(f"[LiveListener] Transcribed Voice: \"{clean_transcript}\"")

                # Dispatch callback
                if self.on_transcription:
                    try:
                        self.on_transcription(clean_transcript)
                    except Exception as e:
                        print(f"[LiveListener] Transcription callback notice: {e}")

                # If connected to Alpha's Brain and Voice, respond naturally!
                self._respond_to_voice(clean_transcript)

    def transcribe_audio_bytes(self, wav_bytes: bytes) -> str:
        """Transcribes PCM WAV audio using Google Speech Recognition or Gemini Audio."""
        if not wav_bytes:
            return ""

        # Method 1: Google Speech Recognition (free, sub-second latency)
        try:
            import speech_recognition as sr
            r_stt = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                audio_data = r_stt.record(source)
            text = r_stt.recognize_google(audio_data)
            if text and text.strip():
                return text.strip()
        except Exception:
            pass

        # Method 2: Cloud Gemini 2.5 Multimodal Audio Fallback
        if self.brain and hasattr(self.brain, "is_online") and self.brain.is_online():
            try:
                from google.genai import types
                prompt = (
                    "Transcribe the user's spoken voice command or question accurately. "
                    "Return ONLY the exact spoken text without commentary or formatting."
                )
                resp = self.brain.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        prompt,
                        types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav")
                    ]
                )
                if resp.text:
                    return resp.text.strip().replace('"', '')
            except Exception as e:
                print(f"[LiveListener] Gemini audio transcription notice: {e}")

        return ""

    def _respond_to_voice(self, user_text: str) -> None:
        """Handles spoken input: queries brain, plays emotive chimes, sets eyes, and speaks naturally."""
        if not self.brain or not self.voice_engine:
            return

        # Alpha processes through conversational memory & dynamic tool cortex
        chat_res = self.brain.chat_with_emotion(user_text)
        reply = chat_res.get("reply", "")
        emo = chat_res.get("emotion", Emotion.HAPPY)

        # Update Dual Eyes and physical posture
        if self.eyes:
            self.eyes.set_emotion(emo)
        if self.motion and hasattr(self.motion, "express_emotion"):
            self.motion.express_emotion(emo)

        # Natural Speech Output (clean, emotive, Wall-E chirp)
        if self.voice_engine and self.voice_engine.voice_enabled:
            print(f"Alpha [{emo.value.upper()}] > {reply}")
            self.voice_engine.speak(reply, emotion=emo, with_chirp=True, async_speech=True)
