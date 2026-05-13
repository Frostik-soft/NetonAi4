import re
import logging
from config import FREE_MODELS, AGENT_SYSTEM_PROMPTS, get_models_by_category, get_all_unique_models
from learning import get_agent_scores, get_model_score

logger = logging.getLogger(__name__)

CODING_KEYWORDS = [
    ("напиши код", 3),
    ("напиши функцию", 3),
    ("реализуй", 3),
    ("напиши скрипт", 3),
    ("python", 2),
    ("javascript", 2),
    ("typescript", 2),
    ("c++", 2),
    ("golang", 2),
    ("fastapi", 2),
    ("django", 2),
    ("flask", 2),
    ("react", 2),
    ("sql", 2),
    ("база данных", 2),
    ("алгоритм", 2),
    ("парсинг", 2),
    ("debug", 2),
    ("баг", 2),
    ("ошибк", 1),
    ("код", 1),
    ("программ", 1),
    ("функци", 1),
    ("класс", 1),
    ("метод", 1),
    ("скрипт", 1),
    ("api", 1),
    ("запрос", 1),
    ("html", 1),
    ("css", 1),
    ("js", 1),
    ("ts", 1),
    ("java", 1),
    ("rust", 1),
    ("php", 1),
    ("ruby", 1),
    ("swift", 1),
]

REASONING_KEYWORDS = [
    ("как работает", 3),
    ("докажи", 3),
    ("плюсы и минусы", 3),
    ("разница между", 3),
    ("что лучше", 2),
    ("сравни", 2),
    ("доказательство", 2),
    ("рассуждение", 2),
    ("почему", 2),
    ("объясни", 2),
    ("анализ", 2),
    ("логика", 2),
    ("вывод", 1),
    ("аргумент", 1),
    ("теорема", 1),
    ("математик", 1),
    ("физик", 1),
    ("химия", 1),
    ("концепц", 1),
    ("принцип", 1),
]

CREATIVE_KEYWORDS = [
    ("напиши рассказ", 3),
    ("придумай историю", 3),
    ("придумай название", 3),
    ("придумай слоган", 3),
    ("придума", 2),
    ("сочини", 2),
    ("нарисуй словами", 2),
    ("текст для", 2),
    ("идея", 1),
    ("история", 1),
    ("стих", 1),
    ("поэм", 1),
    ("сценари", 1),
    ("креатив", 1),
    ("фантази", 1),
    ("придумай", 1),
    ("концепт", 1),
    ("слоган", 1),
    ("название", 1),
    ("бренд", 1),
    ("опиши", 1),
]

VISION_KEYWORDS = [
    ("что на фото", 3),
    ("что здесь", 3),
    ("анализ изображени", 3),
    ("фото", 2),
    ("изображени", 2),
    ("картинк", 2),
    ("посмотри", 1),
    ("на снимке", 1),
    ("скриншот", 1),
]

INTENT_KEYWORD_MAP = {
    "coding": CODING_KEYWORDS,
    "reasoning": REASONING_KEYWORDS,
    "creative": CREATIVE_KEYWORDS,
    "vision": VISION_KEYWORDS,
}


def _weighted_score(text_lower: str, keywords: list) -> float:
    """Compute weighted keyword score for text against a keyword list."""
    total = 0.0
    for kw, weight in keywords:
        if kw in text_lower:
            total += weight
    return total


def detect_intents_multi(text: str, has_image: bool = False) -> list:
    """
    Detect all relevant intents with weighted scores.
    Returns list of (intent, score) tuples sorted by score descending.
    Always includes 'chat' with a baseline score of 0.
    """
    if has_image:
        return [("vision", 10.0), ("chat", 0.0)]

    text_lower = text.lower()
    raw_scores = {
        intent: _weighted_score(text_lower, kws)
        for intent, kws in INTENT_KEYWORD_MAP.items()
    }
    raw_scores["chat"] = 0.0

    sorted_intents = sorted(raw_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_intents


def detect_intent(text: str, has_image: bool = False) -> str:
    """
    Detect primary intent. Returns single intent string.
    Backward-compatible with existing callers.
    """
    if has_image:
        return "vision"
    ranked = detect_intents_multi(text, has_image)
    primary_intent, primary_score = ranked[0]
    if primary_score == 0:
        return "chat"
    return primary_intent


def detect_multi_intent(text: str, has_image: bool = False, threshold: float = 2.0) -> list:
    """
    Return list of active intents where score >= threshold.
    Falls back to ['chat'] if none qualify.
    """
    ranked = detect_intents_multi(text, has_image)
    active = [intent for intent, score in ranked if score >= threshold]
    return active if active else ["chat"]


def select_agents(intent: str) -> list:
    agent_scores = get_agent_scores()
    base_agents = {
        "coding": ["Brain", "Coder", "Critic"],
        "reasoning": ["Brain", "Analyst", "Critic"],
        "creative": ["Creator", "Brain", "Critic"],
        "chat": ["Brain", "Critic"],
        "vision": ["Analyst", "Critic"],
    }
    agents = base_agents.get(intent, ["Brain", "Critic"])
    agents_sorted = sorted(
        agents,
        key=lambda a: agent_scores.get(a, 1.0),
        reverse=True,
    )
    return agents_sorted


def select_models(intent: str, preferred_model: str = None) -> list:
    """
    Build ordered model list combining preferred model, learning scores,
    and multi-intent pool expansion.
    """
    primary_pool = get_models_by_category(intent)

    multi_intents = [intent]
    if intent not in ("chat", "vision"):
        all_ranked = detect_intents_multi("", has_image=(intent == "vision"))
    else:
        all_ranked = []

    expanded_pool_set = list(primary_pool)
    seen = set(primary_pool)

    secondary_candidates = get_models_by_category("default")
    for m in secondary_candidates:
        if m not in seen:
            seen.add(m)
            expanded_pool_set.append(m)

    scored_pool = sorted(
        expanded_pool_set,
        key=lambda m: get_model_score(m),
        reverse=True,
    )

    if preferred_model:
        result = [preferred_model] + [m for m in scored_pool if m != preferred_model]
        return result[:5]

    return scored_pool[:5]


def route(text: str, has_image: bool = False, preferred_model: str = None) -> dict:
    intent = detect_intent(text, has_image)
    multi_intents = detect_multi_intent(text, has_image)
    agents = select_agents(intent)
    models = select_models(intent, preferred_model)
    logger.info(
        f"Route: intent={intent}, multi={multi_intents}, "
        f"agents={agents}, models={models[:2]}"
    )
    return {
        "intent": intent,
        "multi_intents": multi_intents,
        "agents": agents,
        "models": models,
    }


INTENT_LABELS = {
    "coding": "💻 Программирование",
    "reasoning": "🧠 Анализ и логика",
    "creative": "🎨 Креатив",
    "chat": "💬 Диалог",
    "vision": "👁 Изображение",
}
