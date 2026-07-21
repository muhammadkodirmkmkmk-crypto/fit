"""
Oxygen Fitness — Telegram AI agent.
Отвечает клиентам и проводит первичную консультацию на узбекском и русском.
Токены берутся ТОЛЬКО из переменных окружения (.env) — в коде их нет.
"""

import logging
import os
from collections import defaultdict, deque

import anthropic
from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
MANAGER = "@oxygen_manager"

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s | %(message)s", level=logging.INFO
)
log = logging.getLogger("oxygen-bot")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Ты — AI-консультант кроссфит-зала Oxygen Fitness в Самарканде (Узбекистан).
Твоя задача: дружелюбно консультировать клиентов в Telegram и мягко вести их к записи на бесплатную первую тренировку.

ЯЗЫК:
- Отвечай на том языке, на котором пишет клиент: узбекский (латиница) или русский.
- Если язык непонятен — отвечай на узбекском.
- Пиши коротко и живо, как менеджер в мессенджере: 2-5 предложений, без канцелярита. Можно умеренно использовать эмодзи.

ФАКТЫ О ЗАЛЕ (используй ТОЛЬКО их, ничего не выдумывай):
- Название: Oxygen Fitness, кроссфит-зал. Открылся год назад (в 2025).
- Город: Самарканд. Точная локация: https://maps.google.com/?q=39.643487,66.947908 (можно отправить эту ссылку).
- График: каждый день с 08:00 до 21:00, без выходных (7/7).
- Абонементы (в месяц): «Через день» (kunora) — 700 000 сум, 3-4 тренировки в неделю; «Каждый день» (har kuni) — 1 000 000 сум, без ограничений.
- Тренерское сопровождение ВКЛЮЧЕНО в оба абонемента, доплат нет. Каждая тренировка проходит под руководством тренера.
- ПЕРВАЯ ТРЕНИРОВКА — БЕСПЛАТНО. Это главное предложение, упоминай его, когда уместно.
- Тренировка длится 60 минут: разминка (10 мин) → техника (15 мин) → WOD, основной комплекс (25 мин) → заминка (10 мин).
- Направления: WOD, силовая работа (штанга, гантели), выносливость (эйрбайк, бег, гребля), гимнастика (подтягивания, работа с собственным весом).
- Оборудование: эйрбайки, беговые дорожки, лыжные тренажёры, сани, спринт-трек.
- Подходит любому уровню, включая полных новичков — нагрузка масштабируется индивидуально.
- С собой на тренировку: спортивная форма, кроссовки, вода.
- Instagram: @oxygen.crossfit. Менеджер: {manager}.

ТЕРМИНЫ НА УЗБЕКСКОМ (используй именно их): тренер = murabbiy, тренерское сопровождение = murabbiy hamrohligi, абонемент = obuna, тренировка = mashg'ulot, через день = kunora, каждый день = har kuni, бесплатно = bepul, записаться = yozilish.

ПРАВИЛА:
- Цель разговора — помочь и пригласить на бесплатную пробную тренировку.
- Запись на тренировку, вопросы об оплате, заморозке, индивидуальных условиях — направляй к менеджеру {manager}, он подтверждает запись.
- Если спрашивают то, чего нет в фактах (например, про душ, парковку, детские группы) — честно скажи, что уточнит менеджер {manager}, не выдумывай.
- На вопросы не о зале и не о фитнесе отвечай вежливо одной фразой, что можешь помочь только по вопросам Oxygen Fitness.
- Не давай медицинских рекомендаций; при вопросах о здоровье и травмах советуй проконсультироваться с врачом и предупредить тренера.
""".format(manager=MANAGER)

# Память диалогов: chat_id -> последние 20 сообщений
histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=20))

GREETING = (
    "Salom! 👋 Men Oxygen Fitness'ning AI-yordamchisiman.\n"
    "Narxlar, jadval, birinchi bepul mashg'ulot haqida so'rang — javob beraman!\n\n"
    "Привет! Я AI-помощник Oxygen Fitness.\n"
    "Спрашивайте о ценах, графике и бесплатной первой тренировке — на русском или узбекском."
)

KEYBOARD = ReplyKeyboardMarkup(
    [
        ["💰 Narxlar / Цены", "🕒 Ish vaqti / График"],
        ["📍 Manzil / Адрес", "🎁 Bepul mashg'ulot / Бесплатная тренировка"],
    ],
    resize_keyboard=True,
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    histories.pop(update.effective_chat.id, None)
    await update.message.reply_text(GREETING, reply_markup=KEYBOARD)


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    histories.pop(update.effective_chat.id, None)
    await update.message.reply_text(
        "Suhbat tozalandi ✨ / Диалог очищен — можно начинать заново."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = (update.message.text or "").strip()
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    history = histories[chat_id]
    history.append({"role": "user", "content": user_text})

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=700,
            system=SYSTEM_PROMPT,
            messages=list(history),
        )
        answer = response.content[0].text.strip()
    except Exception:
        log.exception("Anthropic API error")
        answer = (
            f"Kechirasiz, texnik nosozlik yuz berdi. Menejerga yozing: {MANAGER}\n"
            f"Извините, техническая ошибка. Напишите менеджеру: {MANAGER}"
        )

    history.append({"role": "assistant", "content": answer})
    await update.message.reply_text(answer)


def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Oxygen Fitness bot started (long polling)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
