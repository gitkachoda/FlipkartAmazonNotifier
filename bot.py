import requests
from bs4 import BeautifulSoup
import time
import telebot
from threading import Thread
import json  # For saving and loading data

# Telegram bot settings
TELEGRAM_TOKEN = '7900327558:AAGoembIo63sosbZmaa8XlZn3f2y51Q387M'
TELEGRAM_CHAT_ID = '6552591095'
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# File to store tracked products
TRACKED_PRODUCTS_FILE = "tracked_products.json"

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

# Storing tracking URLs and prices
tracked_products = load_tracked_products()

# Logging function (only for server logs)
def log_message(message):
    print(message)  # ✅ Only prints on the server, does NOT send to Telegram

# Send notification to Telegram
def send_telegram_message(chat_id, message):
    bot.send_message(chat_id, message, parse_mode="Markdown", disable_web_page_preview=True)

# Function to fetch price from Flipkart
def fetch_price(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, timeout=5, headers=headers)
        content = BeautifulSoup(res.content, "html.parser")

        price_div = content.find('div', class_='_30jeq3 _16Jk6d')  # Flipkart price class
        if price_div:
            return int(price_div.text.replace("₹", "").replace(",", "").strip())
        else:
            return None  # Price not found

    except Exception as e:
        log_message(f"⚠ Error fetching price: {e}")
        return None

# Continuous price monitoring (runs every 1 min)
def price_monitor():
    while True:
        if not tracked_products:
            log_message("📌 No products are being tracked right now.")  # ✅ Only server log
        else:
            for url, (min_price, chat_id) in tracked_products.items():
                price = fetch_price(url)
                if price:
                    if price <= min_price:
                        message = f"🔥 *Price Drop Alert!*\n💰 *New Price:* ₹{price}\n🎯 *Target Price:* ₹{min_price}\n🔗 [Check Product]({url})"
                        send_telegram_message(chat_id, message)

        log_message("⏳ Refreshing in 1 minute...")  # ✅ Only server log
        time.sleep(60)  # 1-minute wait

# Start price monitoring in a separate thread
monitor_thread = Thread(target=price_monitor, daemon=True)
monitor_thread.start()

# Handling callback queries (for inline buttons)
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id

    if call.data == "add":
        handle_add(call.message)
    elif call.data == "list":
        handle_list(call.message)
    elif call.data == "stop":
        handle_stop(call.message)
    elif call.data == "help":
        handle_help(call.message)

    # **Dismissing the inline buttons immediately after click**
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

# Telegram bot commands
@bot.message_handler(commands=['add'])
def handle_add(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📌 *Send the Flipkart product link to track:*", parse_mode="Markdown")
    bot.register_next_step_handler(message, handle_url)

def handle_url(message):
    chat_id = message.chat.id
    url = message.text.strip()

    if not url.startswith('http'):
        bot.send_message(chat_id, "⚠ *Invalid URL! Please send a valid Flipkart product link.*", parse_mode="Markdown")
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

# Show list of tracking products
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

# Stop tracking a product
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

# Help command with dismissable buttons
@bot.message_handler(commands=['help'])
def handle_help(message):
    chat_id = message.chat.id
    keyboard = telebot.types.InlineKeyboardMarkup()
    
    keyboard.add(telebot.types.InlineKeyboardButton("➕ Add Product", callback_data="add"))
    keyboard.add(telebot.types.InlineKeyboardButton("📜 Show Tracked Products", callback_data="list"))
    keyboard.add(telebot.types.InlineKeyboardButton("❌ Stop Tracking", callback_data="stop"))
    keyboard.add(telebot.types.InlineKeyboardButton("ℹ Help", callback_data="help"))

    help_text = "🛠 *Available Commands:*\n\n" \
                "➕ Click 'Add Product' to track a new item\n" \
                "📜 Click 'Show Tracked Products' to view all tracked items\n" \
                "❌ Click 'Stop Tracking' to remove a product\n" \
                "ℹ Click 'Help' to see this message again"

    bot.send_message(chat_id, help_text, reply_markup=keyboard, parse_mode="Markdown")

# Start bot
log_message("🚀 Bot Started...")  # ✅ Only server log
bot.polling()
