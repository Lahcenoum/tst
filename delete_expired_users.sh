#!/bin/bash

# ========================================================================
#  سكريبت للبحث عن وحذف حسابات SSH منتهية الصلاحية
#  مصمم للعمل مع بوت التليجرام
# ========================================================================

LOG_FILE="/home/ssh_bot/expired_users.log"
# يبحث فقط عن المستخدمين الذين تم إنشاؤهم بواسطة البوت
USER_PREFIX="sshdatbot"

echo "----------------------------------------" >> "$LOG_FILE"
echo "Running cleanup job on $(date)" >> "$LOG_FILE"

# الحصول على قائمة بجميع المستخدمين الذين يطابقون النمط
# getent passwd | cut -d: -f1 : يحصل على أسماء جميع المستخدمين في النظام
# grep "^$USER_PREFIX" : يقوم بفلترة القائمة لإظهار المستخدمين الذين يبدأ اسمهم بـ sshdatbot فقط
for USERNAME in $(getent passwd | cut -d: -f1 | grep "^$USER_PREFIX"); do
    
    # الحصول على تاريخ انتهاء الصلاحية باستخدام أمر chage
    # chage -l $USERNAME : يعرض معلومات الحساب
    # grep "Account expires" : يبحث عن السطر الذي يحتوي على تاريخ الانتهاء
    # cut -d: -f2- : يستخرج التاريخ فقط
    EXPIRY_DATE_STR=$(chage -l "$USERNAME" | grep "Account expires" | cut -d: -f2-)

    # التحقق مما إذا كان الحساب لديه تاريخ انتهاء صلاحية
    if [ -n "$EXPIRY_DATE_STR" ] && [ "$EXPIRY_DATE_STR" != " never" ]; then
        
        # تحويل تاريخ الانتهاء إلى ثوانٍ (epoch time) للمقارنة
        EXPIRY_DATE_EPOCH=$(date --date="$EXPIRY_DATE_STR" +%s)
        # الحصول على التاريخ الحالي بالثواني
        TODAY_EPOCH=$(date +%s)

        # المقارنة: إذا كان تاريخ الانتهاء أصغر من أو يساوي تاريخ اليوم
        if [ "$EXPIRY_DATE_EPOCH" -le "$TODAY_EPOCH" ]; then
            echo "-> User '$USERNAME' has expired on $EXPIRY_DATE_STR. Deleting..." >> "$LOG_FILE"
            # حذف المستخدم والمجلد الرئيسي الخاص به
            userdel -r "$USERNAME"
            if [ $? -eq 0 ]; then
                echo "   ... Successfully deleted '$USERNAME'." >> "$LOG_FILE"
            else
                echo "   ... FAILED to delete '$USERNAME'." >> "$LOG_FILE"
            fi
        fi
    fi
done

echo "Cleanup job finished on $(date)" >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"

exit 0
