import requests
from bs4 import BeautifulSoup
import time
import telebot
import json  # For saving and loading data

# Telegram bot settings
TELEGRAM_TOKEN = '7900327558:AAGoembIo63sosbZmaa8XlZn3f2y51Q387M'
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# File to store tracked products
TRACKED_PRODUCTS_FILE = "tracked_products.json"
USERS_FILE = "users.json"  # File to store users who got the welcome message

# Load tracked products from file
def load_tracked_products():
    try:
        with open(TRACKED_PRODUCTS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save tracked products to file
def save_tracked_products():
    with open(TRACKED_PRODUCTS_FILE, "w") as file:
        json.dump(tracked_products, file)

# Load user data
def load_users():
    try:
        with open(USERS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save user data
def save_users():
    with open(USERS_FILE, "w") as file:
        json.dump(users, file)

# Storing tracking URLs and prices
tracked_products = load_tracked_products()
users = load_users()

# Logging function (only for server logs)
def log_message(message):
    print(message)  # ✅ Only prints on the server, does NOT send to Telegram

# Send notification to Telegram
def send_telegram_message(chat_id, message):
    bot.send_message(chat_id, message, parse_mode="Markdown", disable_web_page_preview=True)

# Handle unknown messages and first-time user
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_unknown(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Inline button for /help
    keyboard = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton("ℹ Show Commands", callback_data="help")
    keyboard.add(help_button)

    if str(user_id) not in users:
        users[str(user_id)] = True
        save_users()

        bot.send_message(
            chat_id,
            "👋 *Welcome!*\n\n"
            "📢 This bot helps you track Flipkart/Amazon product prices.\n"
            "⚡ Click below to see available commands.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        bot.send_message(
            chat_id,
            "⚠ *Unknown command!*\n\n"
            "💡 Click below to see all available commands:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

# Handle all button clicks (callbacks)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "help":
        handle_help(call.message)
    elif call.data == "add":
        handle_add(call.message)
    elif call.data == "list":
        handle_list(call.message)
    elif call.data == "stop":
        handle_stop(call.message)

# Help command
@bot.message_handler(commands=['help'])
def handle_help(message):
    chat_id = message.chat.id
    keyboard = telebot.types.InlineKeyboardMarkup()
    
    keyboard.add(telebot.types.InlineKeyboardButton("➕ Add Product", callback_data="add"))
    keyboard.add(telebot.types.InlineKeyboardButton("📜 Show Tracked Products", callback_data="list"))
    keyboard.add(telebot.types.InlineKeyboardButton("❌ Stop Tracking", callback_data="stop"))

    help_text = "🛠 *Available Commands:*\n\n" \
                "➕ `/add` - Track a new product\n" \
                "📜 `/list` - View all tracked items\n" \
                "❌ `/stop` - Remove a product from tracking\n" \
                "ℹ `/help` - Show this help message"

    bot.send_message(chat_id, help_text, reply_markup=keyboard, parse_mode="Markdown")

# ✅ **Fix: handle_add function added**
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

    save_tracked_products()  # ✅ Data saved in JSON file
    bot.send_message(chat_id, f"✅ Now tracking [{url}]({url}) for price drops below *₹{min_price}*.", parse_mode="Markdown")
    log_message(f"🔍 Tracking started for {url} at ₹{min_price}")

# ✅ **Fix: handle_list function added**
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

# ✅ **Fix: handle_stop function added**
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
        save_tracked_products()  # ✅ Data removed from JSON file
        bot.send_message(chat_id, f"🛑 Stopped tracking [{url}]({url}).", parse_mode="Markdown")
        log_message(f"❌ Stopped tracking {url}")
    else:
        bot.send_message(chat_id, "⚠ *This product is not in the tracking list.*", parse_mode="Markdown")

# Auto-restart bot if connection fails
def start_bot():
    while True:
        try:
            log_message("🚀 Bot Started... Listening for messages!")
            bot.polling(none_stop=True, timeout=30)
        except requests.exceptions.ConnectionError:
            log_message("❌ Internet connection lost! Retrying in 5 seconds...")
            time.sleep(5)
        except telebot.apihelper.ApiException as e:
            log_message(f"⚠ Telegram API Error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            log_message(f"⚠ Unexpected error: {e}")
            log_message("🔄 Restarting bot in 5 seconds...")
            time.sleep(5)  # Wait before retrying to avoid spam requests

# Run the bot
start_bot()
