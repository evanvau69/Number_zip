import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.ext import Dispatcher
import asyncio

TOKEN = os.environ.get("BOT_TOKEN")  # Render-এ Environment Variable
BOT_USERNAME = os.environ.get("BOT_USERNAME")  # eg: my_bot (no @)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # eg: https://your-render-url.onrender.com

OUTPUT_DIR = "output_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
bot = Bot(TOKEN)

# 🔁 ফাইল নাম জেনারেটর
def get_next_filename(prefix: str):
    i = 0
    while True:
        name = f"{prefix}{'_' + str(i) if i else ''}.txt"
        full_path = os.path.join(OUTPUT_DIR, name)
        if not os.path.exists(full_path):
            return full_path
        i += 1

# 🔹 /start হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 নম্বর দিন লাইন ধরে। আমি + এবং t.me/+ ফরম্যাটে আলাদা ফাইল বানিয়ে দেব।")

# 🔹 ইউজার নাম্বার দিলে ফাইল বানিয়ে পাঠানো হবে
async def handle_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    numbers = [line.strip() for line in update.message.text.strip().splitlines() if line.strip().isdigit()]

    if not numbers:
        await update.message.reply_text("❗ শুধু সংখ্যা (digits) যুক্ত নাম্বার দিন।")
        return

    plus_formatted = [f"+{num}" for num in numbers]
    tme_formatted = [f"t.me/+{num}" for num in numbers]

    # evan.txt, evan_1.txt, evan_2.txt, evan_3.txt …
    plus_file = get_next_filename("evan")
    tme_file = get_next_filename("evan")

    # প্রথম ফাইল => + নম্বর
    with open(plus_file, "w") as f:
        f.write("\n".join(plus_formatted))

    # দ্বিতীয় ফাইল => t.me/+ নম্বর (next available file)
    if "_0" in tme_file:
        tme_file = tme_file.replace("_0", "_1")
    elif ".txt" in tme_file:
        base, ext = tme_file.rsplit(".", 1)
        tme_file = f"{base}_1.{ext}"

    with open(tme_file, "w") as f:
        f.write("\n".join(tme_formatted))

    await update.message.reply_text("✅ নিচে আপনার ফাইল দুটি 👇")
    await update.message.reply_document(document=open(plus_file, "rb"), filename=os.path.basename(plus_file))
    await update.message.reply_document(document=open(tme_file, "rb"), filename=os.path.basename(tme_file))

# 🔹 Flask endpoint to handle Webhook
@app.route(f"/{BOT_USERNAME}", methods=["POST"])
async def webhook_handler():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        await application.update_queue.put(update)
        return "ok"

# 🔹 Flask root test
@app.route("/")
def root():
    return "✅ Bot is alive."

# 🔹 অ্যাপ্লিকেশন সেটআপ
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_numbers))

# 🔹 Startup hook (set webhook)
async def set_webhook():
    await bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_USERNAME}")

if __name__ == "__main__":
    # Run the webhook setup
    asyncio.run(set_webhook())
    # Start Flask app
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
