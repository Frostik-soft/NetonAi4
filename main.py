import asyncio
import logging
import traceback

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    BotCommand,
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, MODEL_INFO, get_catalog_categories
from memory import save_message, get_context_messages, clear_history, get_stats
from profiles import (
    load_profile,
    save_profile,
    update_style,
    update_level,
    set_preferred_model,
    set_last_used_model,
    get_active_model_display,
    increment_requests,
    get_system_prompt_for_user,
)
from router import route, INTENT_LABELS
from agents import multi_agent_process
from learning import record_result, record_result_from_feedback, get_stats_text
from keyboards import (
    main_menu_keyboard,
    catalog_keyboard,
    model_list_keyboard,
    model_list_paged_keyboard,
    all_models_keyboard,
    model_detail_keyboard,
    settings_keyboard,
    style_keyboard,
    level_keyboard,
    feedback_keyboard,
    memory_keyboard,
    confirm_clear_keyboard,
)
from utils import setup_logging, split_long_message, thinking_message, Timer

setup_logging()
logger = logging.getLogger(__name__)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)
dp = Dispatcher()

pending_feedback: dict[int, dict] = {}


@dp.message(CommandStart())
async def start_handler(message: Message):
    user = message.from_user
    profile = load_profile(user.id, user.first_name or "Пользователь")
    profile["name"] = user.first_name or "Пользователь"
    save_profile(user.id, profile)

    text = (
        f"👋 Привет, *{user.first_name}*!\n\n"
        f"Я *NetonAI* — ваш умный AI-ассистент с мульти-агентной системой.\n\n"
        f"🤖 Просто напишите мне что угодно:\n"
        f"• Вопросы и объяснения\n"
        f"• Написание кода\n"
        f"• Творческие задачи\n"
        f"• Анализ и рассуждения\n\n"
        f"Или воспользуйтесь меню ниже:"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())


@dp.message(Command("menu"))
async def menu_handler(message: Message):
    await message.answer("📋 *Главное меню NetonAI*", reply_markup=main_menu_keyboard())


@dp.message(Command("clear"))
async def clear_handler(message: Message):
    clear_history(message.from_user.id)
    await message.answer("🗑 История диалога очищена.")


@dp.message(Command("stats"))
async def stats_handler(message: Message):
    await message.answer(get_stats_text(), parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("profile"))
async def profile_handler(message: Message):
    user = message.from_user
    profile = load_profile(user.id, user.first_name or "")
    stats = get_stats(user.id)
    active_model = get_active_model_display(profile)
    text = (
        f"👤 *Ваш профиль*\n\n"
        f"Имя: {profile.get('name', 'Пользователь')}\n"
        f"Стиль: {profile.get('style', 'дружелюбный')}\n"
        f"Уровень: {profile.get('level', 'средний')}\n"
        f"Модель: {active_model}\n"
        f"Запросов: {stats.get('message_count', 0)}\n"
        f"Последняя активность: {str(stats.get('last_active', '—'))[:19]}\n"
    )
    await message.answer(text, reply_markup=settings_keyboard())


async def process_user_message(message: Message, text: str, has_image: bool = False):
    user = message.from_user
    profile = load_profile(user.id, user.first_name or "Пользователь")

    routing = route(text, has_image, profile.get("preferred_model"))
    intent = routing["intent"]
    agents = routing["agents"]
    models = routing["models"]

    intent_label = INTENT_LABELS.get(intent, intent)
    thinking_msg = await message.answer(
        f"{thinking_message(intent)}\n_Агенты: {', '.join(agents)}_",
        parse_mode=ParseMode.MARKDOWN,
    )

    timer = Timer()
    system_prompt = get_system_prompt_for_user(profile)
    context = get_context_messages(user.id, system_prompt)
    save_message(user.id, "user", text)

    try:
        answer, agents_used, model_used = await multi_agent_process(
            text, context, agents, models, profile
        )
    except Exception as e:
        logger.error(f"Agent error: {e}\n{traceback.format_exc()}")
        await thinking_msg.delete()
        await message.answer("⚠️ Произошла ошибка при обработке запроса. Попробуйте ещё раз.")
        return

    elapsed = timer.elapsed_str()
    model_short = (model_used or "").split("/")[-1].replace(":free", "")[:25]
    footer = f"\n\n_— {intent_label} · {model_short} · {elapsed}_"

    await thinking_msg.delete()

    parts = split_long_message(answer)
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        try:
            if is_last:
                await message.answer(
                    part + footer,
                    reply_markup=feedback_keyboard(intent, model_used or ""),
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await message.answer(part, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            if is_last:
                await message.answer(
                    part + footer,
                    reply_markup=feedback_keyboard(intent, model_used or ""),
                    parse_mode=None,
                )
            else:
                await message.answer(part, parse_mode=None)

    pending_feedback[user.id] = {
        "agents": agents_used,
        "model": model_used,
        "intent": intent,
    }

    save_message(user.id, "assistant", answer)
    increment_requests(user.id, success=bool(answer))
    if model_used and model_used != "fallback":
        set_last_used_model(user.id, model_used)


@dp.message(F.text & ~F.text.startswith("/"))
async def text_message_handler(message: Message):
    await process_user_message(message, message.text)


@dp.message(F.photo)
async def photo_handler(message: Message):
    caption = message.caption or "Опиши что на этом изображении"
    await process_user_message(message, caption, has_image=True)


@dp.callback_query(F.data == "menu_main")
async def cb_menu_main(cb: CallbackQuery):
    await cb.message.edit_text("📋 *Главное меню NetonAI*", reply_markup=main_menu_keyboard())
    await cb.answer()


@dp.callback_query(F.data == "mode_netonai")
async def cb_mode_netonai(cb: CallbackQuery):
    profile = load_profile(cb.from_user.id)
    profile["netonai_mode"] = True
    save_profile(cb.from_user.id, profile)
    await cb.message.edit_text(
        "🤖 *NetonAI режим активен*\n\nПросто напишите ваш вопрос или задачу!",
        reply_markup=main_menu_keyboard(),
    )
    await cb.answer("NetonAI режим включён!")


@dp.callback_query(F.data == "catalog_main")
async def cb_catalog_main(cb: CallbackQuery):
    await cb.message.edit_text(
        "📚 *Каталог моделей*\n\nВыберите категорию:",
        reply_markup=catalog_keyboard(),
    )
    await cb.answer()


@dp.callback_query(F.data.in_(["catalog_text", "catalog_coding", "catalog_vision"]))
async def cb_catalog_category_legacy(cb: CallbackQuery):
    """Backward-compatible handlers for old static catalog buttons."""
    category_map = {
        "catalog_text": ("chat", "🧠 Текстовые модели"),
        "catalog_coding": ("coding", "💻 Кодовые модели"),
        "catalog_vision": ("vision", "👁 Анализ изображений"),
    }
    cat_key, cat_title = category_map[cb.data]
    await cb.message.edit_text(
        f"📚 *{cat_title}*\n\nВыберите модель для просмотра:",
        reply_markup=model_list_paged_keyboard(cat_key, page=0),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("catpage_"))
async def cb_catalog_paged(cb: CallbackQuery):
    """Dynamic paginated category view. Format: catpage_{category}_{page}"""
    parts = cb.data.split("_", 2)
    if len(parts) < 3:
        await cb.answer()
        return
    _, category, page_str = parts
    try:
        page = int(page_str)
    except ValueError:
        page = 0

    cats = {k: (e, l) for k, e, l in get_catalog_categories()}
    emoji, label = cats.get(category, ("🤖", category.capitalize()))
    await cb.message.edit_text(
        f"📚 *{emoji} {label}*\n\nВыберите модель:",
        reply_markup=model_list_paged_keyboard(category, page=page),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("allpage_"))
async def cb_all_models_paged(cb: CallbackQuery):
    """All models paginated view. Format: allpage_{page}"""
    page_str = cb.data[len("allpage_"):]
    try:
        page = int(page_str)
    except ValueError:
        page = 0
    await cb.message.edit_text(
        "📋 *Все модели*\n\nПолный список доступных бесплатных моделей:",
        reply_markup=all_models_keyboard(page=page),
    )
    await cb.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery):
    await cb.answer()


@dp.callback_query(F.data.startswith("model_info_"))
async def cb_model_info(cb: CallbackQuery):
    model_id = cb.data[len("model_info_"):]
    full_model = next(
        (m for m in MODEL_INFO if m.startswith(model_id) or m[:40] == model_id),
        model_id,
    )
    info = MODEL_INFO.get(full_model, {})
    text = (
        f"*{info.get('name', full_model)}*\n\n"
        f"Тип: {info.get('type', '🤖')}\n"
        f"Описание: {info.get('description', 'Нет описания')}\n\n"
        f"ID: `{full_model}`"
    )
    await cb.message.edit_text(text, reply_markup=model_detail_keyboard(full_model))
    await cb.answer()


@dp.callback_query(F.data.startswith("use_model_"))
async def cb_use_model(cb: CallbackQuery):
    model_id = cb.data[len("use_model_"):]
    full_model = next(
        (m for m in MODEL_INFO if m.startswith(model_id) or m[:40] == model_id),
        model_id,
    )
    set_preferred_model(cb.from_user.id, full_model)
    info = MODEL_INFO.get(full_model, {})
    model_name = info.get("name", full_model)
    await cb.message.edit_text(
        f"✅ Модель *{model_name}* выбрана как предпочтительная.\n\n"
        f"Теперь NetonAI будет использовать её в первую очередь.",
        reply_markup=main_menu_keyboard(),
    )
    await cb.answer(f"Выбрана: {model_name}")


@dp.callback_query(F.data == "memory_info")
async def cb_memory_info(cb: CallbackQuery):
    stats = get_stats(cb.from_user.id)
    count = stats.get("message_count", 0)
    history_len = stats.get("history_len", 0)
    last = str(stats.get("last_active", "никогда"))[:19]
    text = (
        f"🧠 *Память NetonAI*\n\n"
        f"Сообщений в базе: {count}\n"
        f"Активная история: {history_len} сообщений\n"
        f"Последняя активность: {last}\n\n"
        f"NetonAI помнит ваш стиль общения и историю диалога."
    )
    await cb.message.edit_text(text, reply_markup=memory_keyboard())
    await cb.answer()


@dp.callback_query(F.data == "memory_clear")
async def cb_memory_clear(cb: CallbackQuery):
    await cb.message.edit_text(
        "🗑 Вы уверены, что хотите очистить историю диалога?",
        reply_markup=confirm_clear_keyboard(),
    )
    await cb.answer()


@dp.callback_query(F.data == "memory_clear_confirm")
async def cb_memory_clear_confirm(cb: CallbackQuery):
    clear_history(cb.from_user.id)
    await cb.message.edit_text(
        "✅ История диалога очищена.\n\nМожете начать новый разговор!",
        reply_markup=main_menu_keyboard(),
    )
    await cb.answer("История очищена!")


@dp.callback_query(F.data == "memory_learning")
async def cb_memory_learning(cb: CallbackQuery):
    text = get_stats_text()
    await cb.message.edit_text(text, reply_markup=memory_keyboard())
    await cb.answer()


@dp.callback_query(F.data == "settings_main")
async def cb_settings_main(cb: CallbackQuery):
    profile = load_profile(cb.from_user.id)
    active_model = get_active_model_display(profile)
    text = (
        f"⚙️ *Настройки*\n\n"
        f"Стиль: {profile.get('style', 'дружелюбный')}\n"
        f"Уровень: {profile.get('level', 'средний')}\n"
        f"Модель: {active_model}"
    )
    await cb.message.edit_text(text, reply_markup=settings_keyboard())
    await cb.answer()


@dp.callback_query(F.data == "settings_style")
async def cb_settings_style(cb: CallbackQuery):
    await cb.message.edit_text(
        "🎨 *Выберите стиль общения:*", reply_markup=style_keyboard()
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("style_"))
async def cb_set_style(cb: CallbackQuery):
    style = cb.data[len("style_"):]
    update_style(cb.from_user.id, style)
    await cb.message.edit_text(
        f"✅ Стиль общения изменён на *{style}*.",
        reply_markup=settings_keyboard(),
    )
    await cb.answer(f"Стиль: {style}")


@dp.callback_query(F.data == "settings_level")
async def cb_settings_level(cb: CallbackQuery):
    await cb.message.edit_text(
        "📊 *Выберите уровень знаний:*", reply_markup=level_keyboard()
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("level_"))
async def cb_set_level(cb: CallbackQuery):
    level = cb.data[len("level_"):]
    update_level(cb.from_user.id, level)
    await cb.message.edit_text(
        f"✅ Уровень знаний изменён на *{level}*.",
        reply_markup=settings_keyboard(),
    )
    await cb.answer(f"Уровень: {level}")


@dp.callback_query(F.data == "settings_reset_model")
async def cb_reset_model(cb: CallbackQuery):
    set_preferred_model(cb.from_user.id, None)
    await cb.message.edit_text(
        "✅ Предпочтительная модель сброшена.\n\nNetonAI будет автоматически выбирать лучшую модель.",
        reply_markup=settings_keyboard(),
    )
    await cb.answer("Модель сброшена")


@dp.callback_query(F.data.startswith("fb_"))
async def cb_feedback(cb: CallbackQuery):
    parts = cb.data.split("_", 3)
    if len(parts) < 4:
        await cb.answer()
        return
    _, result, intent, model = parts[0], parts[1], parts[2], parts[3]
    success = result == "ok"

    pending = pending_feedback.pop(cb.from_user.id, {})
    agents_used = pending.get("agents", ["Brain"])

    record_result_from_feedback(agents_used, model, intent, success)
    increment_requests(cb.from_user.id, success=success)

    if success:
        await cb.answer("👍 Спасибо! Агенты учатся на вашей оценке.")
    else:
        await cb.answer("👎 Понял. Постараемся улучшиться!")

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Запустить NetonAI"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="stats", description="Статистика обучения"),
        BotCommand(command="clear", description="Очистить историю"),
    ]
    await bot.set_my_commands(commands)


async def main():
    logger.info("Starting NetonAI bot...")
    await set_bot_commands()
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
