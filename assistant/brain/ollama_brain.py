"""Local brain backed by Ollama — unlimited, offline, free.

Talks to a local Ollama server over its HTTP API (no API key, no internet, no
quotas). Uses the *same* skill registry and the *same* system prompt as the
Gemini brain, so behaviour is consistent and nothing else in the project
changes.

Requires:
    * Ollama installed and running  (the desktop app, or `ollama serve`)
    * A tool-calling model pulled, e.g. `ollama pull qwen2.5:7b`

Only the standard library is used for the HTTP calls, so this adds no
dependencies.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import config
from assistant import registry
from assistant.brain.base import Brain
from assistant.brain.gemini_brain import build_system_instruction


class OllamaUnavailable(RuntimeError):
    """Raised when the local Ollama server can't be reached."""


def _tool_schemas() -> list[dict]:
    """The skills as OpenAI/Ollama-style tool schemas (JSON Schema is native)."""
    return [
        {
            "type": "function",
            "function": {
                "name": sk.name,
                "description": sk.description,
                "parameters": sk.parameters,
            },
        }
        for sk in registry.all_skills()
    ]


class OllamaBrain(Brain):
    def __init__(self) -> None:
        self._host = config.OLLAMA_HOST.rstrip("/")
        self._model = config.OLLAMA_MODEL
        self._messages: list[dict] = [
            {"role": "system", "content": build_system_instruction()}
        ]
        # Fail early with a helpful message rather than on the first request.
        self._check_server()

    def _check_server(self) -> None:
        try:
            with urllib.request.urlopen(f"{self._host}/api/version", timeout=5):
                return
        except Exception as exc:  # noqa: BLE001
            raise OllamaUnavailable(
                f"Couldn't reach Ollama at {self._host} ({exc}).\n"
                "  1. Install/start Ollama: https://ollama.com/download\n"
                "  2. Pull a model:  ollama pull qwen2.5:7b\n"
                "  3. Or use the cloud brain:  set BRAIN=gemini in .env"
            ) from exc

    def _chat(self, timeout: int = 180) -> dict:
        payload = {
            "model": self._model,
            "messages": self._messages,
            "tools": _tool_schemas(),
            "stream": False,
            "options": {"temperature": config.OLLAMA_TEMPERATURE},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._host}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(
                f"Ollama returned HTTP {exc.code}: {body}\n"
                f"(Is the model '{self._model}' pulled? Try: ollama pull {self._model})"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise OllamaUnavailable(
                f"Error talking to Ollama at {self._host}: {exc}"
            ) from exc

    def reset(self) -> None:
        self._messages = [
            {"role": "system", "content": build_system_instruction()}
        ]

    def ask(self, user_text: str) -> str:
        self._messages.append({"role": "user", "content": user_text})

        for _ in range(config.MAX_STEPS):
            try:
                response = self._chat()
            except (OllamaUnavailable, RuntimeError) as exc:
                return f"(Local model request failed: {exc})"

            message = response.get("message") or {}
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                # Final natural-language answer.
                self._messages.append(
                    {"role": "assistant", "content": message.get("content", "")}
                )
                return (message.get("content") or "").strip() or "(Done.)"

            # Record the assistant's tool-call turn, then run each skill.
            self._messages.append(message)
            for call in tool_calls:
                fn = call.get("function") or {}
                name = fn.get("name", "")
                raw_args = fn.get("arguments") or {}
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = dict(raw_args)

                result = registry.execute_skill(name, args)
                self._messages.append(
                    {
                        "role": "tool",
                        "name": name,
                        "content": json.dumps(result, default=str),
                    }
                )

        return (
            "(Stopped after reaching the maximum number of steps. "
            "The task may be only partly done.)"
        )
