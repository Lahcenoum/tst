#!/bin/bash
# ========================================================================
#  سكريبت مراقبة V2Ray (الحل الأفضل بواجهة API)
#  يحذف المستخدمين المخالفين فوراً بدون إعادة تشغيل الخدمة
# ========================================================================

# ===================== الإعدادات =====================
# الحد الأقصى للاتصالات (عدد عناوين IP المختلفة) المسموح بها لكل مستخدم
CONNECTION_LIMIT=1

# المسار الكامل لملف إعدادات Xray/V2Ray
V2RAY_CONFIG="/usr/local/etc/xray/config.json"
# المسار الكامل لملف سجلات الوصول
V2RAY_LOG="/var/log/xray/access.log"
# ملف لتسجيل عمليات الحذف
DELETION_LOG="/var/log/xray/deletions.log"

#  إعدادات الـ API
# تأكد من أن هذه القيم تطابق الإعدادات في ملف config.json
API_SERVER="127.0.0.1:10085"
VLESS_INBOUND_TAG="vless-inbound"
# ====================================================

# دالة لكتابة سجلات
log_action() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$DELETION_LOG"
}

# التحقق من وجود ملف السجل
if [ ! -f "$V2RAY_LOG" ]; then
    log_action "خطأ: ملف السجل $V2RAY_LOG غير موجود."
    exit 1
fi

# استخراج البريد الإلكتروني للمستخدمين المخالفين من سجلات آخر دقيقتين
EXCEEDED_USERS_EMAIL=$(tail -n 5000 "$V2RAY_LOG" | \
    grep "accepted" | \
    awk -v time_limit=$(date -d '2 minutes ago' +%s) '
    {
        ip = ""; email = "";
        for (i=1; i<=NF; i++) {
            if ($i == "email:") { email = $(i+1); }
            if (match($i, /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/)) {
                ip = $i; sub(/:[0-9]+$/, "", ip);
            }
        }
        
        gsub(/"/, "", $1); gsub(/\[|\]/, "", $2);
        split($2, dt, ":");
        event_time_str = dt[1]" "dt[2]":"dt[3]":"dt[4];
        cmd = "date -d \"" event_time_str "\" +%s";
        cmd | getline event_time; close(cmd);

        if (event_time > time_limit && email != "" && ip != "") {
            print email, ip
        }
    }' | \
    sort | uniq | \
    awk '{ count[$1]++ } END { for (user in count) if (count[user] > '"$CONNECTION_LIMIT"') print user }')

# إذا لم يكن هناك مستخدمون مخالفون، قم بالخروج
if [ -z "$EXCEEDED_USERS_EMAIL" ]; then
    exit 0
fi

CONFIG_CHANGED=false

for USER_EMAIL in $EXCEEDED_USERS_EMAIL; do
    # استخراج الـ UUID المرتبط بالبريد الإلكتروني من ملف الإعدادات
    USER_ID=$(jq -r '.inbounds[] | select(.tag=="'$VLESS_INBOUND_TAG'") | .settings.clients[] | select(.email=="'$USER_EMAIL'") | .id' "$V2RAY_CONFIG")

    if [ -z "$USER_ID" ]; then
        log_action "لم يتم العثور على UUID للبريد الإلكتروني $USER_EMAIL في ملف الإعدادات."
        continue
    fi

    log_action "تنبيه: المستخدم $USER_EMAIL تجاوز الحد. يتم الآن حذفه (UUID: $USER_ID)."
    
    # الخطوة 1: الحذف الفوري من الخدمة باستخدام الـ API (بدون إعادة تشغيل)
    /usr/local/bin/xray api handlers remove --server="$API_SERVER" --inbound="$VLESS_INBOUND_TAG" --email="$USER_EMAIL" > /dev/null 2>&1
    
    # الخطوة 2: الحذف من ملف الإعدادات لضمان عدم عودته بعد أي إعادة تشغيل مستقبلية
    jq '(.inbounds[] | select(.tag=="'$VLESS_INBOUND_TAG'") .settings.clients) |= map(select(.id != "'$USER_ID'"))' "$V2RAY_CONFIG" > "${V2RAY_CONFIG}.tmp" && mv "${V2RAY_CONFIG}.tmp" "$V2RAY_CONFIG"
    
    CONFIG_CHANGED=true
done

if [ "$CONFIG_CHANGED" = true ]; then
    log_action "تم حذف مستخدم واحد أو أكثر بنجاح بدون انقطاع الخدمة."
fi

exit 0
