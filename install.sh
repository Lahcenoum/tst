#!/bin/bash

# ========================================================================
#  سكريبت التثبيت الشامل والكامل - SSH Telegram Bot
#  - يعتمد على وجود جميع السكريبتات في مستودع GitHub
# ========================================================================

# --- إعدادات أساسية ---
GIT_REPO_URL="https://github.com/Lahcenoum/sshtestbot.git"
PROJECT_DIR="/home/ssh_bot"
# الحد الأقصى لعدد الاتصالات المسموح بها لكل حساب
CONNECTION_LIMIT=2

# --- نهاية قسم الإعدادات ---

# التحقق من صلاحيات الجذر
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ يجب تشغيل السكربت بصلاحيات root."
  exit 1
fi

echo "=================================================="
echo "   🔧 بدء التثبيت الكامل والشامل لبوت SSH"
echo "=================================================="

# الخطوة 0: حذف أي تثبيت قديم لضمان بداية نظيفة
echo -e "\n[0/10] ✅ حذف أي تثبيت قديم..."
sudo systemctl stop ssh_bot.service >/dev/null 2>&1
sudo rm -rf "$PROJECT_DIR"

# 1. تحديث النظام وتثبيت المتطلبات
echo -e "\n[1/10] ✅ تحديث النظام وتثبيت المتطلبات..."
apt-get update
apt-get install -y git python3-venv python3-pip openssl sudo

# 2. استنساخ المشروع
echo -e "\n[2/10] ✅ استنساخ المشروع من GitHub..."
git clone "$GIT_REPO_URL" "$PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1

# 3. إدخال التوكن
echo -e "\n[3/10] ✅ إعداد توكن البوت..."
read -p "📥 أدخل توكن البوت: " BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then echo "❌ لم يتم إدخال التوكن."; exit 1; fi
sed -i 's/^TOKEN = "YOUR_TELEGRAM_BOT_TOKEN".*/TOKEN = "'"$BOT_TOKEN"'"/' "$PROJECT_DIR/bot.py"

#!/bin/bash

# ========================================================================
#  سكريبت التثبيت الشامل والكامل - SSH Telegram Bot
#  - تم إصلاح مشكلة نقل الملفات وإعداد جميع الميزات تلقائيًا
# ========================================================================

# --- إعدادات أساسية ---
GIT_REPO_URL="https://github.com/Lahcenoum/sshtestbot.git"
PROJECT_DIR="/home/ssh_bot"
CONNECTION_LIMIT=2

# --- نهاية قسم الإعدادات ---

# التحقق من صلاحيات الجذر
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ يجب تشغيل السكربت بصلاحيات root."
  exit 1
fi

echo "=================================================="
echo "   🔧 بدء التثبيت الكامل والشامل لبوت SSH"
echo "=================================================="

# الخطوة 0: حذف أي تثبيت قديم لضمان بداية نظيفة
echo -e "\n[0/10] ✅ حذف أي تثبيت قديم..."
systemctl stop ssh_bot.service >/dev/null 2>&1
rm -rf "$PROJECT_DIR"

# 1. تحديث النظام وتثبيت المتطلبات
echo -e "\n[1/10] ✅ تحديث النظام وتثبيت المتطلبات..."
apt-get update
apt-get install -y git python3-venv python3-pip openssl sudo

# 2. استنساخ المشروع
echo -e "\n[2/10] ✅ استنساخ المشروع من GitHub..."
git clone "$GIT_REPO_URL" "$PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1

# 3. إدخال التوكن
echo -e "\n[3/10] ✅ إعداد توكن البوت..."
read -p "📥 أدخل توكن البوت: " BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then echo "❌ لم يتم إدخال التوكن."; exit 1; fi
sed -i 's/^TOKEN = "YOUR_TELEGRAM_BOT_TOKEN".*/TOKEN = "'"$BOT_TOKEN"'"/' "$PROJECT_DIR/bot.py"

# 4. إعداد سكربت إنشاء المستخدم
echo -e "\n[4/10] ✅ إعداد سكربت إنشاء حسابات SSH..."
read -p "📥 أدخل عنوان IP الخاص بسيرفرك: " SERVER_IP
if [ -z "$SERVER_IP" ]; then echo "❌ لم يتم إدخال الآي بي."; exit 1; fi

if [ -f "create_ssh_user.sh" ]; then
    sed -i "s/YOUR_SERVER_IP/${SERVER_IP}/g" "create_ssh_user.sh"
    mv "create_ssh_user.sh" "/usr/local/bin/"
    chmod +x "/usr/local/bin/create_ssh_user.sh"
    echo "-> تم نقل وإعداد 'create_ssh_user.sh' بنجاح."
else
    echo "-> تحذير: لم يتم العثور على 'create_ssh_user.sh'."
fi

# 5. إعداد سكربت الحذف التلقائي للحسابات منتهية الصلاحية
echo -e "\n[5/10] ✅ إعداد سكربت الحذف التلقائي للمستخدمين منتهية الصلاحية..."
if [ -f "delete_expired_users.sh" ]; then
    mv "delete_expired_users.sh" "/usr/local/bin/"
    chmod +x "/usr/local/bin/delete_expired_users.sh"
    (crontab -l 2>/dev/null | grep -v -F "/usr/local/bin/delete_expired_users.sh" ; echo "0 0 * * * /usr/local/bin/delete_expired_users.sh") | crontab -
    echo "-> تم إعداد مهمة حذف الحسابات منتهية الصلاحية بنجاح."
else
    echo "-> تحذير: لم يتم العثور على ملف 'delete_expired_users.sh'."
fi

# 6. إعداد سكربت مراقبة الاتصالات المتعددة
echo -e "\n[6/10] ✅ إعداد سكربت مراقبة وحذف الحسابات المشتركة..."
if [ -f "monitor_connections.sh" ]; then
    sed -i "s/CONNECTION_LIMIT=[0-9]\+/CONNECTION_LIMIT=$CONNECTION_LIMIT/" "monitor_connections.sh"
    mv "monitor_connections.sh" "/usr/local/bin/"
    chmod +x "/usr/local/bin/monitor_connections.sh"
    (crontab -l 2>/dev/null | grep -v -F "/usr/local/bin/monitor_connections.sh" ; echo "*/5 * * * * /usr/local/bin/monitor_connections.sh") | crontab -
    echo "-> تم إعداد مهمة مراقبة الاتصالات بنجاح."
else
    echo "-> تحذير: لم يتم العثور على ملف 'monitor_connections.sh'."
fi

# 7. إعداد بيئة بايثون
echo -e "\n[7/10] ✅ إعداد البيئة الافتراضية وتثبيت المكتبات..."
python3 -m venv venv
(
  source venv/bin/activate
  pip install --upgrade pip
  if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
  else
    pip install python-telegram-bot
  fi
)

# 8. إعداد خدمة systemd
echo -e "\n[8/10] ✅ إعداد الخدمة الدائمة systemd..."
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

# 9. تشغيل الخدمة
echo -e "\n[9/10] ✅ تمكين وتشغيل الخدمة..."
systemctl daemon-reload
systemctl enable ssh_bot.service
systemctl restart ssh_bot.service

# 10. نهاية التثبيت
echo -e "\n[10/10] ✅ تم التثبيت بنجاح!"
echo "=================================================="
echo "📌 لمراقبة الخدمة: systemctl status ssh_bot.service"
echo "📌 لإعادة التشغيل: systemctl restart ssh_bot.service"
echo "=================================================="

# 5. إعداد سكربت الحذف التلقائي للحسابات منتهية الصلاحية
echo -e "\n[5/10] ✅ إعداد سكربت الحذف التلقائي للمستخدمين منتهية الصلاحية..."
if [ -f "delete_expired_users.sh" ]; then
    mv delete_expired_users.sh /usr/local/bin/
    chmod +x /usr/local/bin/delete_expired_users.sh
    (crontab -l 2>/dev/null | grep -v -F "/usr/local/bin/delete_expired_users.sh" ; echo "0 0 * * * /usr/local/bin/delete_expired_users.sh") | crontab -
    echo "-> تم إعداد مهمة حذف الحسابات منتهية الصلاحية بنجاح."
else
    echo "-> تحذير: لم يتم العثور على ملف 'delete_expired_users.sh' في المستودع. تم تخطي هذه الخطوة."
fi

# 6. إعداد سكربت مراقبة الاتصالات المتعددة
echo -e "\n[6/10] ✅ إعداد سكربت مراقبة وحذف الحسابات المشتركة..."
if [ -f "monitor_connections.sh" ]; then
    # تعديل قيمة الحد الأقصى للاتصالات داخل السكريبت
    sed -i "s/CONNECTION_LIMIT=[0-9]\+/CONNECTION_LIMIT=$CONNECTION_LIMIT/" "monitor_connections.sh"
    mv monitor_connections.sh /usr/local/bin/
    chmod +x /usr/local/bin/monitor_connections.sh
    # إضافة المهمة إلى cron (سيتم تشغيلها كل 5 دقائق)
    (crontab -l 2>/dev/null | grep -v -F "/usr/local/bin/monitor_connections.sh" ; echo "*/5 * * * * /usr/local/bin/monitor_connections.sh") | crontab -
    echo "-> تم إعداد مهمة مراقبة الاتصالات بنجاح."
else
    echo "-> تحذير: لم يتم العثور على ملف 'monitor_connections.sh' في المستودع. تم تخطي هذه الخطوة."
fi

# 7. إعداد بيئة بايثون
echo -e "\n[7/10] ✅ إعداد البيئة الافتراضية وتثبيت المكتبات..."
python3 -m venv venv
(
  source venv/bin/activate
  pip install --upgrade pip
  if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
  else
    pip install python-telegram-bot
  fi
)

# 8. إعداد خدمة systemd
echo -e "\n[8/10] ✅ إعداد الخدمة الدائمة systemd..."
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

# 9. تشغيل الخدمة
echo -e "\n[9/10] ✅ تمكين وتشغيل الخدمة..."
systemctl daemon-reload
systemctl enable ssh_bot.service
systemctl restart ssh_bot.service

# 10. نهاية التثبيت
echo -e "\n[10/10] ✅ تم التثبيت بنجاح!"
echo "=================================================="
echo "📌 لمراقبة الخدمة: systemctl status ssh_bot.service"
echo "📌 لإعادة التشغيل: systemctl restart ssh_bot.service"
echo "=================================================="
