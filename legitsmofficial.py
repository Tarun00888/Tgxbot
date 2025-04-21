import logging
import aiohttp
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ========== CONFIG ==========
BOT_TOKEN = "7339654160:AAG7gdROmpBR8xX_GyFOSw9jOK1Zp6QKBKI"
ADMIN_ID = 5335667019
QR_IMAGE_URL = "https://ibb.co/rfz2VV93"
API_URL = "https://worldofsmm.com/api/v2"
API_KEY = "819cdbe4bc4f6af481ea23b17e09d4c3"

SERVICE_IDS = {
    "followers": 5710,
    "likes": 2441,
    "views": 5490
}

PRICING = {
    "followers": {"100": 40, "200": 70, "500": 150, "1K": 250, "2K": 450, "5K": 1100, "10K": 2100},
    "likes":     {"100": 15, "200": 25, "500": 50, "1K": 80,  "2K": 150, "5K": 300, "10K": 550},
    "views":     {"10K": 110, "50K": 300, "100K": 500, "200K": 950, "500K": 1600}
}
# ============================

user_sessions = {}
user_balances = {}

logging.basicConfig(level=logging.INFO)

# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🛍️ Services", callback_data="services")]
    ]
    await update.message.reply_text(
        "Welcome to <b>LegitSM Bot!</b>\n\nPlease use the buttons below to access services or manage your wallet.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if query.data == "balance":
        balance = user_balances.get(user_id, 0)
        await query.edit_message_text("Scan the QR code below to make a payment. Once done, send the payment screenshot here:")
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=QR_IMAGE_URL,
            caption=f"✅ <b>Your Current Balance:</b> ₹{balance}\n\nAfter making the payment, please send a screenshot for verification.\n\n<b>Contact Admin:</b> @legitxsm\n<b>Processing Time:</b> 30–60 minutes.",
            parse_mode="HTML"
        )

    elif query.data == "services":
        keyboard = [[InlineKeyboardButton("📸 Instagram", callback_data="instagram")]]
        await query.edit_message_text("Choose a platform:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "instagram":
        keyboard = [
            [InlineKeyboardButton("👥 Followers", callback_data="followers")],
            [InlineKeyboardButton("❤️ Likes", callback_data="likes")],
            [InlineKeyboardButton("▶️ Views", callback_data="views")],
        ]
        await query.edit_message_text("Select a service:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data in ["followers", "likes", "views"]:
        user_sessions[user_id] = {"service": query.data}
        options = list(PRICING[query.data].keys())
        keyboard = [
            [InlineKeyboardButton(qty, callback_data=f"qty_{qty}") for qty in options[i:i+2]]
            for i in range(0, len(options), 2)
        ]
        await query.edit_message_text("Choose a quantity:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("qty_"):
        qty = query.data.split("_")[1]
        user_sessions[user_id]["quantity"] = qty
        user_sessions[user_id]["waiting_url"] = True
        await query.edit_message_text("Please send the Instagram link for your order:")

    elif query.data == "confirm":
        data = user_sessions.get(user_id, {})
        service = data["service"]
        quantity = int(data["quantity"].replace("K", "000"))
        link = data["url"]
        price = PRICING[service][data["quantity"]]
        balance = user_balances.get(user_id, 0)

        if balance >= price:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, data={
                    "key": API_KEY,
                    "action": "add",
                    "service": SERVICE_IDS[service],
                    "link": link,
                    "quantity": quantity
                }) as resp:
                    result = await resp.json()
                    if "order" in result:
                        user_balances[user_id] -= price
                        await query.edit_message_text("✅ Your order has been successfully placed!")
                        await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=(
                                f"🆕 <b>New Order Received</b>\n"
                                f"👤 User ID: <code>{user_id}</code>\n"
                                f"🔧 Service: {service}\n"
                                f"🔢 Quantity: {data['quantity']}\n"
                                f"🔗 Link: {link}\n"
                                f"💸 Cost: ₹{price}\n"
                                f"🧾 Order ID: {result['order']}"
                            ),
                            parse_mode="HTML"
                        )
                    else:
                        await query.edit_message_text("❌ Failed to place the order. Please try again later.")
        else:
            await query.edit_message_text("❌ Insufficient balance. Please top up your wallet to continue.")

    elif query.data == "cancel":
        await query.edit_message_text("❌ Order has been cancelled.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    msg = update.message.text

    if user_id in user_sessions and user_sessions[user_id].get("waiting_url"):
        user_sessions[user_id]["url"] = msg
        data = user_sessions[user_id]
        price = PRICING[data["service"]][data["quantity"]]
        balance = user_balances.get(user_id, 0)

        confirm_text = (
            f"✅ <b>Order Summary</b>\n"
            f"🔧 Service: {data['service'].capitalize()}\n"
            f"🔢 Quantity: {data['quantity']}\n"
            f"🔗 Link: {data['url']}\n"
            f"💸 Cost: ₹{price}\n"
            f"💰 Your Balance: ₹{balance}\n\n"
            f"Would you like to confirm this order?"
        )
        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]]
        await update.message.reply_text(confirm_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        user_sessions[user_id]["waiting_url"] = False

    elif update.message.photo:
        caption = (
            f"🧾 <b>New Payment Screenshot</b>\n"
            f"👤 User ID: <code>{user_id}</code>"
        )
        await update.message.forward(chat_id=ADMIN_ID)
        await context.bot.send_message(chat_id=ADMIN_ID, text=caption, parse_mode="HTML")
        await update.message.reply_text(
            "✅ Your screenshot has been sent to the admin for verification.\n\n"
            "You’ll receive balance update within 30–60 minutes.\n"
            "For help, contact @legitxsm"
        )
    else:
        await update.message.reply_text("Please use the menu buttons or send your payment screenshot for top-up.")

# ========== ADMIN COMMAND ==========
async def addfund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized access.")
        return

    try:
        user_id, amount = context.args[0], float(context.args[1])
        user_balances[user_id] = user_balances.get(user_id, 0) + amount

        await update.message.reply_text(f"✅ ₹{amount} added to user {user_id}'s wallet.")
        await context.bot.send_message(chat_id=int(user_id), text=f"💰 ₹{amount} has been added to your wallet by admin.")
    except:
        await update.message.reply_text("Usage: /addfund user_id amount")

# ========== RUN ==========
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addfund", addfund))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_text))

    app.run_polling()

if __name__ == "__main__":
    main()