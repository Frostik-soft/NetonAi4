import json
import os
import logging
from datetime import datetime
from config import MEMORY_DIR, MAX_HISTORY

logger = logging.getLogger(__name__)

os.makedirs(MEMORY_DIR, exist_ok=True)


def _user_file(user_id: int) -> str:
    return os.path.join(MEMORY_DIR, f"{user_id}.json")


def load_history(user_id: int) -> list:
    path = _user_file(user_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("history", [])
    except Exception as e:
        logger.error(f"Failed to load history for {user_id}: {e}")
        return []


def save_message(user_id: int, role: str, content: str):
    path = _user_file(user_id)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"history": [], "meta": {}}

        data["history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

        if len(data["history"]) > MAX_HISTORY * 2:
            data["history"] = data["history"][-MAX_HISTORY * 2:]

        data["meta"]["last_active"] = datetime.now().isoformat()
        data["meta"]["message_count"] = data["meta"].get("message_count", 0) + 1

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save message for {user_id}: {e}")


def get_context_messages(user_id: int, system_prompt: str) -> list:
    history = load_history(user_id)
    messages = [{"role": "system", "content": system_prompt}]
    for item in history[-MAX_HISTORY:]:
        role = item.get("role", "user")
        content = item.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    return messages


def clear_history(user_id: int):
    path = _user_file(user_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["history"] = []
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to clear history for {user_id}: {e}")


def get_stats(user_id: int) -> dict:
    path = _user_file(user_id)
    if not os.path.exists(path):
        return {"message_count": 0, "last_active": "никогда"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("meta", {})
        history = data.get("history", [])
        return {
            "message_count": meta.get("message_count", len(history)),
            "last_active": meta.get("last_active", "неизвестно"),
            "history_len": len(history),
        }
    except Exception:
        return {"message_count": 0, "last_active": "ошибка"}
