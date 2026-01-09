#!/bin/bash
# Final Definitive Version: Aligned with the bot code that uses Xray's own CLI.
# No external API libraries are needed. This version avoids using Port 80.

# ========================================================================
#  سكريبت التثبيت الشامل - SSH/V2Ray Telegram Bot ومراقبة الاتصالات
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
echo "    🔧 بدء التثبيت الكامل للبوت (SSH & V2Ray)"
echo "=================================================="

# --- القسم الأول: تثبيت بوت التليجرام ---

# الخطوة 0: حذف أي تثبيت قديم
echo -e "\n[0/15] 🗑️ حذف أي تثبيت قديم..."
systemctl stop ssh_bot.service ssh_bot_dashboard.service xray >/dev/null 2>&1 || true
systemctl disable ssh_bot.service ssh_bot_dashboard.service xray >/dev/null 2>&1 || true
rm -f /etc/systemd/system/ssh_bot.service
rm -f /etc/systemd/system/ssh_bot_dashboard.service
rm -rf "$PROJECT_DIR"

# 1. تحديث النظام وتثبيت المتطلبات
echo -e "\n[1/15] 📦 تحديث النظام وتثبيت المتطلبات الأساسية..."
apt-get update
apt-get install -y git python3-venv python3-pip openssl sudo jq curl wget unzip coreutils socat cron nginx ufw
pip install -r requirements.txt

# 2. التأكد من أن خدمة cron تعمل
echo -e "\n[2/15] ⏰ التأكد من تشغيل خدمة cron..."
systemctl start cron
systemctl enable cron
green "  - ✅ خدمة cron تعمل الآن."

# 3. استنساخ المشروع
echo -e "\n[3/15] 📥 استنساخ المشروع من GitHub..."
git clone "$GIT_REPO_URL" "$PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1
source venv/bin/activate
pip install -r requirements.txt

# 4. إدخال توكن البوت
echo -e "\n[4/15] 🔑 إعداد توكن البوت..."
read -p "  - أدخل توكن البوت: " BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then red "❌ لم يتم إدخال التوكن."; exit 1; fi
sed -i 's/^TOKEN = "YOUR_TELEGRAM_BOT_TOKEN".*/TOKEN = "'"$BOT_TOKEN"'"/' "$PROJECT_DIR/bot.py"
sed -i 's/^TOKEN = "YOUR_TELEGRAM_BOT_TOKEN".*/TOKEN = "'"$BOT_TOKEN"'"/' "$PROJECT_DIR/dashboard.py"
green "  - ✅ تم تحديث التوكن."

# 6. إعداد سكربت إنشاء مستخدم SSH
echo -e "\n[6/15] 👤 إعداد سكربت إنشاء حسابات SSH..."
read -p "  - أدخل عنوان IP الخاص بسيرفرك: " SERVER_IP
if [ -z "$SERVER_IP" ]; then red "❌ لم يتم إدخال الآي بي."; exit 1; fi

if [ -f "create_ssh_user.sh" ]; then
    sed -i "s/YOUR_SERVER_IP/${SERVER_IP}/g" "create_ssh_user.sh"
    mv "create_ssh_user.sh" "/usr/local/bin/"
    chmod +x "/usr/local/bin/create_ssh_user.sh"
    green "  - ✅ تم نقل وإعداد 'create_ssh_user.sh'."
else
    yellow "  - ⚠️ تحذير: لم يتم العثور على 'create_ssh_user.sh'."
fi

# 7. إعداد سكربت حذف مستخدمي SSH منتهية الصلاحية
echo -e "\n[7/15] ⏳ إعداد سكربت الحذف التلقائي لمستخدمي SSH..."
if [ -f "delete_expired_users.sh" ]; then
    mv "delete_expired_users.sh" "/usr/local/bin/"
    chmod +x "/usr/local/bin/delete_expired_users.sh"
    { crontab -l 2>/dev/null | grep -v -F "/usr/local/bin/delete_expired_users.sh"; echo "0 0 * * * /usr/local/bin/delete_expired_users.sh"; } | crontab -
    green "  - ✅ تم إعداد مهمة حذف الحسابات منتهية الصلاحية."
else
    yellow "  - ⚠️ تحذير: لم يتم العثور على 'delete_expired_users.sh'."
fi

# 8. إعداد سكربت مراقبة اتصالات SSH
echo -e "\n[8/15] 🔗 إعداد سكربت مراقبة اتصالات SSH المتعددة..."
if [ -f "monitor_connections.sh" ]; then
    sed -i "s/CONNECTION_LIMIT=[0-9]\+/CONNECTION_LIMIT=$SSH_CONNECTION_LIMIT/" "monitor_connections.sh"
    mv "monitor_connections.sh" "/usr/local/bin/"
    chmod +x "/usr/local/bin/monitor_connections.sh"
    { crontab -l 2>/dev/null | grep -v -F "/usr/local/bin/monitor_connections.sh"; echo "*/1 * * * * /usr/local/bin/monitor_connections.sh"; } | crontab -
    green "  - ✅ تم إعداد مهمة مراقبة اتصالات SSH."
else
    yellow "  - ⚠️ تحذير: لم يتم العثور على 'monitor_connections.sh'."
fi

# --- القسم الثاني: تثبيت V2Ray ---
# --- القسم الثالث: التشغيل النهائي ---
# 14. إعداد بيئة بايثون
echo -e "\n[14/15] 🐍 إعداد البيئة الافتراضية وتثبيت المكتبات..."
python3 -m venv venv
(
    source venv/bin/activate
    echo "  - تحديث pip..."
    pip install --upgrade pip
    
    echo "  - تثبيت المكتبات الأساسية فقط..."
    pip install python-telegram-bot flask psutil pytz

    green "  - ✅ تم تثبيت جميع المكتبات الضرورية بنجاح."
)

# 15. إعداد وتشغيل الخدمات
echo -e "\n[15/15] 🚀 إعداد وتشغيل الخدمات النهائية..."
cat > /etc/systemd/system/ssh_bot.service << EOL
[Unit]
Description=Telegram SSH & V2Ray Bot Service
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
Description=Telegram SSH & V2Ray Bot Dashboard
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
systemctl enable ssh_bot.service ssh_bot_dashboard.service xray >/dev/null 2>&1
systemctl restart ssh_bot.service ssh_bot_dashboard.service xray

# --- نهاية التثبيت ---
VLESS_URL="vless://${UUID}@${V2RAY_DOMAIN}:443?encryption=none&security=tls&type=ws&host=${V2RAY_DOMAIN}&sni=${V2RAY_DOMAIN}&path=$(python3 -c "from urllib.parse import quote; print(quote('${WSPATH}'))")#VLESS-WS-TLS-${V2RAY_DOMAIN}"

echo "=================================================="
green "🎉 تم التثبيت بنجاح!"
echo "--------------------------------------------------"
echo "  - 🤖 لمراقبة البوت: systemctl status ssh_bot.service"
echo "  - 📊 لمراقبة لوحة التحكم: systemctl status ssh_bot_dashboard.service"
echo "  - 🚀 لمراقبة V2Ray: systemctl status xray"
echo "  - 🌐 رابط لوحة التحكم: http://${SERVER_IP}:5000"
echo "--------------------------------------------------"
yellow "  ℹ️ معلومات V2Ray الأولية (للتجربة):"
echo "  الدومين: ${V2RAY_DOMAIN}"
echo "  المسار (WS): ${WSPATH}"
echo "  UUID: ${UUID}"
echo "  رابط الإستيراد: ${VLESS_URL}"
echo "=================================================="
