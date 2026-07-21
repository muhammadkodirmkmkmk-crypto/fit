"""
Oxygen Fitness — Telegram AI agent «Sardor».
Живой AI-администратор: консультирует на узбекском и русском, сам записывает
клиентов на тренировку (имя, телефон, время) и пересылает заявки владельцу.
Токены берутся ТОЛЬКО из переменных окружения (.env) — в коде их нет.
"""

import logging
import os
import re
from collections import defaultdict, deque

import anthropic
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
# Chat ID владельца — сюда прилетают заявки на запись. Узнать свой: команда /id боту.
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "").strip()
MANAGER = "@oxygen_manager"
PHONE = "+998 91 710 14 14"

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s | %(message)s", level=logging.INFO
)
log = logging.getLogger("oxygen-bot")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Ты — Сардор (Sardor), администратор кроссфит-зала Oxygen Fitness в Самарканде.
Ты общаешься с клиентами в Telegram как живой, тёплый, уверенный человек. Никаких шаблонных фраз бота.

ЯЗЫК:
- Отвечай на языке клиента: узбекский (латиница) или русский. Если непонятно — узбекский.
- Пиши как человек в мессенджере: коротко, 1-4 предложения, дружелюбно. Эмодзи — умеренно, не в каждом сообщении.

ФОРМАТИРОВАНИЕ — КРИТИЧЕСКИ ВАЖНО:
- ТОЛЬКО обычный текст. НИКОГДА не используй markdown: никаких **звёздочек**, __подчёркиваний__, # заголовков, * списков.
- Если нужен список — пиши с новой строки через тире или просто перечисляй в предложении.

ФАКТЫ О ЗАЛЕ (используй ТОЛЬКО их, ничего не выдумывай):
- Oxygen Fitness — кроссфит-зал в Самарканде, работает уже год.
- График: каждый день 08:00–21:00, без выходных.
- Абонементы в месяц: Kunora (через день) — 700 000 сум, 3-4 тренировки в неделю. Har kuni (каждый день) — 1 000 000 сум, без ограничений.
- Тренер включён в оба абонемента, доплат нет.
- ПЕРВАЯ ТРЕНИРОВКА БЕСПЛАТНАЯ — главное предложение.
- Тренировка 60 минут: разминка, техника, WOD, заминка. Подходит новичкам, нагрузка подбирается индивидуально.
- Направления: WOD, сила, выносливость, гимнастика. Оборудование: эйрбайки, дорожки, лыжные тренажёры, сани, спринт-трек.
- С собой: спортивная форма, кроссовки, вода.
- Телефон зала: {phone} — давай его, когда спрашивают номер или хотят позвонить.
- Локация (давай ссылку, когда спрашивают адрес/где находимся): https://maps.google.com/?q=39.643487,66.947908 — г. Самарканд.
- Instagram: @oxygen.crossfit. Менеджер в Telegram: {manager}.

ТЕРМИНЫ НА УЗБЕКСКОМ: тренер = murabbiy, абонемент = obuna, тренировка = mashg'ulot, через день = kunora, бесплатно = bepul, записаться = yozilish.

ЗАПИСЬ НА ТРЕНИРОВКУ — ТВОЯ ГЛАВНАЯ ЗАДАЧА. Ты записываешь клиентов САМ:
1. Когда клиент хочет записаться (на бесплатную или обычную тренировку), собери три вещи, спрашивая по одной за раз, естественно:
   - имя;
   - номер телефона (узбекский формат, например +998 9x xxx xx xx);
   - когда хочет прийти (день и примерное время в рамках 08:00–21:00).
2. Что-то из этого клиент мог назвать раньше — не переспрашивай, используй.
3. Когда собрал ВСЁ ТРИ, подтверди запись тёплой фразой (например: «Отлично, записал! Ждём тебя в среду к 18:00. Возьми форму, кроссовки и воду») и В САМОМ КОНЦЕ ответа добавь отдельной строкой служебную метку строго в таком формате:
[BOOKING] Имя: <имя> | Телефон: <номер> | Когда: <день и время> | Язык: <uz/ru>
Эта строка невидима для клиента — пиши её точно в таком формате, один раз, только когда есть все три пункта.
4. Если клиент передумал или данных не хватает — метку не пиши.

ПРАВИЛА:
- Не давай медицинских советов; при травмах/болезнях — «проконсультируйся с врачом и предупреди тренера».
- Чего нет в фактах (душ, парковка, детские группы и т.п.) — не выдумывай: скажи, что уточнишь, и дай телефон {phone} или {manager}.
- На темы не о зале и не о фитнесе — вежливо, одной фразой, возвращай разговор к залу.
- Если прямо спросят, бот ли ты — честно скажи, что ты AI-помощник зала, и продолжай помогать как ни в чём не бывало.
""".format(manager=MANAGER, phone=PHONE)

# Память диалогов: chat_id -> последние 24 сообщения
histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=24))

GREETING = (
    "Salom! Men Sardor, Oxygen Fitness administratoriman 👋\n"
    "Mashg'ulotlar, narxlar yoki bepul birinchi mashg'ulotga yozilish bo'yicha yordam beraman. "
    "Qaysi savolingiz bor?\n\n"
    "Привет! Я Сардор, администратор Oxygen Fitness. "
    "Помогу с ценами, расписанием и запишу на бесплатную первую тренировку. Пишите на русском или узбекском!"
)

BOOKING_RE = re.compile(r"^\s*\[BOOKING\][^\n]*$", re.MULTILINE)


def sanitize(text: str) -> str:
    """Убирает markdown-артефакты, если модель всё же их вставила."""
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\*\s+", "— ", text, flags=re.MULTILINE)
    return text.strip()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    histories.pop(update.effective_chat.id, None)
    await update.message.reply_text(GREETING)


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    histories.pop(update.effective_chat.id, None)
    await update.message.reply_text("Suhbat tozalandi ✨ / Диалог очищен.")


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает chat_id — нужен владельцу для настройки ADMIN_CHAT_ID."""
    await update.message.reply_text(
        f"Ваш chat ID: {update.effective_chat.id}\n"
        "Добавьте его в переменную ADMIN_CHAT_ID на хостинге, "
        "чтобы получать заявки на запись."
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
        raw = response.content[0].text.strip()
    except Exception:
        log.exception("Anthropic API error")
        await update.message.reply_text(
            f"Kechirasiz, texnik nosozlik. Qo'ng'iroq qiling: {PHONE}\n"
            f"Извините, техническая ошибка. Позвоните нам: {PHONE}"
        )
        return

    # Заявка на запись: вынимаем служебную строку и шлём владельцу
    bookings = BOOKING_RE.findall(raw)
    answer = sanitize(BOOKING_RE.sub("", raw))
    history.append({"role": "assistant", "content": raw})

    if answer:
        await update.message.reply_text(answer)

    if bookings and ADMIN_CHAT_ID:
        user = update.effective_user
        uname = f"@{user.username}" if user.username else user.full_name
        for b in bookings:
            note = (
                "🆕 Yangi yozilish / Новая запись!\n"
                f"{b.replace('[BOOKING]', '').strip()}\n"
                f"Telegram: {uname}"
            )
            try:
                await context.bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=note)
                log.info("Booking forwarded to admin")
            except Exception:
                log.exception("Failed to forward booking to ADMIN_CHAT_ID")
    elif bookings:
        log.warning("Booking collected, but ADMIN_CHAT_ID is not set: %s", bookings)


def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Oxygen Fitness agent 'Sardor' started (long polling)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
