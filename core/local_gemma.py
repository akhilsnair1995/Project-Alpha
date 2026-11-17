"""
Project Alpha: Local Gemma Engine (Offline Auxiliary Brain).
Runs quantized Gemma 2 2B GGUF models directly on the Raspberry Pi 5 CPU
via llama-cpp-python or local llama.cpp HTTP server with zero cloud dependency.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

from core.config import LOCAL_GEMMA_GGUF_PATH, DATA_DIR

class LocalGemmaEngine:
    """Manages offline local inference with quantized Gemma 2B GGUF models."""

    def __init__(self, model_path: Optional[str] = None, n_threads: int = 4):
        self.model_path = model_path or LOCAL_GEMMA_GGUF_PATH
        self.n_threads = n_threads
        self.llm = None
        self.is_loaded = False

        self._try_load_model()

    def _try_load_model(self) -> None:
        """Attempts to load the GGUF model if llama_cpp is installed and model file exists."""
        if not os.path.exists(self.model_path):
            # Model file not yet downloaded to data/models/
            return

        try:
            import llama_cpp
            print(f"[LocalGemma] Loading GGUF model: {self.model_path} ({self.n_threads} CPU threads)...")
            self.llm = llama_cpp.Llama(
                model_path=self.model_path,
                n_threads=self.n_threads,
                n_ctx=2048,           # 2K context window
                n_batch=512,
                verbose=False
            )
            self.is_loaded = True
            print("[LocalGemma] Model loaded successfully into RAM. Offline brain active!")
        except ImportError:
            print("[LocalGemma] 'llama-cpp-python' not installed. Install via: pip install llama-cpp-python")
        except Exception as e:
            print(f"[LocalGemma] Error loading GGUF model: {e}")

    def is_available(self) -> bool:
        """Checks if local Gemma is ready to infer."""
        return self.is_loaded and self.llm is not None

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        max_tokens: int = 150,
        temperature: float = 0.7
    ) -> str:
        """
        Executes local Gemma inference.
        Uses Gemma's standard instruction formatting:
        <start_of_turn>user\n...<end_of_turn>\n<start_of_turn>model\n...
        """
        if not self.is_available():
            return self._fallback_stub_response(prompt)

        try:
            # Gemma 2 chat formatting
            formatted_prompt = (
                f"<start_of_turn>user\n"
                f"{system_instruction}\n\n"
                f"{prompt}<end_of_turn>\n"
                f"<start_of_turn>model\n"
            )

            output = self.llm(
                formatted_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["<end_of_turn>", "\n\nUser:"],
                echo=False
            )

            response_text = output["choices"][0]["text"].strip()
            return response_text
        except Exception as e:
            print(f"[LocalGemma] Inference error: {e}")
            return self._fallback_stub_response(prompt)

    def _fallback_stub_response(self, prompt: str) -> str:
        """
        Lightweight rule-based fallback if GGUF model has not yet been downloaded to disk.
        """
        # If wrapped in system prompt, isolate the user's latest query
        p = prompt.lower()
        if "akhil says:" in p:
            user_part = p.split("akhil says:", 1)[1]
            if "alpha's spoken response:" in user_part:
                user_part = user_part.split("alpha's spoken response:", 1)[0]
            p = user_part.strip()

        if "hello" in p or "hi" in p:
            return "Beep-boop! Hello Akhil! I am running on my local offline auxiliary core."
        elif "battery" in p or "charge" in p:
            return "Battery cells are holding steady at 7.4V. Systems operational."
        elif "where" in p:
            return "Checking my local spatial logs... I'll scan the area as I continue roaming."
        else:
            return "Satellite link is offline, but I've processed your message locally into memory!"
