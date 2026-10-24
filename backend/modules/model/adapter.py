import json
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional
from backend.core.config import settings

class ModelAdapterError(Exception):
    """Custom exception raised when model inference fails."""
    pass

class BaseModelAdapter(ABC):
    """Abstract Interface for Model Adapters (Ollama, llama.cpp, vLLM, Mock)."""

    @abstractmethod
    async def generate_response(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
        pass

    @abstractmethod
    async def stream_response(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        pass

class OllamaAdapter(BaseModelAdapter):
    """Concrete adapter connecting to local Ollama inference service."""

    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, default_model: str = settings.PRIMARY_MODEL):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def check_health(self) -> Dict[str, Any]:
        """Check if Ollama service is reachable and list available local models."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    return {
                        "online": True,
                        "available_models": models,
                        "primary_model_loaded": any(self.default_model in m for m in models)
                    }
                return {"online": False, "error": f"Ollama HTTP {res.status_code}"}
        except Exception as e:
            return {"online": False, "error": str(e)}

    async def generate_response(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
        """Send chat messages and return full assistant response text."""
        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.base_url}/api/chat", json=payload)
                if res.status_code != 200:
                    raise ModelAdapterError(f"Ollama error {res.status_code}: {res.text}")
                data = res.json()
                return data.get("message", {}).get("content", "")
        except httpx.ConnectError:
            raise ModelAdapterError(f"Cannot connect to Ollama at {self.base_url}. Please ensure 'ollama serve' is running.")
        except Exception as e:
            raise ModelAdapterError(f"Ollama inference error: {str(e)}")

    async def stream_response(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream token chunks from Ollama response via async generator."""
        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": True
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    if response.status_code != 200:
                        raise ModelAdapterError(f"Ollama stream error {response.status_code}")
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError:
            raise ModelAdapterError(f"Cannot connect to Ollama at {self.base_url}.")

class MockAdapter(BaseModelAdapter):
    """Deterministic mock adapter for unit tests and offline testing."""

    async def generate_response(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
        last_msg = messages[-1]["content"] if messages else ""
        return f"[MOCK ASSISTANT RESPONSE] Processed prompt: '{last_msg}'"

    async def stream_response(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> AsyncGenerator[str, None]:
        response = await self.generate_response(messages, model)
        for word in response.split():
            yield word + " "

    async def check_health(self) -> Dict[str, Any]:
        return {"online": True, "available_models": ["mock-model"], "primary_model_loaded": True}
