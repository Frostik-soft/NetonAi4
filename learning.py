import json
import os
import logging
import math
from datetime import datetime
from config import LEARNING_FILE, SCORE_MIN, SCORE_MAX

logger = logging.getLogger(__name__)

os.makedirs(os.path.dirname(LEARNING_FILE), exist_ok=True)

DEFAULT_LEARNING = {
    "agents": {
        "Brain": {"success": 0, "fail": 0, "score": 1.0, "style_hints": []},
        "Coder": {"success": 0, "fail": 0, "score": 1.0, "style_hints": []},
        "Creator": {"success": 0, "fail": 0, "score": 1.0, "style_hints": []},
        "Analyst": {"success": 0, "fail": 0, "score": 1.0, "style_hints": []},
        "Critic": {"success": 0, "fail": 0, "score": 1.0, "style_hints": []},
    },
    "models": {},
    "intents": {
        "coding": {"success": 0, "total": 0},
        "reasoning": {"success": 0, "total": 0},
        "creative": {"success": 0, "total": 0},
        "chat": {"success": 0, "total": 0},
        "vision": {"success": 0, "total": 0},
    },
    "last_updated": None,
}


def _normalize_score(raw: float) -> float:
    """Clamp score to always stay in [SCORE_MIN, SCORE_MAX] range."""
    return round(max(SCORE_MIN, min(SCORE_MAX, raw)), 4)


def _compute_score(success: int, fail: int, feedback_boost: float = 0.0) -> float:
    """
    Bayesian-style score with feedback boost.
    feedback_boost is added when the score comes from explicit user 👍/👎.
    Result is always within [SCORE_MIN, SCORE_MAX].
    """
    total = success + fail
    if total == 0:
        return _normalize_score(1.0)
    win_rate = success / total
    score = win_rate * (SCORE_MAX - SCORE_MIN) + SCORE_MIN + feedback_boost
    return _normalize_score(score)


def _apply_decay(entry: dict, decay_factor: float = 0.05) -> dict:
    """
    Apply a small decay to models/agents that have a poor track record
    (fail > success) and have accumulated enough data. Prevents them from
    sitting at a mediocre score indefinitely.
    """
    s = entry.get("success", 0)
    f = entry.get("fail", 0)
    total = s + f
    if total >= 10 and f > s:
        current = entry.get("score", 1.0)
        decayed = _normalize_score(current - decay_factor)
        entry["score"] = decayed
    return entry


def _load() -> dict:
    if not os.path.exists(LEARNING_FILE):
        return DEFAULT_LEARNING.copy()
    try:
        with open(LEARNING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for agent in DEFAULT_LEARNING["agents"]:
            if agent not in data.get("agents", {}):
                data.setdefault("agents", {})[agent] = DEFAULT_LEARNING["agents"][agent].copy()
        return data
    except Exception as e:
        logger.error(f"Failed to load learning data: {e}")
        return DEFAULT_LEARNING.copy()


def _save(data: dict):
    try:
        data["last_updated"] = datetime.now().isoformat()
        with open(LEARNING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save learning data: {e}")


def record_result(
    agents_used: list,
    model: str,
    intent: str,
    success: bool,
    from_feedback: bool = False,
):
    """
    Record outcome and update scores.
    from_feedback=True means explicit 👍/👎 — applies 3x weight to the update.
    Scores are always normalized to [SCORE_MIN, SCORE_MAX]. Decay is applied
    to consistently underperforming agents/models.
    """
    data = _load()
    feedback_boost = 0.05 if from_feedback and success else (-0.05 if from_feedback and not success else 0.0)
    weight = 3 if from_feedback else 1

    for agent in agents_used:
        if agent in data.get("agents", {}):
            entry = data["agents"][agent]
            if success:
                entry["success"] += weight
            else:
                entry["fail"] += weight
            entry = _apply_decay(entry)
            entry["score"] = _compute_score(
                entry["success"], entry["fail"], feedback_boost
            )
            data["agents"][agent] = entry

    if model and model != "fallback":
        if model not in data.get("models", {}):
            data.setdefault("models", {})[model] = {
                "success": 0, "fail": 0, "score": 1.0
            }
        entry = data["models"][model]
        if success:
            entry["success"] += weight
        else:
            entry["fail"] += weight
        entry = _apply_decay(entry)
        entry["score"] = _compute_score(
            entry["success"], entry["fail"], feedback_boost
        )
        data["models"][model] = entry

    if intent in data.get("intents", {}):
        data["intents"][intent]["total"] += 1
        if success:
            data["intents"][intent]["success"] += 1

    _save(data)


def record_result_from_feedback(agents_used: list, model: str, intent: str, success: bool):
    """Explicit feedback path: 3x impact on scores."""
    record_result(agents_used, model, intent, success, from_feedback=True)


def get_agent_scores() -> dict:
    data = _load()
    return {a: _normalize_score(d.get("score", 1.0)) for a, d in data.get("agents", {}).items()}


def get_model_score(model: str) -> float:
    data = _load()
    raw = data.get("models", {}).get(model, {}).get("score", 1.0)
    return _normalize_score(raw)


def get_stats_text() -> str:
    data = _load()
    lines = ["📊 *Статистика самообучения*\n"]
    lines.append("*Агенты:*")
    for agent, info in data.get("agents", {}).items():
        s = info.get("success", 0)
        f = info.get("fail", 0)
        score = _normalize_score(info.get("score", 1.0))
        filled = int(score * 10)
        bar = "▓" * filled + "░" * (10 - filled)
        lines.append(f"  {agent}: {bar} {score:.2f} (✅{s} ❌{f})")

    lines.append("\n*Модели:*")
    models = data.get("models", {})
    if models:
        sorted_models = sorted(models.items(), key=lambda x: x[1].get("score", 1.0), reverse=True)
        for model, info in sorted_models[:6]:
            short = model.split("/")[-1][:30]
            score = _normalize_score(info.get("score", 1.0))
            s = info.get("success", 0)
            f = info.get("fail", 0)
            lines.append(f"  {short}: {score:.2f} (✅{s} ❌{f})")
    else:
        lines.append("  Данных пока нет")

    lines.append("\n*Интенты:*")
    for intent, info in data.get("intents", {}).items():
        total = info.get("total", 0)
        success = info.get("success", 0)
        pct = f"{round(success/total*100)}%" if total > 0 else "—"
        lines.append(f"  {intent}: {total} запросов, успех {pct}")

    updated = data.get("last_updated", "никогда")
    if updated and updated != "никогда":
        updated = updated[:19].replace("T", " ")
    lines.append(f"\n_Последнее обновление: {updated}_")
    return "\n".join(lines)
