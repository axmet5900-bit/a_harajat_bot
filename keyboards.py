from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_keyboard():
    """Asosiy menyu"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="💰 Daromad"),
        KeyboardButton(text="💸 Xarajat")
    )
    builder.row(
        KeyboardButton(text="📊 Statistika"),
        KeyboardButton(text="📝 Qarzlar")
    )
    builder.row(
        KeyboardButton(text="💰 Byudjet"),
        KeyboardButton(text="📅 Eslatmalar")
    )
    builder.row(
        KeyboardButton(text="📁 Hisobot"),
        KeyboardButton(text="⚙️ Sozlamalar")
    )
    return builder.as_markup(resize_keyboard=True)

def get_categories_keyboard(categories):
    """Kategoriyalar menyusi"""
    builder = InlineKeyboardBuilder()
    for cat in categories[:8]:
        builder.button(
            text=f"{cat[3]} {cat[2]}",  # emoji + name
            callback_data=f"cat_{cat[2]}"
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="➕ Yangi", callback_data="new_category"),
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_main")
    )
    return builder.as_markup()

def get_period_keyboard():
    """Davr tanlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Kun", callback_data="period_day"),
        InlineKeyboardButton(text="📆 Hafta", callback_data="period_week")
    )
    builder.row(
        InKeyboardButton(text="🗓 Oy", callback_data="period_month"),
        InlineKeyboardButton(text="📊 Yil", callback_data="period_year")
    )
    return builder.as_markup()

def get_report_keyboard():
    """Hisobot turlari"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Excel", callback_data="report_excel"),
        InlineKeyboardButton(text="📄 PDF", callback_data="report_pdf")
    )
    builder.row(
        InlineKeyboardButton(text="📈 Diagramma", callback_data="report_chart"),
        InlineKeyboardButton(text="📊 Tahlil", callback_data="report_analysis")
    )
    return builder.as_markup()

def get_debts_keyboard(debts):
    """Qarzlar menyusi"""
    builder = InlineKeyboardBuilder()
    for debt in debts:
        status = "✅" if debt[5] == 'paid' else "⏳"
        builder.button(
            text=f"{status} {debt[2]}: {debt[3]:,.0f}",
            callback_data=f"debt_{debt[0]}"
        )
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="➕ Yangi qarz", callback_data="new_debt"),
        InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_debts")
    )
    return builder.as_markup()

def get_settings_keyboard():
    """Sozlamalar menyusi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌐 Til", callback_data="set_lang"),
        InlineKeyboardButton(text="💰 Valyuta", callback_data="set_currency")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Oylik daromad", callback_data="set_income"),
        InlineKeyboardButton(text="⏰ Eslatma vaqti", callback_data="set_notification")
    )
    builder.row(
        InlineKeyboardButton(text="🔐 PIN kod", callback_data="set_pin"),
        InlineKeyboardButton(text="💳 Bank kartalari", callback_data="manage_cards")
    )
    builder.row(
        InlineKeyboardButton(text="💾 Zaxiralash", callback_data="backup"),
        InlineKeyboardButton(text="📤 Eksport", callback_data="export")
    )
    return builder.as_markup()

def get_confirmation_keyboard(action):
    """Tasdiqlash menyusi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm_{action}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data=f"cancel_{action}")
    )
    return builder.as_markup()
