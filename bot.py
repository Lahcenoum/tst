import sys
import subprocess
import random
import string
import sqlite3
import re
import traceback
import html
from datetime import datetime, date, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from telegram.constants import ParseMode
from telegram.error import BadRequest

# =================================================================================
# 1. الإعدادات الرئيسية (Configuration)
# =================================================================================
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ADMIN_USER_ID = 5344028088
ADMIN_CONTACT_INFO = "@YourAdminUsername" 

SCRIPT_PATH = '/usr/local/bin/create_ssh_user.sh'
DB_FILE = 'ssh_bot_users.db'

# --- قيم نظام النقاط ---
COST_PER_ACCOUNT = 4
DAILY_LOGIN_BONUS = 1
INITIAL_POINTS = 2
JOIN_BONUS = 4
ACCOUNT_EXPIRY_DAYS = 2

# Channel and Group links and IDs (for force join)
REQUIRED_CHANNEL_ID = -1001932589296
REQUIRED_GROUP_ID = -1002218671728
CHANNEL_LINK = "https://t.me/FASTVPSVIP"
GROUP_LINK = "https://t.me/dgtliA"

# Conversation handler states
(ADD_CHANNEL_NAME, ADD_CHANNEL_LINK, ADD_CHANNEL_ID, ADD_CHANNEL_POINTS) = range(4)
(CREATE_CODE_NAME, CREATE_CODE_POINTS, CREATE_CODE_USES) = range(4, 7)
(REDEEM_CODE_INPUT,) = range(7, 8)
(EDIT_HOSTNAME, EDIT_WS_PORTS, EDIT_SSL_PORT, EDIT_UDPCUSTOM, EDIT_ADMIN_CONTACT, EDIT_PAYLOAD) = range(8, 14)

# =================================================================================
# 2. دعم اللغات (Localization)
# =================================================================================
TEXTS = {
    'ar': {
        "welcome": "أهلاً بك في بوت خدمة SSH!\n\nاستخدم الأزرار أدناه للتفاعل أو غير لغتك بالأمر /language.",
        "get_ssh_button": "💳 طلب حساب جديد",
        "my_account_button": "👤 حسابي",
        "balance_button": "💰 رصيدي",
        "earn_points_button": "🎁 كسب النقاط",
        "redeem_code_button": "🎁 استرداد كود",
        "daily_button": "☀️ مكافأة يومية",
        "contact_admin_button": "👨‍💻 تواصل مع الأدمن",
        "contact_admin_info": "للتواصل مع الأدمن، يرجى مراسلة: {contact_info}",
        "not_enough_points": "⚠️ ليس لديك نقاط كافية. التكلفة هي <b>{cost}</b> نقطة.",
        "creation_error": "❌ حدث خطأ أثناء إنشاء الحساب. قد يكون لديك حساب بالفعل أو خطأ آخر.",
        "creation_wait": "⏳ لا يمكنك إنشاء حساب جديد الآن. يرجى الانتظار <b>{time_left}</b>.",
        "force_join_prompt": "❗️لاستخدام البوت، يجب عليك الانضمام إلى قناتنا ومجموعتنا أولاً.\n\nبعد الانضمام، اضغط على زر '✅ تحققت'.",
        "force_join_channel_button": "📢 انضم للقناة",
        "force_join_group_button": "👥 انضم للمجموعة",
        "force_join_verify_button": "✅ تحققت",
        "force_join_success": "✅ شكرًا لانضمامك! يمكنك الآن استخدام البوت.",
        "force_join_fail": "❌ لم يتم التحقق من انضمامك. يرجى التأكد من انضمامك لكليهما والمحاولة مرة أخرى.",
        "join_bonus_awarded": "🎉 مكافأة الانضمام! لقد حصلت على {bonus} نقطة.",
        "balance_info": "💰 رصيدك الحالي هو: <b>{points}</b> نقطة.",
        "daily_bonus_claimed": "🎉 لقد حصلت على مكافأتك اليومية: <b>{bonus}</b> نقطة! رصيدك الآن هو <b>{new_balance}</b>.",
        "daily_bonus_already_claimed": "ℹ️ لقد حصلت بالفعل على مكافأتك اليومية. تعال غدًا!",
        "no_accounts_found": "ℹ️ لم يتم العثور على أي حسابات نشطة مرتبطة بك.",
        "your_accounts": "<b>👤 حساباتك النشطة:</b>",
        "account_details_full": "🏷️ <b>اسم المستخدم:</b> <code>{username}</code>\n🔑 <b>كلمة المرور:</b> <code>{password}</code>\n🗓️ <b>تاريخ انتهاء الصلاحية:</b> <code>{expiry}</code>\n\n<b>Hostname:</b> <code>{hostname}</code>\n<b>Websocket Ports:</b> <code>{ws_ports}</code>\n<b>SSL Port:</b> <code>{ssl_port}</code>\n<b>UDPCUSTOM Port:</b> <code>{udpcustom_port}</code>\n\n<b>Payload:</b>\n<pre><code>{payload}</code></pre>",
        "rewards_header": "انضم إلى هذه القنوات والمجموعات واحصل على نقاط!",
        "verify_join_button": "✅ تحقق من الانضمام",
        "reward_success": "🎉 رائع! لقد حصلت على {points} نقطة.",
        "reward_fail": "❌ لم تنضم بعد. حاول مرة أخرى بعد الانضمام.",
        "no_channels_available": "ℹ️ لا توجد قنوات متاحة للمكافآت حاليًا.",
        "redeem_prompt": "يرجى إرسال الكود الذي تريد استرداده.",
        "redeem_success": "🎉 تهانينا! لقد حصلت على <b>{points}</b> نقطة. رصيدك الآن هو <b>{new_balance}</b>.",
        "redeem_invalid_code": "❌ هذا الكود غير صالح أو غير موجود.",
        "redeem_limit_reached": "❌ لقد وصل هذا الكود إلى الحد الأقصى من الاستخدام.",
        "redeem_already_used": "❌ لقد قمت بالفعل باستخدام هذا الكود.",
        "admin_panel_header": "⚙️ لوحة تحكم الأدمن",
        "admin_return_button": "⬅️ عودة",
        "admin_manage_rewards_button": "📢 إدارة قنوات الربح",
        "admin_manage_codes_button": "🎁 إدارة أكواد الهدايا",
        "admin_user_stats_button": "📊 إحصائيات المستخدمين",
        "admin_edit_connection_info_button": "⚙️ تعديل معلومات الاتصال",
        "admin_add_channel_button": "➕ إضافة قناة/مجموعة",
        "admin_remove_channel_button": "➖ إزالة قناة/مجموعة",
        "admin_add_channel_name_prompt": "أرسل اسم القناة:",
        "admin_add_channel_link_prompt": "الآن أرسل رابط القناة الكامل:",
        "admin_add_channel_id_prompt": "أرسل معرف القناة الرقمي (يبدأ بـ -100):",
        "admin_add_channel_points_prompt": "أخيراً، أرسل عدد نقاط المكافأة:",
        "admin_channel_added_success": "✅ تم إضافة القناة بنجاح.",
        "admin_remove_channel_prompt": "اختر القناة التي تريد إزالتها:",
        "admin_channel_removed_success": "🗑️ تم إزالة القناة بنجاح.",
        "admin_create_code_button": "➕ إنشاء كود جديد",
        "admin_create_code_prompt_name": "أرسل اسم الكود الجديد (مثال: WELCOME2025):",
        "admin_create_code_prompt_points": "الآن أرسل عدد النقاط التي يمنحها هذا الكود:",
        "admin_create_code_prompt_uses": "أخيراً، أرسل عدد المستخدمين الذين يمكنهم استخدام هذا الكود:",
        "admin_code_created": "✅ تم إنشاء الكود <code>{code}</code> بنجاح. يمنح <b>{points}</b> نقطة ومتاح لـ <b>{uses}</b> مستخدمين.",
        "admin_edit_hostname_prompt": "أرسل الـ Hostname الجديد:",
        "admin_edit_ws_ports_prompt": "أرسل بورتات Websocket الجديدة (مثال: 80, 8880):",
        "admin_edit_ssl_port_prompt": "أرسل بورت SSL الجديد:",
        "admin_edit_udpcustom_prompt": "أرسل بورت UDPCUSTOM الجديد:",
        "admin_edit_contact_prompt": "أرسل معلومات التواصل الجديدة (مثال: @username):",
        "admin_edit_payload_prompt": "أخيراً، أرسل الـ Payload الجديد:",
        "admin_info_updated_success": "✅ تم تحديث معلومات الاتصال بنجاح.",
        "user_stats_info": "<b>📊 إحصائيات المستخدمين:</b>\n\n- <b>إجمالي المستخدمين:</b> {total_users}\n- <b>النشطون اليوم:</b> {active_today}\n- <b>النشطون أمس:</b> {active_yesterday}\n- <b>المستخدمون الجدد اليوم:</b> {new_today}",
        "choose_language": "اختر لغتك المفضلة:",
        "language_set": "✅ تم تعيين اللغة إلى: {lang_name}",
        "invalid_input": "❌ إدخال غير صالح، يرجى المحاولة مرة أخرى.",
        "operation_cancelled": "✅ تم إلغاء العملية.",
        "creating_account": "جاري إنشاء الحساب...",
        "points": "نقاط",
    },
    'en': {
        "welcome": "Welcome to the SSH Service Bot!\n\nUse the buttons below to interact or change your language with /language.",
        "get_ssh_button": "💳 Request New Account",
        "my_account_button": "👤 My Account",
        "balance_button": "💰 My Balance",
        "earn_points_button": "🎁 Earn Points",
        "redeem_code_button": "🎁 Redeem Code",
        "daily_button": "☀️ Daily Bonus",
        "contact_admin_button": "👨‍💻 Contact Admin",
        "contact_admin_info": "To contact the admin, please message: {contact_info}",
        "not_enough_points": "⚠️ You don't have enough points. The cost is <b>{cost}</b> points.",
        "creation_error": "❌ An error occurred while creating the account. You may already have an account or another error occurred.",
        "creation_wait": "⏳ You cannot create a new account right now. Please wait <b>{time_left}</b>.",
        "force_join_prompt": "❗️To use the bot, you must first join our channel and group.\n\nAfter joining, press the '✅ Verified' button.",
        "force_join_channel_button": "📢 Join Channel",
        "force_join_group_button": "👥 Join Group",
        "force_join_verify_button": "✅ Verified",
        "force_join_success": "✅ Thank you for joining! You can now use the bot.",
        "force_join_fail": "❌ Your membership could not be verified. Please make sure you have joined both and try again.",
        "join_bonus_awarded": "🎉 Join bonus! You have received {bonus} points.",
        "balance_info": "💰 Your current balance is: <b>{points}</b> points.",
        "daily_bonus_claimed": "🎉 You've received your daily bonus: <b>{bonus}</b> points! Your new balance is <b>{new_balance}</b>.",
        "daily_bonus_already_claimed": "ℹ️ You have already claimed your daily bonus. Come back tomorrow!",
        "no_accounts_found": "ℹ️ No active accounts associated with you were found.",
        "your_accounts": "<b>👤 Your Active Accounts:</b>",
        "account_details_full": "🏷️ <b>Username:</b> <code>{username}</code>\n🔑 <b>Password:</b> <code>{password}</code>\n🗓️ <b>Expiration Date:</b> <code>{expiry}</code>\n\n<b>Hostname:</b> <code>{hostname}</code>\n<b>Websocket Ports:</b> <code>{ws_ports}</code>\n<b>SSL Port:</b> <code>{ssl_port}</code>\n<b>UDPCUSTOM Port:</b> <code>{udpcustom_port}</code>\n\n<b>Payload:</b>\n<pre><code>{payload}</code></pre>",
        "rewards_header": "Join these channels and groups to get points!",
        "verify_join_button": "✅ Verify Join",
        "reward_success": "🎉 Great! You've received {points} points.",
        "reward_fail": "❌ You haven't joined yet. Try again after joining.",
        "no_channels_available": "ℹ️ There are currently no channels available for rewards.",
        "redeem_prompt": "Please send the code you want to redeem.",
        "redeem_success": "🎉 Congratulations! You've received <b>{points}</b> points. Your new balance is <b>{new_balance}</b>.",
        "redeem_invalid_code": "❌ This code is invalid or does not exist.",
        "redeem_limit_reached": "❌ This code has reached its maximum usage limit.",
        "redeem_already_used": "❌ You have already used this code.",
        "admin_panel_header": "⚙️ Admin Control Panel",
        "admin_return_button": "⬅️ Back",
        "admin_manage_rewards_button": "📢 Manage Reward Channels",
        "admin_manage_codes_button": "🎁 Manage Gift Codes",
        "admin_user_stats_button": "📊 User Statistics",
        "admin_edit_connection_info_button": "⚙️ Edit Connection Info",
        "admin_add_channel_button": "➕ Add Channel/Group",
        "admin_remove_channel_button": "➖ Remove Channel/Group",
        "admin_add_channel_name_prompt": "Send the channel name:",
        "admin_add_channel_link_prompt": "Now send the full channel link:",
        "admin_add_channel_id_prompt": "Send the numeric channel ID (starts with -100):",
        "admin_add_channel_points_prompt": "Finally, send the number of reward points:",
        "admin_channel_added_success": "✅ Channel added successfully.",
        "admin_remove_channel_prompt": "Choose the channel you want to remove:",
        "admin_channel_removed_success": "🗑️ Channel removed successfully.",
        "admin_create_code_button": "➕ Create New Code",
        "admin_create_code_prompt_name": "Send the new code name (e.g., WELCOME2025):",
        "admin_create_code_prompt_points": "Now send the number of points this code grants:",
        "admin_create_code_prompt_uses": "Finally, send the number of users who can use this code:",
        "admin_code_created": "✅ Code <code>{code}</code> created successfully. It grants <b>{points}</b> points and is available for <b>{uses}</b> users.",
        "admin_edit_hostname_prompt": "Send the new Hostname:",
        "admin_edit_ws_ports_prompt": "Send the new Websocket ports (e.g., 80, 8880):",
        "admin_edit_ssl_port_prompt": "Send the new SSL port:",
        "admin_edit_udpcustom_prompt": "Send the new UDPCUSTOM port:",
        "admin_edit_contact_prompt": "Send the new contact info (e.g., @username):",
        "admin_edit_payload_prompt": "Finally, send the new Payload:",
        "admin_info_updated_success": "✅ Connection info updated successfully.",
        "user_stats_info": "<b>📊 User Statistics:</b>\n\n- <b>Total Users:</b> {total_users}\n- <b>Active Today:</b> {active_today}\n- <b>Active Yesterday:</b> {active_yesterday}\n- <b>New Today:</b> {new_today}",
        "choose_language": "Choose your preferred language:",
        "language_set": "✅ Language has been set to: {lang_name}",
        "invalid_input": "❌ Invalid input, please try again.",
        "operation_cancelled": "✅ Operation cancelled.",
        "creating_account": "Creating account...",
        "points": "points",
    },
}

def get_text(key, lang_code='ar'):
    return TEXTS.get(lang_code, TEXTS['en']).get(key, key)

# =================================================================================
# 3. إدارة قاعدة البيانات (Database Management)
# =================================================================================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS ssh_accounts (id INTEGER PRIMARY KEY, telegram_user_id INTEGER NOT NULL, ssh_username TEXT NOT NULL, ssh_password TEXT NOT NULL, created_at TIMESTAMP NOT NULL)')
        cursor.execute('CREATE TABLE IF NOT EXISTS users (telegram_user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, last_daily_claim DATE, join_bonus_claimed INTEGER DEFAULT 0, language_code TEXT DEFAULT "ar", created_date DATE)')
        cursor.execute('CREATE TABLE IF NOT EXISTS reward_channels (channel_id INTEGER PRIMARY KEY, channel_link TEXT NOT NULL, reward_points INTEGER NOT NULL, channel_name TEXT NOT NULL)')
        cursor.execute('CREATE TABLE IF NOT EXISTS user_channel_rewards (telegram_user_id INTEGER, channel_id INTEGER, PRIMARY KEY (telegram_user_id, channel_id))')
        cursor.execute('CREATE TABLE IF NOT EXISTS redeem_codes (code TEXT PRIMARY KEY, points INTEGER, max_uses INTEGER, current_uses INTEGER DEFAULT 0)')
        cursor.execute('CREATE TABLE IF NOT EXISTS redeemed_users (code TEXT, telegram_user_id INTEGER, PRIMARY KEY (code, telegram_user_id))')
        cursor.execute('CREATE TABLE IF NOT EXISTS daily_activity (user_id INTEGER PRIMARY KEY, last_seen_date DATE NOT NULL)')
        cursor.execute('CREATE TABLE IF NOT EXISTS connection_settings (key TEXT PRIMARY KEY, value TEXT)')
        
        default_settings = {
            "hostname": "your.hostname.com", "ws_ports": "80, 8880, 8888, 2053",
            "ssl_port": "443", "udpcustom_port": "7300", "admin_contact": ADMIN_CONTACT_INFO,
            "payload": "your.default.payload"
        }
        for key, value in default_settings.items():
            cursor.execute("INSERT OR IGNORE INTO connection_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()

def get_or_create_user(user_id, lang_code='ar'):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        if not cursor.execute("SELECT 1 FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone():
            today = date.today().isoformat()
            cursor.execute("INSERT INTO users (telegram_user_id, points, language_code, created_date) VALUES (?, ?, ?, ?)", (user_id, INITIAL_POINTS, lang_code, today))
            conn.commit()

def get_user_lang(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        res = conn.execute("SELECT language_code FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone()
        return res[0] if res else 'ar'

def set_user_lang(user_id, lang_code):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE users SET language_code = ? WHERE telegram_user_id = ?", (lang_code, user_id))
        conn.commit()

def get_connection_setting(key):
    with sqlite3.connect(DB_FILE) as conn:
        result = conn.execute("SELECT value FROM connection_settings WHERE key = ?", (key,)).fetchone()
        return result[0] if result else ""

def set_connection_setting(key, value):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT OR REPLACE INTO connection_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()

# =================================================================================
# 4. دوال مساعدة وديكورات (Helpers & Decorators)
# =================================================================================
def log_activity(func):
    """Decorator to log user activity for statistics."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        today = date.today().isoformat()
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT OR REPLACE INTO daily_activity (user_id, last_seen_date) VALUES (?, ?)", (user_id, today))
            conn.commit()
        return await func(update, context, *args, **kwargs)
    return wrapper

def generate_password():
    return "bot" + ''.join(random.choices(string.ascii_letters + string.digits, k=6))

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        channel_member = await context.bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        group_member = await context.bot.get_chat_member(REQUIRED_GROUP_ID, user_id)
        if channel_member.status not in ['member', 'administrator', 'creator']: return False
        if group_member.status not in ['member', 'administrator', 'creator']: return False
        return True
    except Exception as e:
        print(f"Error checking membership for {user_id}: {e}")
        return False

# =================================================================================
# 5. أوامر البوت الأساسية (Core Bot Commands)
# =================================================================================
@log_activity
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback: bool = False):
    user = update.effective_user
    message = update.message if not from_callback else update.callback_query.message
    get_or_create_user(user.id)
    lang_code = get_user_lang(user.id)

    if not await check_membership(user.id, context):
        keyboard = [
            [InlineKeyboardButton(get_text('force_join_channel_button', lang_code), url=CHANNEL_LINK)],
            [InlineKeyboardButton(get_text('force_join_group_button', lang_code), url=GROUP_LINK)],
            [InlineKeyboardButton(get_text('force_join_verify_button', lang_code), callback_data='verify_join')],
        ]
        await message.reply_text(get_text('force_join_prompt', lang_code), reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard_layout = [
        [KeyboardButton(get_text('get_ssh_button', lang_code))],
        [KeyboardButton(get_text('balance_button', lang_code)), KeyboardButton(get_text('my_account_button', lang_code))],
        [KeyboardButton(get_text('daily_button', lang_code)), KeyboardButton(get_text('earn_points_button', lang_code))],
        [KeyboardButton(get_text('redeem_code_button', lang_code)), KeyboardButton(get_text('contact_admin_button', lang_code))]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard_layout, resize_keyboard=True)
    await message.reply_text(get_text('welcome', lang_code), reply_markup=reply_markup)

@log_activity
async def get_ssh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Ensure user exists in DB before proceeding
    get_or_create_user(user_id) 
    lang_code = get_user_lang(user_id)
    
    with sqlite3.connect(DB_FILE) as conn:
        last_creation = conn.execute("SELECT MAX(created_at) FROM ssh_accounts WHERE telegram_user_id = ?", (user_id,)).fetchone()[0]
    
    if last_creation:
        last_creation_time = datetime.strptime(last_creation, '%Y-%m-%d %H:%M:%S.%f')
        if datetime.now() - last_creation_time < timedelta(hours=24):
            time_left = timedelta(hours=24) - (datetime.now() - last_creation_time)
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await update.message.reply_text(get_text('creation_wait', lang_code).format(time_left=f"{hours}h {minutes}m"), parse_mode=ParseMode.HTML)
            return

    await update.message.reply_text("⏳ " + get_text('creating_account', lang_code))

    with sqlite3.connect(DB_FILE) as conn:
        user_points = conn.execute("SELECT points FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone()[0]
    
    if user_points < COST_PER_ACCOUNT:
        await update.message.reply_text(get_text('not_enough_points', lang_code).format(cost=COST_PER_ACCOUNT), parse_mode=ParseMode.HTML)
        return

    try:
        username = f"sshdatbot{user_id}"
        password = generate_password()
        command_to_run = ["sudo", SCRIPT_PATH, username, password, str(ACCOUNT_EXPIRY_DAYS)]

        process = subprocess.run(command_to_run, capture_output=True, text=True, timeout=30, check=True)
        
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("UPDATE users SET points = points - ? WHERE telegram_user_id = ?", (COST_PER_ACCOUNT, user_id))
            conn.execute("INSERT INTO ssh_accounts (telegram_user_id, ssh_username, ssh_password, created_at) VALUES (?, ?, ?, ?)", (user_id, username, password, datetime.now()))
            conn.commit()

        result_details = process.stdout
        
        hostname = get_connection_setting("hostname")
        ws_ports = get_connection_setting("ws_ports")
        ssl_port = get_connection_setting("ssl_port")
        udpcustom_port = get_connection_setting("udpcustom_port")
        payload = get_connection_setting("payload")

        account_info = (
            f"<b>✅ تم إنشاء حسابك بنجاح!</b>\n\n"
            f"<b>البيانات الأساسية:</b>\n"
            f"<pre><code>{html.escape(result_details.strip())}</code></pre>\n\n"
            f"<b>Hostname:</b> <code>{html.escape(hostname)}</code>\n\n"
            f"<b> Websocket Ports:</b> <code>{html.escape(ws_ports)}</code>\n"
            f"<b> SSL Port:</b> <code>{html.escape(ssl_port)}</code>\n"
            f"<b> Websocket SSL Port:</b> <code>{html.escape(ssl_port)}</code>\n"
            f"<b> UDPCUSTOM Port:</b> <code>{html.escape(udpcustom_port)}</code>\n\n"
            f"<b>Payload:</b>\n<pre><code>{html.escape(payload)}</code></pre>\n\n"
            f"⚠️ <b>ملاحظة</b>: الحساب صالح لمستخدم واحد فقط للحفاظ على السرعة."
        )
        await update.message.reply_text(account_info, parse_mode=ParseMode.HTML)

    except Exception as e:
        print("--- AN UNEXPECTED ERROR OCCURRED ---"); traceback.print_exc()
        await update.message.reply_text(get_text('creation_error', lang_code))

@log_activity
async def my_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = get_user_lang(user_id)
    with sqlite3.connect(DB_FILE) as conn:
        accounts = conn.execute("SELECT ssh_username, ssh_password FROM ssh_accounts WHERE telegram_user_id = ?", (user_id,)).fetchall()
    
    if not accounts:
        await update.message.reply_text(get_text('no_accounts_found', lang_code)); return

    response_parts = [get_text('your_accounts', lang_code)]
    
    hostname = get_connection_setting("hostname")
    ws_ports = get_connection_setting("ws_ports")
    ssl_port = get_connection_setting("ssl_port")
    udpcustom_port = get_connection_setting("udpcustom_port")
    payload = get_connection_setting("payload")

    for username, password in accounts:
        try:
            expiry_output = subprocess.check_output(['/usr/bin/chage', '-l', username], text=True, stderr=subprocess.DEVNULL)
            expiry_line = next((line for line in expiry_output.split('\n') if "Account expires" in line), None)
            expiry = expiry_line.split(':', 1)[1].strip() if expiry_line else "N/A"
            
            account_info = get_text('account_details_full', lang_code).format(
                username=html.escape(username), 
                password=html.escape(password), 
                expiry=html.escape(expiry),
                hostname=html.escape(hostname),
                ws_ports=html.escape(ws_ports),
                ssl_port=html.escape(ssl_port),
                udpcustom_port=html.escape(udpcustom_port),
                payload=html.escape(payload)
            )
            response_parts.append(account_info)

        except Exception as e: 
            print(f"Could not get expiry for {username}: {e}")
            response_parts.append(f"Could not retrieve details for user <code>{html.escape(username)}</code>.")

    full_response = "\n\n---\n\n".join(response_parts)
    await update.message.reply_text(full_response, parse_mode=ParseMode.HTML)

@log_activity
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = get_user_lang(user_id)
    with sqlite3.connect(DB_FILE) as conn:
        points = conn.execute("SELECT points FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone()[0]
    await update.message.reply_text(get_text('balance_info', lang_code).format(points=points), parse_mode=ParseMode.HTML)

@log_activity
async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = get_user_lang(user_id)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        today = date.today()
        last_claim_str = cursor.execute("SELECT last_daily_claim FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone()[0]
        
        if last_claim_str and date.fromisoformat(last_claim_str) >= today:
            await update.message.reply_text(get_text('daily_bonus_already_claimed', lang_code)); return
            
        cursor.execute("UPDATE users SET points = points + ?, last_daily_claim = ? WHERE telegram_user_id = ?", (DAILY_LOGIN_BONUS, today.isoformat(), user_id))
        conn.commit()
        new_balance = cursor.execute("SELECT points FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone()[0]
        await update.message.reply_text(get_text('daily_bonus_claimed', lang_code).format(bonus=DAILY_LOGIN_BONUS, new_balance=new_balance), parse_mode=ParseMode.HTML)

@log_activity
async def contact_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = get_user_lang(update.effective_user.id)
    contact_info = get_connection_setting("admin_contact")
    await update.message.reply_text(get_text('contact_admin_info', lang_code).format(contact_info=contact_info))

@log_activity
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = get_user_lang(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data='set_lang_en')],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data='set_lang_ar')],
    ]
    await update.message.reply_text(get_text('choose_language', lang_code), reply_markup=InlineKeyboardMarkup(keyboard))

async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang_code = query.data.split('_')[-1]
    set_user_lang(user_id, lang_code)
    lang_map = {'en': 'English', 'ar': 'العربية'}
    await query.edit_message_text(text=get_text('language_set', lang_code).format(lang_name=lang_map.get(lang_code)))
    await start(update, context, from_callback=True)


# =================================================================================
# 6. Admin Panel & Features
# =================================================================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID: return
    lang_code = get_user_lang(user_id)
    keyboard = [
        [InlineKeyboardButton(get_text('admin_manage_rewards_button', lang_code), callback_data='admin_manage_rewards')],
        [InlineKeyboardButton(get_text('admin_manage_codes_button', lang_code), callback_data='admin_manage_codes')],
        [InlineKeyboardButton(get_text('admin_user_stats_button', lang_code), callback_data='admin_user_stats')],
        [InlineKeyboardButton(get_text('admin_edit_connection_info_button', lang_code), callback_data='admin_edit_connection_info')],
    ]
    await update.message.reply_text(get_text('admin_panel_header', lang_code), reply_markup=InlineKeyboardMarkup(keyboard))

async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = get_user_lang(query.from_user.id)
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    with sqlite3.connect(DB_FILE) as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_today = conn.execute("SELECT COUNT(*) FROM daily_activity WHERE last_seen_date = ?", (today,)).fetchone()[0]
        active_yesterday = conn.execute("SELECT COUNT(*) FROM daily_activity WHERE last_seen_date = ?", (yesterday,)).fetchone()[0]
        new_today = conn.execute("SELECT COUNT(*) FROM users WHERE created_date = ?", (today,)).fetchone()[0]
    
    stats_text = get_text('user_stats_info', lang_code).format(
        total_users=total_users,
        active_today=active_today,
        active_yesterday=active_yesterday,
        new_today=new_today
    )
    keyboard = [[InlineKeyboardButton(get_text('admin_return_button', lang_code), callback_data='admin_panel_main')]]
    await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID: return
    
    data = query.data
    lang_code = get_user_lang(user_id)
    
    if data == 'admin_panel_main':
        keyboard = [
            [InlineKeyboardButton(get_text('admin_manage_rewards_button', lang_code), callback_data='admin_manage_rewards')],
            [InlineKeyboardButton(get_text('admin_manage_codes_button', lang_code), callback_data='admin_manage_codes')],
            [InlineKeyboardButton(get_text('admin_user_stats_button', lang_code), callback_data='admin_user_stats')],
            [InlineKeyboardButton(get_text('admin_edit_connection_info_button', lang_code), callback_data='admin_edit_connection_info')],
        ]
        await query.edit_message_text(get_text('admin_panel_header', lang_code), reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == 'admin_manage_rewards':
        keyboard = [
            [InlineKeyboardButton(get_text('admin_add_channel_button', lang_code), callback_data='admin_add_channel_start')],
            [InlineKeyboardButton(get_text('admin_remove_channel_button', lang_code), callback_data='admin_remove_channel_start')],
            [InlineKeyboardButton(get_text('admin_return_button', lang_code), callback_data='admin_panel_main')]
        ]
        await query.edit_message_text(get_text('admin_manage_rewards_button', lang_code), reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == 'admin_manage_codes':
        keyboard = [
            [InlineKeyboardButton(get_text('admin_create_code_button', lang_code), callback_data='admin_create_code_start')],
            [InlineKeyboardButton(get_text('admin_return_button', lang_code), callback_data='admin_panel_main')]
        ]
        await query.edit_message_text(get_text('admin_manage_codes_button', lang_code), reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == 'admin_user_stats':
        await show_user_stats(update, context)

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    lang_code = get_user_lang(query.from_user.id)
    await query.edit_message_text(get_text('admin_add_channel_name_prompt', lang_code))
    return ADD_CHANNEL_NAME

async def add_channel_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['channel_name'] = update.message.text
    lang_code = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('admin_add_channel_link_prompt', lang_code))
    return ADD_CHANNEL_LINK

async def add_channel_get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['channel_link'] = update.message.text
    lang_code = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('admin_add_channel_id_prompt', lang_code))
    return ADD_CHANNEL_ID

async def add_channel_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = get_user_lang(update.effective_user.id)
    try:
        context.user_data['channel_id'] = int(update.message.text)
        await update.message.reply_text(get_text('admin_add_channel_points_prompt', lang_code))
        return ADD_CHANNEL_POINTS
    except ValueError:
        await update.message.reply_text(get_text('invalid_input', lang_code)); return ADD_CHANNEL_ID

async def add_channel_get_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = get_user_lang(update.effective_user.id)
    try:
        points = int(update.message.text)
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT OR REPLACE INTO reward_channels (channel_id, channel_link, reward_points, channel_name) VALUES (?, ?, ?, ?)",
                         (context.user_data['channel_id'], context.user_data['channel_link'], points, context.user_data['channel_name']))
        await update.message.reply_text(get_text('admin_channel_added_success', lang_code))
        context.user_data.clear()
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(get_text('invalid_input', lang_code)); return ADD_CHANNEL_POINTS

async def remove_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    lang_code = get_user_lang(query.from_user.id)
    with sqlite3.connect(DB_FILE) as conn:
        channels = conn.execute("SELECT channel_id, channel_name FROM reward_channels").fetchall()
    if not channels:
        await query.edit_message_text(get_text('no_channels_available', lang_code), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text('admin_return_button', lang_code), callback_data='admin_manage_rewards')]])); return
    keyboard = [[InlineKeyboardButton(name, callback_data=f"remove_c_{cid}")] for cid, name in channels]
    keyboard.append([InlineKeyboardButton(get_text('admin_return_button', lang_code), callback_data='admin_manage_rewards')])
    await query.edit_message_text(get_text('admin_remove_channel_prompt', lang_code), reply_markup=InlineKeyboardMarkup(keyboard))

async def remove_channel_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    lang_code = get_user_lang(query.from_user.id)
    channel_id = int(query.data.split('_')[-1])
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM reward_channels WHERE channel_id = ?", (channel_id,))
        conn.execute("DELETE FROM user_channel_rewards WHERE channel_id = ?", (channel_id,))
    await query.edit_message_text(get_text('admin_channel_removed_success', lang_code))
    await remove_channel_start(update, context)

async def create_code_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    lang_code = get_user_lang(query.from_user.id)
    await query.edit_message_text(get_text('admin_create_code_prompt_name', lang_code))
    return CREATE_CODE_NAME

async def receive_code_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['code_name'] = update.message.text
    lang_code = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('admin_create_code_prompt_points', lang_code))
    return CREATE_CODE_POINTS

async def receive_code_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = get_user_lang(update.effective_user.id)
    try:
        context.user_data['code_points'] = int(update.message.text)
        await update.message.reply_text(get_text('admin_create_code_prompt_uses', lang_code))
        return CREATE_CODE_USES
    except ValueError:
        await update.message.reply_text(get_text('invalid_input', lang_code)); return CREATE_CODE_POINTS

async def receive_code_uses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = get_user_lang(update.effective_user.id)
    try:
        uses = int(update.message.text)
        name = context.user_data['code_name']
        points = context.user_data['code_points']
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT OR REPLACE INTO redeem_codes (code, points, max_uses, current_uses) VALUES (?, ?, ?, 0)", (name, points, uses))
        await update.message.reply_text(get_text('admin_code_created', lang_code).format(code=name, points=points, uses=uses), parse_mode=ParseMode.HTML)
        context.user_data.clear()
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(get_text('invalid_input', lang_code)); return CREATE_CODE_USES

async def edit_connection_info_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    lang_code = get_user_lang(query.from_user.id)
    await query.edit_message_text(get_text('admin_edit_hostname_prompt', lang_code))
    return EDIT_HOSTNAME

async def edit_hostname_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['hostname'] = update.message.text
    lang_code = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('admin_edit_ws_ports_prompt', lang_code))
    return EDIT_WS_PORTS

async def edit_ws_ports_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ws_ports'] = update.message.text
    lang_code = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('admin_edit_ssl_port_prompt', lang_code))
    return EDIT_SSL_PORT

async def edit_ssl_port_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ssl_port'] = update.message.text
    lang_code = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('admin_edit_udpcustom_prompt', lang_code))
    return EDIT_UDPCUSTOM

async def edit_udpcustom_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['udpcustom_port'] = update.message.text
    lang_code = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('admin_edit_contact_prompt', lang_code))
    return EDIT_ADMIN_CONTACT

async def edit_admin_contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_contact'] = update.message.text
    lang_code = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('admin_edit_payload_prompt', lang_code))
    return EDIT_PAYLOAD

async def edit_payload_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = get_user_lang(update.effective_user.id)
    set_connection_setting('hostname', context.user_data['hostname'])
    set_connection_setting('ws_ports', context.user_data['ws_ports'])
    set_connection_setting('ssl_port', context.user_data['ssl_port'])
    set_connection_setting('udpcustom_port', context.user_data['udpcustom_port'])
    set_connection_setting('admin_contact', context.user_data['admin_contact'])
    set_connection_setting('payload', update.message.text)
    await update.message.reply_text(get_text('admin_info_updated_success', lang_code))
    context.user_data.clear()
    return ConversationHandler.END

# =================================================================================
# 7. User Rewards and Codes
# =================================================================================
@log_activity
async def earn_points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = get_user_lang(user_id)
    with sqlite3.connect(DB_FILE) as conn:
        all_channels = conn.execute("SELECT channel_id, channel_link, reward_points, channel_name FROM reward_channels").fetchall()
        claimed_ids = {row[0] for row in conn.execute("SELECT channel_id FROM user_channel_rewards WHERE telegram_user_id = ?", (user_id,))}
    
    if not all_channels:
        await update.message.reply_text(get_text('no_channels_available', lang_code)); return

    keyboard = []
    for cid, link, points, name in all_channels:
        if cid in claimed_ids:
            button_text = f"✅ {name}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data="dummy")])
        else:
            button_text = f"{name} (+{points} {get_text('points', lang_code)})"
            keyboard.append([InlineKeyboardButton(button_text, url=link)])
            keyboard.append([InlineKeyboardButton(get_text('verify_join_button', lang_code), callback_data=f"verify_r_{cid}_{points}")])
    
    # Check if update.callback_query exists before using it
    if update.callback_query:
        reply_func = update.callback_query.edit_message_text
    else:
        reply_func = update.message.reply_text
        
    await reply_func(get_text('rewards_header', lang_code), reply_markup=InlineKeyboardMarkup(keyboard))

async def verify_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    user_id = query.from_user.id
    lang_code = get_user_lang(user_id)
    
    try:
        _, _, channel_id_str, points_str = query.data.split('_')
        channel_id, points = int(channel_id_str), int(points_str)
    except (ValueError, IndexError):
        await query.answer("Data error.", show_alert=True); return

    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            await query.answer(get_text('reward_fail', lang_code), show_alert=True); return
    except Exception as e:
        await query.answer(f"Error: Could not verify. Make sure the bot is an admin in the channel.", show_alert=True); return
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        if cursor.execute("SELECT 1 FROM user_channel_rewards WHERE telegram_user_id = ? AND channel_id = ?", (user_id, channel_id)).fetchone():
            await query.answer("You have already claimed this reward.", show_alert=True); return
        
        cursor.execute("UPDATE users SET points = points + ? WHERE telegram_user_id = ?", (points, user_id))
        cursor.execute("INSERT INTO user_channel_rewards (telegram_user_id, channel_id) VALUES (?, ?)", (user_id, channel_id))
    await query.answer(get_text('reward_success', lang_code).format(points=points), show_alert=True)
    await earn_points_command(update, context)

@log_activity
async def redeem_code_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('redeem_prompt', lang_code))
    return REDEEM_CODE_INPUT

async def redeem_code_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = get_user_lang(user_id)
    code = update.message.text
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        code_data = cursor.execute("SELECT points, max_uses, current_uses FROM redeem_codes WHERE code = ?", (code,)).fetchone()
        
        if not code_data:
            await update.message.reply_text(get_text('redeem_invalid_code', lang_code)); return ConversationHandler.END
        
        points, max_uses, current_uses = code_data
        if current_uses >= max_uses:
            await update.message.reply_text(get_text('redeem_limit_reached', lang_code)); return ConversationHandler.END
        
        if cursor.execute("SELECT 1 FROM redeemed_users WHERE code = ? AND telegram_user_id = ?", (code, user_id)).fetchone():
            await update.message.reply_text(get_text('redeem_already_used', lang_code)); return ConversationHandler.END
            
        cursor.execute("UPDATE users SET points = points + ? WHERE telegram_user_id = ?", (points, user_id))
        cursor.execute("UPDATE redeem_codes SET current_uses = current_uses + 1 WHERE code = ?", (code,))
        cursor.execute("INSERT INTO redeemed_users (code, telegram_user_id) VALUES (?, ?)", (code, user_id))
        new_balance = cursor.execute("SELECT points FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone()[0]
        await update.message.reply_text(get_text('redeem_success', lang_code).format(points=points, new_balance=new_balance), parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# =================================================================================
# 8. Callbacks and Conversations
# =================================================================================
async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    user_id = query.from_user.id
    lang_code = get_user_lang(user_id)

    if await check_membership(user_id, context):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            claimed = cursor.execute("SELECT join_bonus_claimed FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone()[0]
            if not claimed:
                cursor.execute("UPDATE users SET points = points + ?, join_bonus_claimed = 1 WHERE telegram_user_id = ?", (JOIN_BONUS, user_id))
                conn.commit()
                await query.answer(get_text('join_bonus_awarded', lang_code).format(bonus=JOIN_BONUS), show_alert=True)
            
        await query.edit_message_text(get_text('force_join_success', lang_code))
        await start(update, context, from_callback=True)
    else:
        await query.answer(get_text('force_join_fail', lang_code), show_alert=True)

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('operation_cancelled', lang_code))
    context.user_data.clear()
    return ConversationHandler.END

# =================================================================================
# 9. نقطة انطلاق البوت (Main Entry Point)
# =================================================================================
def main():
    init_db()
    
    if "YOUR_TELEGRAM_BOT_TOKEN" in TOKEN:
        print("FATAL ERROR: Bot token is not set.")
        sys.exit(1)

    app = ApplicationBuilder().token(TOKEN).build()

    conv_defaults = {'per_message': True, 'allow_reentry': True}

    # Conversation Handlers (Add these FIRST to ensure specific entry points are prioritized)
    edit_info_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_connection_info_start, pattern='^admin_edit_connection_info$')],
        states={
            EDIT_HOSTNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, edit_hostname_received)],
            EDIT_WS_PORTS: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, edit_ws_ports_received)],
            EDIT_SSL_PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, edit_ssl_port_received)],
            EDIT_UDPCUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, edit_udpcustom_received)],
            EDIT_ADMIN_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, edit_admin_contact_received)],
            EDIT_PAYLOAD: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, edit_payload_received)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
        **conv_defaults
    )
    add_channel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_channel_start, pattern='^admin_add_channel_start$')],
        states={
            ADD_CHANNEL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, add_channel_get_name)],
            ADD_CHANNEL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, add_channel_get_link)],
            ADD_CHANNEL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, add_channel_get_id)],
            ADD_CHANNEL_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, add_channel_get_points)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
        **conv_defaults
    )
    create_code_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_code_start, pattern='^admin_create_code_start$')],
        states={
            CREATE_CODE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, receive_code_name)],
            CREATE_CODE_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, receive_code_points)],
            CREATE_CODE_USES: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, receive_code_uses)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
        **conv_defaults
    )
    redeem_code_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^(?:{re.escape(get_text('redeem_code_button', 'ar'))}|{re.escape(get_text('redeem_code_button', 'en'))})$") & filters.ChatType.PRIVATE, redeem_code_start)],
        states={REDEEM_CODE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, redeem_code_received)]},
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
        **conv_defaults
    )

    # Add command handlers
    app.add_handler(CommandHandler("start", start, filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("admin", admin_panel, filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("language", language_command, filters.ChatType.PRIVATE))

    # Add conversation handlers to the application
    app.add_handler(add_channel_conv)
    app.add_handler(create_code_conv)
    app.add_handler(redeem_code_conv)
    app.add_handler(edit_info_conv)

    # Add message handlers for main menu buttons (simplified Regex as discussed previously)
    app.add_handler(MessageHandler(filters.Regex(f"^(?:{re.escape(get_text('get_ssh_button', 'ar'))}|{re.escape(get_text('get_ssh_button', 'en'))})$") & filters.ChatType.PRIVATE, get_ssh))
    app.add_handler(MessageHandler(filters.Regex(f"^(?:{re.escape(get_text('my_account_button', 'ar'))}|{re.escape(get_text('my_account_button', 'en'))})$") & filters.ChatType.PRIVATE, my_account))
    app.add_handler(MessageHandler(filters.Regex(f"^(?:{re.escape(get_text('balance_button', 'ar'))}|{re.escape(get_text('balance_button', 'en'))})$") & filters.ChatType.PRIVATE, balance_command))
    app.add_handler(MessageHandler(filters.Regex(f"^(?:{re.escape(get_text('daily_button', 'ar'))}|{re.escape(get_text('daily_button', 'en'))})$") & filters.ChatType.PRIVATE, daily_command))
    app.add_handler(MessageHandler(filters.Regex(f"^(?:{re.escape(get_text('earn_points_button', 'ar'))}|{re.escape(get_text('earn_points_button', 'en'))})$") & filters.ChatType.PRIVATE, earn_points_command))
    app.add_handler(MessageHandler(filters.Regex(f"^(?:{re.escape(get_text('contact_admin_button', 'ar'))}|{re.escape(get_text('contact_admin_button', 'en'))})$") & filters.ChatType.PRIVATE, contact_admin_command))

    # Add callback query handlers (general ones AFTER specific conversation entry points)
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern='^verify_join$'))
    app.add_handler(CallbackQueryHandler(verify_reward_callback, pattern='^verify_r_'))
    app.add_handler(CallbackQueryHandler(remove_channel_confirm, pattern='^remove_c_'))
    app.add_handler(CallbackQueryHandler(set_language_callback, pattern='^set_lang_'))
    app.add_handler(CallbackQueryHandler(lambda u,c: u.callback_query.answer(), pattern='^dummy$'))
    # This general admin handler should be added AFTER specific admin conversation entry points
    app.add_handler(CallbackQueryHandler(admin_panel_callback, pattern='^admin_'))

    print("Bot is running with FULL features...")
    app.run_polling()

if __name__ == '__main__':
    main()
