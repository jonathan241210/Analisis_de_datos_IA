"""
config.py
Configuración centralizada: claves de API, endpoints y catálogo de modelos de IA.
"""
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class AIModel:
    id: str
    label: str
    provider: str
    endpoint: str
    description: str


# --- Claves de API (se leen de variables de entorno / .env) ---
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("LLAMA_API_KEY", "")

# --- Catálogo de modelos disponibles en el selector de la UI ---
AI_MODELS = {
    "nvidia": AIModel(
        id="nvidia/llama-3.3-nemotron-super-49b-v1",
        label="⚡ NVIDIA Nemotron (rápido)",
        provider="nvidia",
        endpoint="https://integrate.api.nvidia.com/v1/chat/completions",
        description=(
            "Modelo ultra-rápido optimizado por NVIDIA para ejecución precisa "
            "de código Python, Pandas y manipulación directa de datos."
        ),
    ),
    "deepseek": AIModel(
        id="meta/llama-3.3-70b-instruct",
        label="🧠llama-3.3-70b-instruct",
        provider="nvidia",
        endpoint="https://integrate.api.nvidia.com/v1/chat/completions",
        description=(
            "Modelo "
        ),
    ),
}

DEFAULT_MODEL_KEY = "nvidia"

# --- Límites de contexto enviado a la IA (Regla de Oro: nunca el dataset completo) ---
N_HEAD_ROWS = 3
N_SAMPLE_ROWS = 3
N_TOP_CATEGORIES = 5
MAX_COLUMNS_IN_METADATA = 60  # si hay más columnas, se resume

# --- Archivos aceptados en la ingesta ---
ALLOWED_EXTENSIONS = ["csv", "xlsx", "xls", "tsv"]

APP_TITLE = "DataLab Copiloto IA"
APP_ICON = "🧪"
