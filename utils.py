import re
import logging
import time

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def escape_markdown(text: str) -> str:
    escape_chars = r"_[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


def split_long_message(text: str, max_len: int = 4000) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts = []
    while len(text) > max_len:
        split_pos = text.rfind("\n", 0, max_len)
        if split_pos == -1:
            split_pos = max_len
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")
    if text:
        parts.append(text)
    return parts


def format_model_name(model_id: str) -> str:
    return model_id.split("/")[-1].replace(":free", "").replace("-", " ").title()


def truncate_text(text: str, max_chars: int = 100) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


class Timer:
    def __init__(self):
        self._start = time.time()

    def elapsed(self) -> float:
        return round(time.time() - self._start, 2)

    def elapsed_str(self) -> str:
        e = self.elapsed()
        if e < 1:
            return f"{int(e*1000)}мс"
        return f"{e:.1f}с"


INTENT_EMOJI = {
    "coding": "💻",
    "reasoning": "🧠",
    "creative": "🎨",
    "chat": "💬",
    "vision": "👁",
}


def thinking_message(intent: str) -> str:
    emoji = INTENT_EMOJI.get(intent, "🤔")
    messages = {
        "coding": f"{emoji} Анализирую задачу, пишу код...",
        "reasoning": f"{emoji} Думаю, анализирую...",
        "creative": f"{emoji} Генерирую идеи...",
        "chat": f"{emoji} Подбираю ответ...",
        "vision": f"{emoji} Анализирую изображение...",
    }
    return messages.get(intent, f"{emoji} Обрабатываю запрос...")
