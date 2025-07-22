

import os
import json
import random
import re
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Загрузка токена
load_dotenv(dotenv_path=Path(__file__).parent / ".env")
TOKEN = os.getenv("TOKEN")  # Убедись, что в .env есть строка: TOKEN=your_token_here

DATA_FILE = "cards.json"
quiz_mode = {}
correct_answer_map = {}

# --- Работа с файлами
def load_cards():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cards(cards):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

# --- Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    cards = load_cards()
    total = len(cards.get(user_id, {}))

    text = (
        f"👋 Привет! У тебя уже сохранено {total} слов. "
        "Можешь использовать /quiz для тренировки или добавить новые слова в формате: dog - собака"
    )
    await update.message.reply_text(text)
    

async def handle_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    cards = load_cards()
    user_cards = cards.get(user_id, {})

    lines = update.message.text.strip().split("\n")
    added, skipped = 0, 0

    for line in lines:
        parts = re.split(r"\s*[-–—]\s*", line, maxsplit=1)
        if len(parts) != 2:
            skipped += 1
            continue
        word, translation = parts
        word, translation = word.strip(), translation.strip()
        if word and translation:
            user_cards[word] = translation
            added += 1
        else:
            skipped += 1

    cards[user_id] = user_cards
    save_cards(cards)

    msg = f"✅ Добавлено: {added}."
    if skipped:
        msg += f" Пропущено: {skipped} строк (неверный формат)."
    await update.message.reply_text(msg)

# --- Квиз
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    cards = load_cards().get(user_id, {})

    print(f">>> /quiz команда вызвана от {user_id}, всего слов: {len(cards)}")

    if len(cards) < 2:
        await update.message.reply_text("⛔️ Нужно минимум 2 слова для квиза.")
        return

    word, correct = random.choice(list(cards.items()))
    wrong = random.choice([v for k, v in cards.items() if v != correct] or ["(другой перевод)"])

    options = [correct, wrong]
    random.shuffle(options)

    correct_index = options.index(correct)
    context.user_data["quiz_word"] = word
    context.user_data["quiz_correct_index"] = correct_index
    context.user_data["quiz_options"] = options

    keyboard = [
        [InlineKeyboardButton(text=opt, callback_data=str(i))]
        for i, opt in enumerate(options)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"❓ Как переводится: *{word}*?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

    

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_data = context.user_data
    correct_index = user_data.get("quiz_correct_index")
    options = user_data.get("quiz_options", [])
    selected_index = int(query.data)

    if selected_index == correct_index:
        await query.edit_message_text("✅ Правильно!")
    else:
        correct = options[correct_index]
        await query.edit_message_text(f"❌ Неправильно. Правильный ответ: {correct}")


# --- Главный запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CallbackQueryHandler(handle_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_words))

    app.run_polling()
