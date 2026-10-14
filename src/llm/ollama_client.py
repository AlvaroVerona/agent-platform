import time

import ollama


class OllamaClient:
    """Thin Ollama wrapper with a per-call timeout, a token cap and usage counters."""

    def __init__(self, model: str = "llama3.1", timeout: float = 240.0, num_predict: int = 2048, temperature: float = 0.0):
        self.model = model
        self.num_predict = num_predict
        self.temperature = temperature
        self._client = ollama.Client(timeout=timeout)
        self.calls = 0
        self.seconds = 0.0

    def generate(self, prompt: str, schema: dict | None = None) -> str:
        """With `schema`, Ollama constrains decoding to that JSON schema (structured outputs)."""
        start = time.time()
        try:
            response = self._client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                format=schema,
                options={"num_predict": self.num_predict, "temperature": self.temperature},
            )
        finally:
            self.calls += 1
            self.seconds += time.time() - start

        return response["message"]["content"]
