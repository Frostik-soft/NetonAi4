import json
import os
import logging
from datetime import datetime
from config import PROFILES_DIR, MODEL_INFO

logger = logging.getLogger(__name__)

os.makedirs(PROFILES_DIR, exist_ok=True)


def _profile_file(user_id: int) -> str:
    return os.path.join(PROFILES_DIR, f"{user_id}.json")


def _default_profile(user_id: int, name: str = "Пользователь") -> dict:
    return {
        "user_id": user_id,
        "name": name,
        "style": "дружелюбный",
        "level": "средний",
        "interests": [],
        "preferred_model": None,
        "last_used_model": None,
        "last_used_model_at": None,
        "netonai_mode": True,
        "total_requests": 0,
        "successful_requests": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def load_profile(user_id: int, name: str = "Пользователь") -> dict:
    path = _profile_file(user_id)
    if not os.path.exists(path):
        profile = _default_profile(user_id, name)
        save_profile(user_id, profile)
        return profile
    try:
        data = json.load(open(path, "r", encoding="utf-8"))
        if "last_used_model" not in data:
            data["last_used_model"] = None
        if "last_used_model_at" not in data:
            data["last_used_model_at"] = None
        return data
    except Exception as e:
        logger.error(f"Failed to load profile {user_id}: {e}")
        return _default_profile(user_id, name)


def save_profile(user_id: int, profile: dict):
    path = _profile_file(user_id)
    try:
        profile["updated_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save profile {user_id}: {e}")


def update_style(user_id: int, style: str):
    profile = load_profile(user_id)
    profile["style"] = style
    save_profile(user_id, profile)


def update_level(user_id: int, level: str):
    profile = load_profile(user_id)
    profile["level"] = level
    save_profile(user_id, profile)


def set_preferred_model(user_id: int, model: str):
    profile = load_profile(user_id)
    profile["preferred_model"] = model
    save_profile(user_id, profile)


def set_last_used_model(user_id: int, model: str):
    """Track the last model that actually responded. Updated after every successful response."""
    if not model or model == "fallback":
        return
    profile = load_profile(user_id)
    profile["last_used_model"] = model
    profile["last_used_model_at"] = datetime.now().isoformat()
    save_profile(user_id, profile)


def get_active_model_display(profile: dict) -> str:
    """
    Return a human-readable string describing the currently active model.
    Shows: preferred model if set, otherwise last-used model, otherwise 'Авто'.
    """
    preferred = profile.get("preferred_model")
    last_used = profile.get("last_used_model")

    if preferred:
        name = MODEL_INFO.get(preferred, {}).get("name", preferred)
        return f"📌 {name} (закреплена)"

    if last_used:
        name = MODEL_INFO.get(last_used, {}).get("name", last_used)
        last_at = profile.get("last_used_model_at", "")
        short_date = last_at[:10] if last_at else ""
        suffix = f" · {short_date}" if short_date else ""
        return f"🔄 {name}{suffix} (последняя)"

    return "⚙️ Авто (выбор по задаче)"


def add_interest(user_id: int, interest: str):
    profile = load_profile(user_id)
    interests = profile.get("interests", [])
    if interest not in interests:
        interests.append(interest)
        if len(interests) > 10:
            interests = interests[-10:]
        profile["interests"] = interests
    save_profile(user_id, profile)


def increment_requests(user_id: int, success: bool = True):
    profile = load_profile(user_id)
    profile["total_requests"] = profile.get("total_requests", 0) + 1
    if success:
        profile["successful_requests"] = profile.get("successful_requests", 0) + 1
    save_profile(user_id, profile)


def get_system_prompt_for_user(profile: dict) -> str:
    style = profile.get("style", "дружелюбный")
    level = profile.get("level", "средний")
    interests = profile.get("interests", [])

    style_desc = {
        "дружелюбный": "общайся тепло, по-дружески, с умеренными эмодзи",
        "строгий": "будь краток, чёток, без лишних слов и эмодзи",
        "объясняющий": "объясняй подробно, с примерами, терпеливо",
    }.get(style, "общайся естественно")

    level_desc = {
        "новичок": "используй простые слова, избегай сложных терминов",
        "средний": "объясняй понятно, можно использовать термины с пояснением",
        "эксперт": "можно использовать технические термины без пояснений",
    }.get(level, "адаптируйся под пользователя")

    interests_str = (
        f"Интересы пользователя: {', '.join(interests)}. " if interests else ""
    )

    return (
        f"Ты — NetonAI, умный AI-ассистент. Отвечай ТОЛЬКО на русском языке. "
        f"Стиль общения: {style_desc}. Уровень: {level_desc}. "
        f"{interests_str}"
        f"Ты многофункциональный ассистент: помогаешь с кодом, идеями, вопросами, анализом. "
        f"Никогда не переходи на другой язык кроме русского."
    )
