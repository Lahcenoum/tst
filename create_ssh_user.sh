#!/bin/bash

# ========================================================================
#  النسخة النهائية والمحسنة من سكريبت إنشاء المستخدمين
# ========================================================================

# --- التحقق من المدخلات ---
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <username> <password> <expiry_days>"
    exit 1
fi

USERNAME=$1
PASSWORD=$2
EXPIRY_DAYS=$3

# --- التحقق من وجود المستخدم ---
if id "$USERNAME" &>/dev/null; then
    echo "Error: User '$USERNAME' already exists."
    exit 1
fi

# --- حساب تاريخ الانتهاء ---
EXPIRY_DATE=$(date -d "+$EXPIRY_DAYS days" +%Y-%m-%d)

# --- إنشاء المستخدم (بدون تعيين كلمة مرور مبدئيًا) ---
useradd "$USERNAME" -m -e "$EXPIRY_DATE" -s /bin/bash

# --- التحقق من نجاح إنشاء المستخدم ---
if [ $? -ne 0 ]; then
    echo "Error: Failed to add user '$USERNAME'."
    exit 1
fi

# --- تعيين كلمة المرور باستخدام chpasswd (طريقة أكثر موثوقية) ---
echo "$USERNAME:$PASSWORD" | sudo chpasswd

# --- التحقق من نجاح تعيين كلمة المرور ---
if [ $? -ne 0 ]; then
    echo "Error: Failed to set password for user '$USERNAME'."
    # في حالة الفشل، قم بحذف المستخدم الذي تم إنشاؤه للتو
    userdel -r "$USERNAME"
    exit 1
fi

# --- إخراج التفاصيل لكي يلتقطها البوت ---
# استبدل "YOUR_SERVER_IP" بالآي بي الفعلي لسيرفرك
# يمكنك الحصول عليه بالأمر: curl -s ifconfig.me
SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
echo "Host/IP: ${SERVER_IP}"
echo "Username: ${USERNAME}"
echo "Password: ${PASSWORD}"
echo "Expires on: ${EXPIRY_DATE}"

exit 0
