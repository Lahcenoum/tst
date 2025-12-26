#!/bin/bash
# ========================================================================
#  سكريبت المراقبة النهائي (نسخة الاختبار - تعتمد على سجلات الدخول)
#  يقوم بعدّ الجلسات المفتوحة والمغلقة من /var/log/auth.log
# ========================================================================

# ===================== الإعدادات =====================
# ملف لتسجيل الإجراءات
LOG_FILE="/var/log/combined_monitor.log"
# ملف سجلات المصادقة في النظام (تأكد من أنه المسار الصحيح لنظامك)
AUTH_LOG_FILE="/var/log/auth.log"
# ====================================================

# دالة لكتابة سجلات
log_action() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# التحقق من وجود ملف سجلات المصادقة
if [ ! -f "$AUTH_LOG_FILE" ]; then
    log_action "خطأ: ملف سجلات المصادقة غير موجود في المسار: $AUTH_LOG_FILE"
    exit 1
fi

log_action "--- بدء فحص الجلسات من سجلات الدخول (وضع الاختبار) ---"

# الحصول على قائمة المستخدمين مباشرة من النظام
USERS=$(getent passwd | cut -d: -f1 | grep '^sshdatbot')

# المرور على كل مستخدم وتسجيل عدد جلساته
for USER in $USERS; do
    # تجاهل إذا كان اسم المستخدم فارغاً
    if [ -z "$USER" ]; then
        continue
    fi

    # !! الطريقة الجديدة: عدّ الجلسات من ملف auth.log !!
    # ملاحظة: هذا يفترض أن السجلات لم يتم مسحها منذ بدء الجلسات
    SESSIONS_OPENED=$(grep "session opened for user $USER" "$AUTH_LOG_FILE" | wc -l)
    SESSIONS_CLOSED=$(grep "session closed for user $USER" "$AUTH_LOG_FILE" | wc -l)

    CURRENT_SESSIONS=$((SESSIONS_OPENED - SESSIONS_CLOSED))

    # تسجيل عدد الجلسات لكل مستخدم متصل
    if [ "$CURRENT_SESSIONS" -gt 0 ]; then
        log_action "مراقبة: المستخدم '$USER' لديه $CURRENT_SESSIONS جلسات نشطة (حسب السجلات)."
    fi
done

log_action "--- اكتمل فحص الجلسات (وضع الاختبار) ---"
