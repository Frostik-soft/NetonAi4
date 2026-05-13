from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import MODEL_INFO, FREE_MODELS, get_models_by_category, get_all_unique_models, get_catalog_categories

MODELS_PER_PAGE = 6


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 NetonAI режим", callback_data="mode_netonai")],
        [InlineKeyboardButton(text="📚 Каталог моделей", callback_data="catalog_main")],
        [InlineKeyboardButton(text="🧠 Память", callback_data="memory_info")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_main")],
    ])


def catalog_keyboard() -> InlineKeyboardMarkup:
    """
    Dynamically generated catalog menu from FREE_MODELS categories.
    Existing static buttons are preserved; categories are now auto-generated.
    """
    rows = []
    for key, emoji, label in get_catalog_categories():
        rows.append([
            InlineKeyboardButton(
                text=f"{emoji} {label}",
                callback_data=f"catpage_{key}_0",
            )
        ])
    rows.append([
        InlineKeyboardButton(text="📋 Все модели", callback_data="allpage_0")
    ])
    rows.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def model_list_keyboard(category: str) -> InlineKeyboardMarkup:
    """Backward-compatible: delegates to paged version, page 0."""
    return model_list_paged_keyboard(category, page=0)


def model_list_paged_keyboard(category: str, page: int = 0) -> InlineKeyboardMarkup:
    """
    Paginated model list for a given category.
    Auto-generated from FREE_MODELS — no manual edits needed when adding models.
    """
    models = get_models_by_category(category)
    total = len(models)
    start = page * MODELS_PER_PAGE
    end = start + MODELS_PER_PAGE
    page_models = models[start:end]
    total_pages = max(1, (total + MODELS_PER_PAGE - 1) // MODELS_PER_PAGE)

    rows = []
    for model_id in page_models:
        info = MODEL_INFO.get(model_id, {})
        name = info.get("name", model_id.split("/")[-1][:28])
        type_icon = info.get("type", "🤖").split(" ")[0]
        rows.append([
            InlineKeyboardButton(
                text=f"{type_icon} {name}",
                callback_data=f"model_info_{model_id[:40]}",
            )
        ])

    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="◀️", callback_data=f"catpage_{category}_{page - 1}")
        )
    if total_pages > 1:
        nav_row.append(
            InlineKeyboardButton(
                text=f"{page + 1}/{total_pages}", callback_data="noop"
            )
        )
    if end < total:
        nav_row.append(
            InlineKeyboardButton(text="▶️", callback_data=f"catpage_{category}_{page + 1}")
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="◀️ Назад к категориям", callback_data="catalog_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def all_models_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Paginated view of every unique model across all non-default categories."""
    models = get_all_unique_models()
    total = len(models)
    start = page * MODELS_PER_PAGE
    end = start + MODELS_PER_PAGE
    page_models = models[start:end]
    total_pages = max(1, (total + MODELS_PER_PAGE - 1) // MODELS_PER_PAGE)

    rows = []
    for model_id in page_models:
        info = MODEL_INFO.get(model_id, {})
        name = info.get("name", model_id.split("/")[-1][:28])
        type_icon = info.get("type", "🤖").split(" ")[0]
        rows.append([
            InlineKeyboardButton(
                text=f"{type_icon} {name}",
                callback_data=f"model_info_{model_id[:40]}",
            )
        ])

    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="◀️", callback_data=f"allpage_{page - 1}")
        )
    if total_pages > 1:
        nav_row.append(
            InlineKeyboardButton(
                text=f"{page + 1}/{total_pages}", callback_data="noop"
            )
        )
    if end < total:
        nav_row.append(
            InlineKeyboardButton(text="▶️", callback_data=f"allpage_{page + 1}")
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="◀️ Назад к категориям", callback_data="catalog_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def model_detail_keyboard(model_id: str) -> InlineKeyboardMarkup:
    safe_id = model_id[:40]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Использовать эту модель", callback_data=f"use_model_{safe_id}")],
        [InlineKeyboardButton(text="◀️ Назад к каталогу", callback_data="catalog_main")],
    ])


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Стиль общения", callback_data="settings_style")],
        [InlineKeyboardButton(text="📊 Уровень знаний", callback_data="settings_level")],
        [InlineKeyboardButton(text="🔄 Сбросить модель", callback_data="settings_reset_model")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])


def style_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="😊 Дружелюбный", callback_data="style_дружелюбный")],
        [InlineKeyboardButton(text="📋 Строгий", callback_data="style_строгий")],
        [InlineKeyboardButton(text="📚 Объясняющий", callback_data="style_объясняющий")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_main")],
    ])


def level_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 Новичок", callback_data="level_новичок")],
        [InlineKeyboardButton(text="⚙️ Средний", callback_data="level_средний")],
        [InlineKeyboardButton(text="🚀 Эксперт", callback_data="level_эксперт")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_main")],
    ])


def feedback_keyboard(intent: str, model: str) -> InlineKeyboardMarkup:
    safe_model = (model or "unknown")[:40]
    safe_intent = (intent or "chat")[:20]
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👍", callback_data=f"fb_ok_{safe_intent}_{safe_model}"
            ),
            InlineKeyboardButton(
                text="👎", callback_data=f"fb_bad_{safe_intent}_{safe_model}"
            ),
        ]
    ])


def memory_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить историю", callback_data="memory_clear")],
        [InlineKeyboardButton(text="📊 Статистика обучения", callback_data="memory_learning")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])


def confirm_clear_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, очистить", callback_data="memory_clear_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="memory_info"),
        ]
    ])
