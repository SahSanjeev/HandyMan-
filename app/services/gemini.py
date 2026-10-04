import json
import re

import httpx

from app.config import settings


class AgentError(RuntimeError):
    pass


def generate_json(system_prompt: str, user_prompt: str) -> dict:
    if not settings.gemini_api_key:
        raise AgentError(
            "Gemini is not configured. Set GEMINI_API_KEY in the project .env file."
        )

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    try:
        response = httpx.post(
            endpoint,
            params={"key": settings.gemini_api_key},
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            },
            timeout=45.0,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise AgentError("Gemini request timed out.") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise AgentError(f"Gemini returned HTTP {exc.response.status_code}: {detail}") from exc
    except httpx.HTTPError as exc:
        raise AgentError(f"Could not reach Gemini: {exc}") from exc

    try:
        payload = response.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
        result = json.loads(text)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AgentError("Gemini returned an invalid JSON response.") from exc
    if not isinstance(result, dict):
        raise AgentError("Gemini returned JSON that is not an object.")
    return result
