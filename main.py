import os
import re
import asyncio
import pandas as pd
from flask import Flask, request
from telegram import Update, Bot, Document
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.ext import Dispatcher

TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

OUTPUT_DIR = "output_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
bot = Bot(TOKEN)

# ✅ ফাইল নাম নির্ধারণ
def get_next_filename(prefix: str):
    i = 0
    while True:
        name = f"{prefix}{'_' + str(i) if i else ''}.txt"
        full_path = os.path.join(OUTPUT_DIR, name)
        if not os.path.exists(full_path):
            return full_path
        i += 1

# ✅ নাম্বার detect function (text)
def extract_numbers_from_text(text: str):
    return re.findall(r"\b\d{5,}\b", text)  # 5 ডিজিট বা তার বেশি নাম্বার

# ✅ .xlsx থেকে নাম্বার
def extract_numbers_from_xlsx(file_path: str):
    numbers = []
    try:
        xls = pd.ExcelFile(file_path)
        for sheet in xls.sheet_names:
            df = xls.parse(sheet)
            for col in df.columns:
                col_data = df[col].astype(str)
                for val in col_data:
                    matches = extract_numbers_from_text(val)
                    numbers.extend(matches)
    except Exception as e:
        print(f"Error reading xlsx: {e}")
    return numbers

# ✅ .txt থেকে নাম্বার
def extract_numbers_from_txt(file_path: str):
    numbers = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            numbers = extract_numbers_from_text(text)
    except Exception as e:
        print(f"Error reading txt: {e}")
    return numbers

# ✅ /start হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 নম্বর দিন (টেক্সট বা .txt/.xlsx ফাইল) — আমি + এবং t.me/+ ফরম্যাটে ফাইল পাঠাবো।"
    )

# ✅ নাম্বার লিস্ট ইনপুট (টেক্সট)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    numbers = extract_numbers_from_text(update.message.text)

    if not numbers:
        await update.message.reply_text("❗ বৈধ নাম্বার খুঁজে পাইনি।")
        return

    await send_number_files(update, numbers)

# ✅ ডকুমেন্ট হ্যান্ডলার (.txt, .xlsx)
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc: Document = update.message.document

    if not doc:
        return

    if not (doc.file_name.endswith(".txt") or doc.file_name.endswith(".xlsx")):
        await update.message.reply_text("❗ শুধুমাত্র .txt অথবা .xlsx ফাইল দিন।")
        return

    file = await doc.get_file()
    file_path = os.path.join(OUTPUT_DIR, doc.file_name)
    await file.download_to_drive(file_path)

    if doc.file_name.endswith(".txt"):
        numbers = extract_numbers_from_txt(file_path)
    else:
        numbers = extract_numbers_from_xlsx(file_path)

    if not numbers:
        await update.message.reply_text("❗ ফাইল থেকে কোন বৈধ নাম্বার খুঁজে পাইনি।")
        return

    await send_number_files(update, numbers)

# ✅ আউটপুট ফাইল বানানো ও পাঠানো
async def send_number_files(update: Update, numbers: list):
    plus_file = get_next_filename("evan")
    tme_file = get_next_filename("evan")

    if "_0" in tme_file:
        tme_file = tme_file.replace("_0", "_1")
    elif ".txt" in tme_file:
        base, ext = tme_file.rsplit(".", 1)
        tme_file = f"{base}_1.{ext}"

    plus_list = [f"+{n}" for n in numbers]
    tme_list = [f"t.me/+{n}" for n in numbers]

    with open(plus_file, "w") as f:
        f.write("\n".join(plus_list))

    with open(tme_file, "w") as f:
        f.write("\n".join(tme_list))

    await update.message.reply_text("✅ তৈরি করা হয়েছে, নিচে ফাইল 👇")
    await update.message.reply_document(open(plus_file, "rb"), filename=os.path.basename(plus_file))
    await update.message.reply_document(open(tme_file, "rb"), filename=os.path.basename(tme_file))

# ✅ Webhook handler (Flask endpoint)
@app.route(f"/{BOT_USERNAME}", methods=["POST"])
async def webhook_handler():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        await application.update_queue.put(update)
        return "ok"

# ✅ Root endpoint
@app.route("/")
def root():
    return "🚀 Bot is running!"

# ✅ Telegram bot handlers
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

# ✅ Webhook set
async def set_webhook():
    await bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_USERNAME}")

if __name__ == "__main__":
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
