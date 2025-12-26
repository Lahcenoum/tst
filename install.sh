#!/bin/bash
# Final Version: Focuses on SSH-only setup and integrates automatic DB backups to Telegram.

# ========================================================================
#                 سكريبت التثبيت (SSH + نسخ احتياطي)
# ========================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# --- إعدادات أساسية ---
GIT_REPO_URL="https://github.com/Lahcenoum/sshtestbot.git"
PROJECT_DIR="/home/ssh_bot"
SSH_CONNECTION_LIMIT=2 # حد الاتصالات لخدمة SSH

# --- نهاية قسم الإعدادات ---

# --- دوال الألوان ---
red() { echo -e "\e[31m$*\e[0m"; }
green() { echo -e "\e[32m$*\e[0m"; }
yellow() { echo -e "\e[33m$*\e[0m"; }

# التحقق من صلاحيات الجذر
if [ "$(id -u)" -ne 0 ]; then
    red "❌ يجب تشغيل السكربت بصلاحيات root."
    exit 1
fi

echo "=================================================="
echo "    🔧 بدء التثبيت الكامل للبوت (SSH فقط)"
echo "=================================================="

# --- القسم الأول: تثبيت بوت التليجرام ---

# الخطوة 0: حذف أي تثبيت قديم
echo -e "\n[0/10] 🗑️ حذف أي تثبيت قديم..."
systemctl stop ssh_bot.service ssh_bot_dashboard.service >/dev/null 2>&1 || true
systemctl disable ssh_bot.service ssh_bot_dashboard.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/ssh_bot.service
rm -f /etc/systemd/system/ssh_bot_dashboard.service
rm -rf "$PROJECT_DIR"

# 1. تحديث النظام وتثبيت المتطلبات
echo -e "\n[1/10] 📦 تحديث النظام وتثبيت المتطلبات الأساسية..."
apt-get update
apt-get install -y git python3-venv python3-pip openssl sudo curl cron

# 2. التأكد من أن خدمة cron تعمل
echo -e "\n[2/10] ⏰ التأكد من تشغيل خدمة cron..."
systemctl start cron
systemctl enable cron
green "  - ✅ خدمة cron تعمل الآن."

# 3. استنساخ المشروع
echo -e "\n[3/10] 📥 استنساخ المشروع من GitHub..."
git clone "$GIT_REPO_URL" "$PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1

# 4. إدخال توكن البوت
echo -e "\n[4/10] 🔑 إعداد توكن البوت..."
read -p "  - أدخل توكن البوت: " BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then red "❌ لم يتم إدخال التوكن."; exit 1; fi
sed -i 's/^TOKEN = "YOUR_TELEGRAM_BOT_TOKEN".*/TOKEN = "'"$BOT_TOKEN"'"/' "$PROJECT_DIR/bot.py"
sed -i 's/^TOKEN = "YOUR_TELEGRAM_BOT_TOKEN".*/TOKEN = "'"$BOT_TOKEN"'"/' "$PROJECT_DIR/dashboard.py"
green "  - ✅ تم تحديث التوكن."

# 5. إعداد كلمة مرور لوحة التحكم
echo -e "\n[5/10] 🛡️ إعداد كلمة مرور لوحة التحكم..."
read -p "  - أدخل كلمة مرور للوحة التحكم (اتركها فارغة لاستخدام 'admin'): " DASH_PASSWORD
if [ -z "$DASH_PASSWORD" ]; then DASH_PASSWORD="admin"; fi
sed -i "s/^DASHBOARD_PASSWORD = \"admin\".*/DASHBOARD_PASSWORD = \"$DASH_PASSWORD\"/" "$PROJECT_DIR/dashboard.py"
green "  - ✅ تم تعيين كلمة مرور لوحة التحكم."

# 6. إعداد سكربتات SSH
echo -e "\n[6/10] 👤 إعداد سكربتات SSH..."
read -p "  - أدخل عنوان IP الخاص بسيرفرك: " SERVER_IP
if [ -z "$SERVER_IP" ]; then red "❌ لم يتم إدخال الآي بي."; exit 1; fi

if [ -f "create_ssh_user.sh" ]; then
    sed -i "s/YOUR_SERVER_IP/${SERVER_IP}/g" "create_ssh_user.sh"
    mv "create_ssh_user.sh" "/usr/local/bin/"
    chmod +x "/usr/local/bin/create_ssh_user.sh"
    green "  - ✅ تم إعداد سكربت إنشاء المستخدمين."
else
    yellow "  - ⚠️ تحذير: لم يتم العثور على 'create_ssh_user.sh'."
fi

if [ -f "delete_expired_users.sh" ]; then
    mv "delete_expired_users.sh" "/usr/local/bin/"
    chmod +x "/usr/local/bin/delete_expired_users.sh"
    { crontab -l 2>/dev/null | grep -v -F "/usr/local/bin/delete_expired_users.sh"; echo "0 0 * * * /usr/local/bin/delete_expired_users.sh"; } | crontab -
    green "  - ✅ تم إعداد مهمة حذف الحسابات منتهية الصلاحية."
else
    yellow "  - ⚠️ تحذير: لم يتم العثور على 'delete_expired_users.sh'."
fi

if [ -f "monitor_connections.sh" ]; then
    sed -i "s/CONNECTION_LIMIT=[0-9]\+/CONNECTION_LIMIT=$SSH_CONNECTION_LIMIT/" "monitor_connections.sh"
    mv "monitor_connections.sh" "/usr/local/bin/"
    chmod +x "/usr/local/bin/monitor_connections.sh"
    { crontab -l 2>/dev/null | grep -v -F "/usr/local/bin/monitor_connections.sh"; echo "*/1 * * * * /usr/local/bin/monitor_connections.sh"; } | crontab -
    green "  - ✅ تم إعداد مهمة مراقبة اتصالات SSH."
else
    yellow "  - ⚠️ تحذير: لم يتم العثور على 'monitor_connections.sh'."
fi

# 7. إعداد النسخ الاحتياطي التلقائي
echo -e "\n[7/10] 🗄️ إعداد النسخ الاحتياطي التلقائي لقاعدة البيانات..."
read -p "  - أدخل معرف القناة (Channel ID) لإرسال النسخ الاحتياطية إليها (يجب أن يبدأ بـ -100): " CHANNEL_ID
if [[ ! "$CHANNEL_ID" =~ ^-100[0-9]+$ ]]; then
    red "❌ المعرف غير صالح. يجب أن يكون رقمًا ويبدأ بـ -100."
    exit 1
fi

# إنشاء سكربت النسخ الاحتياطي
cat > /usr/local/bin/backup_bot.sh << EOL
#!/bin/bash
BOT_TOKEN="$BOT_TOKEN"
CHANNEL_ID="$CHANNEL_ID"
DB_PATH="$PROJECT_DIR/ssh_bot_users.db"
CAPTION="نسخة احتياطية جديدة لقاعدة بيانات المستخدمين - \$(date)"

if [ ! -f "\$DB_PATH" ]; then exit 1; fi

BACKUP_FILE="/tmp/db_backup_\$(date +%F_%H-%M-%S).db"
cp "\$DB_PATH" "\$BACKUP_FILE"

curl -s -F "chat_id=\${CHANNEL_ID}" -F "document=@\${BACKUP_FILE}" -F "caption=\${CAPTION}" "https://api.telegram.org/bot\${BOT_TOKEN}/sendDocument" > /dev/null

rm "\$BACKUP_FILE"
EOL

chmod +x /usr/local/bin/backup_bot.sh
{ crontab -l 2>/dev/null | grep -v -F "/usr/local/bin/backup_bot.sh"; echo "0 */10 * * * /usr/local/bin/backup_bot.sh"; } | crontab -
green "  - ✅ تم إعداد مهمة النسخ الاحتياطي كل 10 ساعات بنجاح."

# 8. إعداد بيئة بايثون
echo -e "\n[8/10] 🐍 إعداد البيئة الافتراضية وتثبيت المكتبات..."
python3 -m venv venv
(
    source venv/bin/activate
    pip install --upgrade pip
    pip install python-telegram-bot flask psutil pytz
    green "  - ✅ تم تثبيت جميع المكتبات الضرورية بنجاح."
)

# 9. إعداد وتشغيل الخدمات
echo -e "\n[9/10] 🚀 إعداد وتشغيل الخدمات..."
cat > /etc/systemd/system/ssh_bot.service << EOL
[Unit]
Description=Telegram SSH Bot Service
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

cat > /etc/systemd/system/ssh_bot_dashboard.service << EOL
[Unit]
Description=Telegram SSH Bot Dashboard
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/dashboard.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL
green "  - ✅ تم إنشاء ملفات الخدمات بنجاح."

systemctl daemon-reload
systemctl enable ssh_bot.service ssh_bot_dashboard.service >/dev/null 2>&1
systemctl restart ssh_bot.service ssh_bot_dashboard.service

# 10. نهاية التثبيت
echo -e "\n[10/10] 🎉 تم التثبيت بنجاح!"
echo "=================================================="
green "🎉 تم التثبيت بنجاح!"
echo "--------------------------------------------------"
echo "  - 🤖 لمراقبة البوت: systemctl status ssh_bot.service"
echo "  - 📊 لمراقبة لوحة التحكم: systemctl status ssh_bot_dashboard.service"
echo "  - 🌐 رابط لوحة التحكم: http://${SERVER_IP}:5000"
echo "  - 🗄️ تم إعداد النسخ الاحتياطي لقاعدة البيانات كل 10 ساعات."
echo "=================================================="
