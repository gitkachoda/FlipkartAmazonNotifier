import os
import time
import threading
import logging
import requests
import telebot
from flask import Flask, jsonify
import json  # For saving and loading data

# ✅ Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("server_logs.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ✅ Load environment variables for deployment
TOKEN = os.getenv("BOT_TOKEN", "7900327558:AAGoembIo63sosbZmaa8XlZn3f2y51Q387M")
CHAT_ID = int(os.getenv("CHAT_ID", "1289304344"))
PORT = int(os.getenv("PORT", 5000))

bot = telebot.TeleBot(TOKEN)

# ✅ Flask Server Setup
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "Bot is running!", "tracked_products": len(tracked_products)})

@app.route("/keep_alive")
def keep_alive():
    logger.info("✅ Keep-alive ping received")
    return jsonify({"message": "Bot is active!"})

# ✅ Keep Bot Alive Every 10 Minutes
def keep_bot_alive():
    while True:
        try:
            requests.get(f"http://127.0.0.1:{PORT}/keep_alive")  # Internal request to keep Flask active
        except Exception as e:
            logger.warning(f"⚠ Keep-alive failed: {e}")
        time.sleep(600)  # 10-minute interval

# ✅ Load tracked products
TRACKED_PRODUCTS_FILE = "tracked_products.json"
USERS_FILE = "users.json"

def load_tracked_products():
    try:
        with open(TRACKED_PRODUCTS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_tracked_products():
    with open(TRACKED_PRODUCTS_FILE, "w") as file:
        json.dump(tracked_products, file)

def load_users():
    try:
        with open(USERS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_users():
    with open(USERS_FILE, "w") as file:
        json.dump(users, file)

tracked_products = load_tracked_products()
users = load_users()

# ✅ Send notification to Telegram
def send_telegram_message(chat_id, message):
    bot.send_message(chat_id, message, parse_mode="Markdown", disable_web_page_preview=True)

# ✅ Handle Bot Commands
@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    chat_id = message.chat.id
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("➕ Add Product", "📜 Show Tracked Products", "❌ Stop Tracking")
    bot.send_message(
        chat_id,
        "🛠 *Available Commands:*\n"
        "➕ `/add` - Track a new product\n"
        "📜 `/list` - View all tracked items\n"
        "❌ `/stop` - Remove a product from tracking\n"
        "ℹ `/help` - Show this help message",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['add'])
def handle_add(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📌 *Send the Flipkart/Amazon product link to track:*", parse_mode="Markdown")
    bot.register_next_step_handler(message, handle_url)

def handle_url(message):
    chat_id = message.chat.id
    url = message.text.strip()

    if not url.startswith('http'):
        bot.send_message(chat_id, "⚠ *Invalid URL! Please send a valid Flipkart/Amazon product link.*", parse_mode="Markdown")
        return

    bot.send_message(chat_id, "💰 *Enter the minimum price (in ₹) for alerts:*", parse_mode="Markdown")
    bot.register_next_step_handler(message, handle_min_price, url)

def handle_min_price(message, url):
    chat_id = message.chat.id

    if not message.text.isdigit():
        bot.send_message(chat_id, "⚠ *Invalid price! Please enter a numeric value.*", parse_mode="Markdown")
        return

    min_price = int(message.text.strip())
    tracked_products[url] = (min_price, chat_id)

    save_tracked_products()
    bot.send_message(chat_id, f"✅ Now tracking [{url}]({url}) for price drops below *₹{min_price}*.", parse_mode="Markdown")

@bot.message_handler(commands=['list'])
def handle_list(message):
    chat_id = message.chat.id
    if not tracked_products:
        bot.send_message(chat_id, "🔍 *No products are being tracked right now.*", parse_mode="Markdown")
    else:
        msg = "📌 *Currently Tracking:*\n\n"
        for url, (min_price, _) in tracked_products.items():
            msg += f"🔹 [{url}]({url}) - Below *₹{min_price}*\n"
        bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "❌ *Send the product link you want to stop tracking:*", parse_mode="Markdown")
    bot.register_next_step_handler(message, handle_remove_url)

def handle_remove_url(message):
    chat_id = message.chat.id
    url = message.text.strip()

    if url in tracked_products:
        del tracked_products[url]
        save_tracked_products()
        bot.send_message(chat_id, f"🛑 Stopped tracking [{url}]({url}).", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "⚠ *This product is not in the tracking list.*", parse_mode="Markdown")

# ✅ Handle Unknown Commands
@bot.message_handler(func=lambda message: True)
def handle_invalid_command(message):
    chat_id = message.chat.id
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("➕ Add Product", "📜 Show Tracked Products", "❌ Stop Tracking")

    help_text = (
        "⚠ *Invalid command!*\n\n"
        "🛠 *Available Commands:*\n"
        "➕ `/add` - Track a new product\n"
        "📜 `/list` - View all tracked items\n"
        "❌ `/stop` - Remove a product from tracking\n"
        "ℹ `/help` - Show this help message"
    )

    bot.send_message(chat_id, help_text, parse_mode="Markdown", reply_markup=keyboard)

# ✅ Auto-Restarting Bot
def start_bot():
    while True:
        try:
            logger.info("🚀 Bot Started... Listening for messages!")
            bot.polling(none_stop=True, timeout=30)
        except requests.exceptions.ConnectionError:
            logger.warning("⚠ Internet lost! Retrying in 5 seconds...")
            time.sleep(5)
        except telebot.apihelper.ApiException as e:
            logger.warning(f"⚠ Telegram API Error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.warning(f"⚠ Unexpected error: {e}")
            time.sleep(5)

# ✅ Run Flask & Bot in Parallel
if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    threading.Thread(target=keep_bot_alive, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
