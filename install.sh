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

# 2. التأكد من أن خدمة cron تعمل
echo -e "\n[2/15] ⏰ التأكد من تشغيل خدمة cron..."
systemctl start cron
systemctl enable cron
green "  - ✅ خدمة cron تعمل الآن."

# 3. استنساخ المشروع
echo -e "\n[3/15] 📥 استنساخ المشروع من GitHub..."
git clone "$GIT_REPO_URL" "$PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1

# 4. إدخال توكن البوت
echo -e "\n[4/15] 🔑 إعداد توكن البوت..."
read -p "  - أدخل توكن البوت: " BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then red "❌ لم يتم إدخال التوكن."; exit 1; fi
sed -i 's/^TOKEN = "YOUR_TELEGRAM_BOT_TOKEN".*/TOKEN = "'"$BOT_TOKEN"'"/' "$PROJECT_DIR/bot.py"
sed -i 's/^TOKEN = "YOUR_TELEGRAM_BOT_TOKEN".*/TOKEN = "'"$BOT_TOKEN"'"/' "$PROJECT_DIR/dashboard.py"
green "  - ✅ تم تحديث التوكن."

# 5. إعداد كلمة مرور لوحة التحكم
echo -e "\n[5/15] 🛡️ إعداد كلمة مرور لوحة التحكم..."
read -p "  - أدخل كلمة مرور للوحة التحكم (اتركها فارغة لاستخدام 'admin'): " DASH_PASSWORD
if [ -z "$DASH_PASSWORD" ]; then DASH_PASSWORD="admin"; fi
sed -i "s/^DASHBOARD_PASSWORD = \"admin\".*/DASHBOARD_PASSWORD = \"$DASH_PASSWORD\"/" "$PROJECT_DIR/dashboard.py"
green "  - ✅ تم تعيين كلمة مرور لوحة التحكم."

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
echo -e "\n--------------------------------------------------"
echo "        🚀 بدء تثبيت و إعداد V2Ray"
echo "--------------------------------------------------"

# 9. إدخال دومين V2Ray
echo -e "\n[9/15] 🌐 إعداد دومين V2Ray..."
read -p "  - أدخل اسم الدومين الخاص بـ V2Ray (مثال: example.com): " V2RAY_DOMAIN
if [[ -z ${V2RAY_DOMAIN} ]]; then red "  [خطأ] إدخال الدومين مطلوب."; exit 1; fi
EMAIL="admin@${V2RAY_DOMAIN}"
WSPATH="/vless-ws"

# تحديث الدومين في ملف البوت
sed -i "s/V2RAY_SERVER_ADDRESS = \".*\"/V2RAY_SERVER_ADDRESS = \"${V2RAY_DOMAIN}\"/" "$PROJECT_DIR/bot.py"
green "  - ✅ تم تحديث الدومين في ملف البوت."

# 10. تثبيت Xray-core
echo -e "\n[10/15]  xray تثبيت..."
bash <(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh) >/tmp/xray-install.log 2>&1 || {
    red "فشل تثبيت Xray. راجع /tmp/xray-install.log"; exit 1
}
mkdir -p /var/www/html
chown -R www-data:www-data /var/www/html

# 11. إصدار شهادة TLS (بدون استخدام بورت 80)
echo -e "\n[11/15] 🔒 إصدار شهادة TLS عبر بورت 443..."
# التأكد من أن بورت 443 مفتوح ومتاح
ufw allow 443/tcp >/dev/null 2>&1
# إيقاف Nginx مؤقتاً للسماح لـ Certbot باستخدام بورت 443
echo "  - إيقاف Nginx مؤقتاً..."
systemctl stop nginx
# استصدار الشهادة باستخدام تحدي TLS-ALPN-01
apt-get install -y certbot
certbot certonly --standalone --preferred-challenges tls-alpn-01 -d "$V2RAY_DOMAIN" -m "$EMAIL" --agree-tos --no-eff-email -n || {
    red "فشل إصدار الشهادة. تأكد أن الدومين يشير إلى IP هذا السيرفر وأن بورت 443 غير مستخدم حالياً.";
    systemctl start nginx; # إعادة تشغيل Nginx في حالة الفشل
    exit 1;
}
# إعادة تشغيل Nginx بعد الحصول على الشهادة
echo "  - إعادة تشغيل Nginx..."
systemctl start nginx

# 12. إنشاء إعدادات Xray مع API
echo -e "\n[12/15] ⚙️ إنشاء إعدادات Xray مع واجهة API..."
UUID=$(cat /proc/sys/kernel/random/uuid)
cat >/usr/local/etc/xray/config.json <<XRAYCONF
{
  "log": { "access": "/var/log/xray/access.log", "error": "/var/log/xray/error.log", "loglevel": "warning" },
  "api": { "tag": "api", "services": [ "HandlerService" ] },
  "routing": { "rules": [ { "type": "field", "inboundTag": [ "api" ], "outboundTag": "api" } ] },
  "inbounds": [
    { "listen": "127.0.0.1", "port": 10085, "protocol": "dokodemo-door", "settings": { "address": "127.0.0.1" }, "tag": "api" },
    { "port": 10000, "listen": "127.0.0.1", "protocol": "vless", "tag": "vless-inbound",
      "settings": { "clients": [ { "id": "${UUID}", "email": "vless@${V2RAY_DOMAIN}" } ], "decryption": "none" },
      "streamSettings": { "network": "ws", "security": "none", "wsSettings": { "path": "${WSPATH}" } }
    }
  ],
  "outbounds": [ { "protocol": "freedom" }, { "protocol": "blackhole", "tag": "blocked" } ]
}
XRAYCONF
systemctl enable xray && systemctl restart xray

# 13. إعداد Nginx النهائي (بورت 443 فقط)
echo -e "\n[13/15] 🔗 إعداد Nginx النهائي على بورت 443 فقط..."
cat >/etc/nginx/sites-available/xray <<NGINX
map \$http_upgrade \$connection_upgrade { default upgrade; '' close; }
server {
    listen 443 ssl http2;
    server_name ${V2RAY_DOMAIN};
    ssl_certificate /etc/letsencrypt/live/${V2RAY_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${V2RAY_DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    root /var/www/html;
    location ${WSPATH} {
        proxy_redirect off;
        proxy_pass http://127.0.0.1:10000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$host;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/xray /etc/nginx/sites-enabled/xray
rm -f /etc/nginx/sites-enabled/xray_temp || true
systemctl reload nginx
{ crontab -l 2>/dev/null | grep -v certbot || true; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'"; } | crontab -
green "  - ✅ تم إعداد مهمة تجديد الشهادة تلقائياً."

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
