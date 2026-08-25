"""
modules/ai_copilot/client.py
Cliente unificado para invocar los endpoints de NVIDIA NIM API y DeepSeek.
Ambos exponen una API compatible con el formato "chat/completions" de OpenAI.
"""
import requests

from config import AI_MODELS, NVIDIA_API_KEY, DEEPSEEK_API_KEY
from modules.ai_copilot.prompts import SYSTEM_PROMPT


class AIClientError(Exception):
    pass


def _api_key_for(provider: str) -> str:
    return NVIDIA_API_KEY if provider == "nvidia" else DEEPSEEK_API_KEY


def call_ai_model(model_key: str, chat_history: list[dict], user_message: str, timeout: int = 60) -> str:
    """
    Llama al modelo seleccionado (NVIDIA Nemotron o DeepSeek-R1).

    chat_history: lista de mensajes previos [{"role": "user"/"assistant", "content": "..."}]
    user_message: el mensaje del usuario ya combinado con el contexto adaptativo del dataset.
    """
    model = AI_MODELS[model_key]
    api_key = _api_key_for(model.provider)

    if not api_key:
        raise AIClientError(
            f"Falta la clave de API para {model.provider.upper()}. "
            f"Configúrala como variable de entorno antes de usar este modelo."
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Solo se reenvía el texto del historial (no metadata pesada) para optimizar tokens.
    for msg in chat_history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model.id,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 4096,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(model.endpoint, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        raise AIClientError("El modelo tardó demasiado en responder. Intenta de nuevo.")
    except requests.exceptions.HTTPError as e:
        raise AIClientError(f"Error HTTP {response.status_code} al llamar a {model.provider}: {e}")
    except (KeyError, IndexError):
        raise AIClientError("Respuesta inesperada de la API del modelo.")
    except requests.exceptions.RequestException as e:
        raise AIClientError(f"Error de conexión con {model.provider}: {e}")
