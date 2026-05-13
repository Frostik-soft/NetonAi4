import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

FREE_MODELS = {
    "coding": [
        "qwen/qwen3-coder:free",
        "openai/gpt-oss-120b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
    ],
    "reasoning": [
        "arcee-ai/trinity-large-thinking:free",
        "openai/gpt-oss-120b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
    ],
    "creative": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "openai/gpt-oss-120b:free",
        "google/gemma-4-31b-it:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
    ],
    "chat": [
        "openai/gpt-oss-20b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-4-26b-a4b-it:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
    ],
    "vision": [
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "openai/gpt-oss-120b:free",
        "google/gemma-4-31b-it:free",
    ],
    "default": [
        "openai/gpt-oss-20b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-4-26b-a4b-it:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
    ],
}

MODEL_INFO = {
    "qwen/qwen3-coder:free": {
        "name": "Qwen3 Coder",
        "type": "💻 Кодовая",
        "description": "Специализированная модель для написания и анализа кода",
    },
    "openai/gpt-oss-120b:free": {
        "name": "GPT OSS 120B",
        "type": "🧠 Текстовая",
        "description": "Мощная открытая модель от OpenAI, 120 миллиардов параметров",
    },
    "openai/gpt-oss-20b:free": {
        "name": "GPT OSS 20B",
        "type": "💬 Чат",
        "description": "Быстрая открытая модель от OpenAI для диалога",
    },
    "meta-llama/llama-3.3-70b-instruct:free": {
        "name": "Llama 3.3 70B",
        "type": "🧠 Текстовая",
        "description": "Универсальная модель высокого качества от Meta",
    },
    "nousresearch/hermes-3-llama-3.1-405b:free": {
        "name": "Hermes 3 Llama 405B",
        "type": "🧠 Текстовая",
        "description": "Гигантская модель 405B для сложных многоступенчатых задач",
    },
    "arcee-ai/trinity-large-thinking:free": {
        "name": "Trinity Large Thinking",
        "type": "🧠 Рассуждения",
        "description": "Модель с цепочкой рассуждений для сложной логики и анализа",
    },
    "nvidia/nemotron-3-super-120b-a12b:free": {
        "name": "Nemotron Super 120B",
        "type": "🧠 Рассуждения",
        "description": "Сверхмощная модель от NVIDIA для аналитических задач",
    },
    "google/gemma-4-31b-it:free": {
        "name": "Gemma 4 31B",
        "type": "🧠 Текстовая",
        "description": "Новейшая модель четвёртого поколения от Google",
    },
    "google/gemma-4-26b-a4b-it:free": {
        "name": "Gemma 4 26B (MoE)",
        "type": "💬 Чат",
        "description": "Эффективная смесь экспертов от Google для быстрого диалога",
    },
    "nvidia/nemotron-nano-12b-v2-vl:free": {
        "name": "Nemotron Nano 12B Vision",
        "type": "👁 Изображения",
        "description": "Мультимодальная модель NVIDIA для работы с изображениями",
    },
    "liquid/lfm-2.5-1.2b-instruct:free": {
        "name": "LFM 2.5 1.2B",
        "type": "💬 Чат",
        "description": "Сверхбыстрая лёгкая модель для простых вопросов",
    },
    "meta-llama/llama-3.2-3b-instruct:free": {
        "name": "Llama 3.2 3B",
        "type": "💬 Чат",
        "description": "Компактная и быстрая модель от Meta",
    },
}

CATEGORY_DISPLAY = {
    "coding":    ("💻", "Кодовые модели"),
    "reasoning": ("🧠", "Рассуждения"),
    "creative":  ("🎨", "Творческие"),
    "chat":      ("💬", "Чат"),
    "vision":    ("👁", "Изображения"),
}


def register_model(
    model_id: str,
    name: str,
    type_: str,
    description: str,
    categories: list,
) -> None:
    """
    Register a new model into MODEL_INFO and optionally into FREE_MODELS categories.

    Usage:
        register_model(
            model_id="vendor/model-name:free",
            name="Display Name",
            type_="💬 Чат",
            description="What this model does",
            categories=["chat", "default"],
        )
    """
    MODEL_INFO[model_id] = {
        "name": name,
        "type": type_,
        "description": description,
    }
    for cat in categories:
        if cat in FREE_MODELS and model_id not in FREE_MODELS[cat]:
            FREE_MODELS[cat].append(model_id)


def get_models_by_category(category: str) -> list:
    """Return deduplicated model list for a given FREE_MODELS category."""
    seen = set()
    result = []
    for m in FREE_MODELS.get(category, FREE_MODELS.get("default", [])):
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def get_all_unique_models() -> list:
    """Return all unique models across all non-default categories, preserving insertion order."""
    seen = set()
    result = []
    for cat, models in FREE_MODELS.items():
        if cat == "default":
            continue
        for m in models:
            if m not in seen:
                seen.add(m)
                result.append(m)
    return result


def get_catalog_categories() -> list:
    """Return list of (key, emoji, label) for all non-default FREE_MODELS categories."""
    return [
        (key, *CATEGORY_DISPLAY.get(key, ("🤖", key.capitalize())))
        for key in FREE_MODELS
        if key != "default"
    ]


AGENT_SYSTEM_PROMPTS = {
    "Brain": (
        "Ты — агент Brain, специалист по стратегическому планированию и логике. "
        "Твоя задача: декомпозировать задачу, выстроить чёткий план решения, "
        "обеспечить структуру и логичность ответа. Отвечай строго на русском языке. "
        "Будь точен, аналитичен и структурирован."
    ),
    "Coder": (
        "Ты — агент Coder, эксперт в программировании. "
        "Ты пишешь чистый, рабочий, хорошо прокомментированный код. "
        "Объясняй решения кратко и понятно. Отвечай на русском языке. "
        "Код оформляй в блоках ```."
    ),
    "Creator": (
        "Ты — агент Creator, мастер креативного мышления и генерации идей. "
        "Предлагай оригинальные, нестандартные решения. Думай шире. "
        "Отвечай на русском языке с вдохновением и энтузиазмом."
    ),
    "Analyst": (
        "Ты — агент Analyst, специалист по анализу и объяснению. "
        "Разбирай сложное на простые части, структурируй информацию. "
        "Отвечай на русском языке чётко и понятно для любого уровня."
    ),
    "Critic": (
        "Ты — агент Critic, финальный редактор и улучшатель. "
        "Тебе дан вопрос пользователя и черновой ответ. "
        "Улучши ответ: исправь ошибки, сделай его чётче, убери лишнее, "
        "адаптируй под пользователя. Верни только финальный улучшенный ответ на русском языке."
    ),
}

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
PROFILES_DIR = os.path.join(MEMORY_DIR, "profiles")
LEARNING_FILE = os.path.join(MEMORY_DIR, "agent_learning.json")

MAX_HISTORY = 20
MAX_TOKENS = 1500
REQUEST_TIMEOUT = 45
MAX_RETRIES = 3
SCORE_MIN = 0.2
SCORE_MAX = 1.0
ULTIMATE_FALLBACK_TEXT = (
    "⚠️ Все AI-модели временно недоступны. "
    "Попробуйте через несколько минут или измените ваш запрос."
)
