# llm_clients.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dotenv import load_dotenv
import os
import requests
from typing import List, Optional

import openai


class ChatClient(ABC):
    @abstractmethod
    def chat(self, prompt: str, *, temperature: float = 0.0, timeout: int = 240) -> str: ...


class OllamaChatClient(ChatClient):
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base = base_url.rstrip("/")

    def chat(self, prompt: str, *, temperature: float = 0.0, timeout: int = 240) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature},
        }
        r = requests.post(f"{self.base}/api/chat", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "") or ""


class CBorgChatClient(ChatClient):
    """
    OpenAI-compatible client for CBORG (https://api.cborg.lbl.gov).
    Works with models like:
      - "google/gemini-flash", "google/gemini-pro"
      - "lbl/cborg-chat:latest", "lbl/cborg-vision:latest"
      - "openai/gpt-4o", "anthropic/claude-sonnet", etc. (as exposed by CBORG)
    Env:
      CBORG_API_KEY=...
      CBORG_BASE_URL=https://api.cborg.lbl.gov
    """
    def __init__(self,
                 model: str,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: float = 240):
        self.model = model
        self.client = openai.OpenAI(
            api_key=api_key or os.environ.get("CBORG_API_KEY"),
            base_url=(base_url or os.environ.get("CBORG_BASE_URL") or "https://api.cborg.lbl.gov").rstrip("/"),
            # If you need different per-call timeouts, you can also use client.with_options(timeout=...)
        )
        self.timeout = timeout

    def chat(self, prompt: str, *, temperature: float = 0.0, timeout: int = 240) -> str:
        # Mirrors CBORG sample: client.chat.completions.create(...)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            # tools / response_format / max_tokens can be added here if needed
            timeout=timeout or self.timeout,  # requires openai>=1.40
        )
        return resp.choices[-1].message.content or ""


if __name__ == "__main__":
    # load from env
    load_dotenv()
    client = CBorgChatClient(
        model="google/gemini-flash",
        base_url=os.getenv("CBORG_BASE_URL", "https://api.cborg.lbl.gov"),
        api_key=os.getenv("CBORG_API_KEY", "your_api_key_here")
    )

    response = client.chat("Explain the significance of the Higgs boson.")
    print("Response:", response)
