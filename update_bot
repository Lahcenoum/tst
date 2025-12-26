#!/bin/bash

# =================================================================
#  سكربت للتحقق من التحديثات على GitHub وتحديث البوت تلقائياً
# =================================================================

# المسار إلى مجلد المشروع
PROJECT_DIR="/home/ssh_bot"

# الانتقال إلى مجلد المشروع، والخروج إذا فشل
cd "$PROJECT_DIR" || exit

echo "Checking for updates from GitHub at $(date)..."

# جلب آخر التغييرات من المستودع دون دمجها
git fetch

# مقارنة الإصدار المحلي بالإصدار الموجود على GitHub
HEADHASH=$(git rev-parse HEAD)
UPSTREAMHASH=$(git rev-parse @{u})

if [ "$HEADHASH" == "$UPSTREAMHASH" ]; then
    echo "Bot is already up-to-date. No changes needed."
else
    echo "New changes detected. Updating the bot..."
    
    # سحب التغييرات الجديدة من الفرع الرئيسي (main)
    git pull origin main
    
    # إعادة تثبيت المكتبات في حال تم تحديث ملف requirements.txt
    if [ -f "requirements.txt" ]; then
        echo "Re-installing dependencies..."
        pip3 install -r requirements.txt
    fi
    
    # إعادة تشغيل خدمة البوت لتطبيق التحديثات
    echo "Restarting the bot service..."
    systemctl restart ssh_bot.service
    
    echo "Bot updated and restarted successfully!"
fi
