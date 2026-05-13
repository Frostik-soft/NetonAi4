import logging
from openrouter import call_with_fallback
from config import AGENT_SYSTEM_PROMPTS, MAX_TOKENS

logger = logging.getLogger(__name__)


async def run_agent(
    agent_name: str,
    user_message: str,
    context_messages: list,
    models: list,
    temperature: float = 0.7,
) -> tuple[str | None, str | None]:
    system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_name, "Ты полезный ассистент. Отвечай на русском.")
    messages = [{"role": "system", "content": system_prompt}]
    for msg in context_messages:
        if msg["role"] != "system":
            messages.append(msg)
    if not any(m["content"] == user_message for m in messages if m["role"] == "user"):
        messages.append({"role": "user", "content": user_message})

    result, model_used = await call_with_fallback(messages, models, MAX_TOKENS, temperature)
    return result, model_used


async def run_critic(
    user_message: str,
    draft_answer: str,
    models: list,
    user_context: str = "",
) -> str | None:
    system_prompt = AGENT_SYSTEM_PROMPTS["Critic"]
    critic_input = (
        f"Вопрос пользователя: {user_message}\n\n"
        f"Черновой ответ:\n{draft_answer}\n\n"
        f"{f'Контекст пользователя: {user_context}' if user_context else ''}\n\n"
        f"Верни только финальный улучшенный ответ:"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": critic_input},
    ]
    result, _ = await call_with_fallback(messages, models, MAX_TOKENS, 0.5)
    return result


async def multi_agent_process(
    user_message: str,
    context_messages: list,
    agents: list,
    models: list,
    profile: dict,
) -> tuple[str, list, str | None]:
    primary_agents = [a for a in agents if a != "Critic"]
    critic_in_list = "Critic" in agents

    draft = None
    model_used = None
    agents_used = []

    for agent in primary_agents:
        logger.info(f"Running agent: {agent}")
        temp = 0.6 if agent in ("Brain", "Analyst") else 0.8
        result, model = await run_agent(
            agent, user_message, context_messages, models, temp
        )
        if result:
            draft = result
            model_used = model
            agents_used.append(agent)
            break

    if not draft:
        from config import FREE_MODELS
        logger.warning("Primary agents failed, trying fallback")
        fallback_models = FREE_MODELS["default"]
        messages = [
            {
                "role": "system",
                "content": "Ты NetonAI. Отвечай полезно и на русском языке.",
            },
            {"role": "user", "content": user_message},
        ]
        from openrouter import call_with_fallback as cwf
        draft, model_used = await cwf(messages, fallback_models)
        agents_used = ["Brain"]

    if draft and critic_in_list:
        logger.info("Running Critic agent")
        user_context = (
            f"Стиль: {profile.get('style', 'дружелюбный')}, "
            f"Уровень: {profile.get('level', 'средний')}"
        )
        improved = await run_critic(user_message, draft, models, user_context)
        if improved:
            draft = improved
            agents_used.append("Critic")

    return draft or "Извините, не удалось получить ответ. Попробуйте позже.", agents_used, model_used
