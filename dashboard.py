import sqlite3
import telegram
import asyncio
import subprocess
import re
from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify
from datetime import date, timedelta, datetime

#  مكتبة جديدة لمراقبة الموارد
import psutil

# =================================================================================
# 1. الإعدادات الرئيسية (Configuration)
# =================================================================================
# ⚠️ تأكد من أن هذه القيم مطابقة تماماً للقيم في ملف البوت الرئيسي
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
DB_FILE = 'ssh_bot_users.db'
DASHBOARD_PASSWORD = "admin"
V2RAY_LOG_PATH = "/var/log/xray/access.log" # ⚠️ تأكد من صحة هذا المسار

# --- إعدادات لوحة التحكم ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-very-strong-and-random-secret-key-for-the-dashboard'

# تهيئة اتصال البوت (للإذاعة)
bot = telegram.Bot(token=TOKEN)

# =================================================================================
# 2. دوال مساعدة (Helper Functions)
# =================================================================================

def db_connect():
    """Create a database connection."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('يجب عليك تسجيل الدخول أولاً', 'danger')
            return redirect(url_for('login'))
    wrap.__name__ = f.__name__
    return wrap

def get_system_stats():
    """Gets CPU, RAM, Disk, and Network stats."""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    
    # تحويل البايت إلى جيجابايت
    gb = 1024 ** 3
    
    return {
        'cpu_percent': cpu,
        'ram_percent': ram.percent,
        'ram_total': f"{ram.total / gb:.2f}",
        'ram_used': f"{ram.used / gb:.2f}",
        'disk_percent': disk.percent,
        'disk_total': f"{disk.total / gb:.2f}",
        'disk_used': f"{disk.used / gb:.2f}",
        'net_sent': f"{net.bytes_sent / gb:.2f}",
        'net_recv': f"{net.bytes_recv / gb:.2f}",
    }

def get_ssh_connections(username):
    """Counts active SSH sessions for a user."""
    try:
        command = f"ps -u {username} -o comm= | grep -c '^sshd$'"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return int(result.stdout.strip())
    except Exception:
        return 0

def get_v2ray_live_connections():
    """Parses V2Ray log to count unique IPs per user in the last 2 minutes."""
    connections = {}
    try:
        two_minutes_ago = datetime.now() - timedelta(minutes=2)
        #  استخدام journalctl هو الطريقة الأحدث والأكثر موثوقية لقراءة سجلات xray
        command = "journalctl -u xray -n 5000 --no-pager"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        for line in result.stdout.strip().split('\n'):
            if "accepted" in line:
                # استخراج البريد الإلكتروني (UUID) وعنوان IP
                email_match = re.search(r'email:\s*(\S+)', line)
                ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+', line)
                
                # استخراج الوقت
                time_str_match = re.search(r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', line)

                if email_match and ip_match and time_str_match:
                    log_time = datetime.strptime(f"{date.today().year} {time_str_match.group(1)}", "%Y %b %d %H:%M:%S")

                    if log_time >= two_minutes_ago:
                        email = email_match.group(1)
                        ip = ip_match.group(1)
                        
                        if email not in connections:
                            connections[email] = set()
                        connections[email].add(ip)

        # تحويل المجموعات إلى عدد
        live_users = {email: len(ips) for email, ips in connections.items()}
        return live_users

    except Exception as e:
        print(f"Error reading V2Ray log: {e}")
        return {}


# =================================================================================
# 3. HTML Templates (تم تحديثها)
# =================================================================================

# --- القالب الأساسي (Layout) ---
LAYOUT_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - لوحة التحكم</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Cairo', sans-serif; }
        .sidebar { transition: transform 0.3s ease-in-out; }
        .main-content { transition: margin-right 0.3s ease-in-out; }
        @media (max-width: 768px) {
            .sidebar { transform: translateX(100%); }
            .sidebar.open { transform: translateX(0); }
            .main-content { margin-right: 0 !important; }
        }
    </style>
</head>
<body class="bg-gray-900 text-gray-200">
    <div class="flex h-screen">
        <!-- Sidebar -->
        <aside id="sidebar" class="sidebar fixed top-0 right-0 h-full w-64 bg-gray-800 p-4 z-20 md:translate-x-0 overflow-y-auto">
            <h1 class="text-2xl font-bold text-white mb-8 border-b border-gray-700 pb-4">لوحة التحكم</h1>
            <nav>
                <a href="{{ url_for('index') }}" class="flex items-center p-3 rounded-lg hover:bg-gray-700 {% if request.path == '/' %}bg-blue-600{% endif %}">
                    <svg class="w-6 h-6 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>
                    <span>الرئيسية</span>
                </a>
                <a href="{{ url_for('users_list') }}" class="flex items-center p-3 mt-2 rounded-lg hover:bg-gray-700 {% if 'users' in request.path %}bg-blue-600{% endif %}">
                    <svg class="w-6 h-6 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M15 21a6 6 0 00-9-5.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-3-5.197m0 0A7.963 7.963 0 0112 4.354a7.963 7.963 0 013 3.203m-3 5.197a4 4 0 11-6.32-4.962M15 21a2 2 0 11-4 0m4 0a2 2 0 10-4 0m4 0a2 2 0 10-4 0"></path></svg>
                    <span>المستخدمون</span>
                </a>
                <a href="{{ url_for('codes_list') }}" class="flex items-center p-3 mt-2 rounded-lg hover:bg-gray-700 {% if 'codes' in request.path %}bg-blue-600{% endif %}">
                    <svg class="w-6 h-6 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7"></path></svg>
                    <span>أكواد الهدايا</span>
                </a>
                <a href="{{ url_for('channels_list') }}" class="flex items-center p-3 mt-2 rounded-lg hover:bg-gray-700 {% if 'channels' in request.path %}bg-blue-600{% endif %}">
                    <svg class="w-6 h-6 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <span>قنوات الربح</span>
                </a>
                <a href="{{ url_for('settings') }}" class="flex items-center p-3 mt-2 rounded-lg hover:bg-gray-700 {% if 'settings' in request.path %}bg-blue-600{% endif %}">
                     <svg class="w-6 h-6 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                    <span>الإعدادات</span>
                </a>
            </nav>
            <a href="{{ url_for('logout') }}" class="absolute bottom-4 right-4 flex items-center p-3 rounded-lg text-red-400 hover:bg-red-500 hover:text-white">
                <svg class="w-6 h-6 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
                <span>تسجيل الخروج</span>
            </a>
        </aside>

        <!-- Main Content -->
        <main id="main-content" class="flex-1 p-6 md:mr-64 overflow-y-auto">
            <button id="menu-button" class="md:hidden mb-4 p-2 rounded-md bg-gray-700 text-white">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7"></path></svg>
            </button>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="p-4 mb-4 text-sm rounded-lg {% if category == 'danger' %} bg-red-800 text-red-200 {% else %} bg-green-800 text-green-200 {% endif %}" role="alert">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            {% block content %}{% endblock %}
        </main>
    </div>
    
    <script>
        const sidebar = document.getElementById('sidebar');
        const menuButton = document.getElementById('menu-button');
        menuButton.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    </script>
</body>
</html>
"""

# --- صفحة تسجيل الدخول ---
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style> body { font-family: 'Cairo', sans-serif; } </style>
</head>
<body class="bg-gray-900 flex items-center justify-center h-screen">
    <div class="w-full max-w-md p-8 space-y-6 bg-gray-800 rounded-lg shadow-md">
        <h1 class="text-2xl font-bold text-center text-white">تسجيل الدخول للوحة التحكم</h1>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="p-3 text-sm rounded-lg bg-red-800 text-red-200" role="alert">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST">
            <div>
                <label for="password" class="block mb-2 text-sm font-medium text-gray-300">كلمة المرور</label>
                <input type="password" name="password" id="password" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5" required>
            </div>
            <button type="submit" class="w-full mt-6 text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:outline-none focus:ring-blue-800 font-medium rounded-lg text-sm px-5 py-2.5 text-center">دخول</button>
        </form>
    </div>
</body>
</html>
"""

# --- الصفحة الرئيسية (index.html) ---
INDEX_HTML = """
{% extends "layout.html" %}
{% block content %}
<h2 class="text-3xl font-bold mb-6 text-white">لوحة المعلومات الرئيسية</h2>

<!-- Stat Cards -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
    <div class="bg-gray-800 p-6 rounded-lg">
        <h3 class="text-gray-400 text-lg">إجمالي المستخدمين</h3>
        <p class="text-3xl font-bold text-white">{{ stats.total }}</p>
    </div>
    <div class="bg-gray-800 p-6 rounded-lg">
        <h3 class="text-gray-400 text-lg">النشطون اليوم</h3>
        <p class="text-3xl font-bold text-white">{{ stats.active_today }}</p>
    </div>
    <div class="bg-gray-800 p-6 rounded-lg">
        <h3 class="text-gray-400 text-lg">المستخدمون الجدد اليوم</h3>
        <p class="text-3xl font-bold text-white">{{ stats.new_today }}</p>
    </div>
    <div class="bg-gray-800 p-6 rounded-lg">
        <h3 class="text-gray-400 text-lg">إجمالي الحسابات</h3>
        <p class="text-xl font-bold text-white">SSH: {{ stats.ssh_accounts }} | V2Ray: {{ stats.v2ray_accounts }}</p>
    </div>
</div>

<!-- System Stats -->
<div class="bg-gray-800 p-6 rounded-lg mb-8">
    <h3 class="text-xl font-bold mb-4 text-white">حالة النظام</h3>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
            <label class="text-gray-400">المعالج (CPU)</label>
            <div class="w-full bg-gray-700 rounded-full h-2.5">
                <div class="bg-blue-600 h-2.5 rounded-full" style="width: {{ system.cpu_percent }}%"></div>
            </div>
            <p class="text-sm text-center mt-1">{{ system.cpu_percent }}%</p>
        </div>
        <div>
            <label class="text-gray-400">الذاكرة (RAM)</label>
            <div class="w-full bg-gray-700 rounded-full h-2.5">
                <div class="bg-green-500 h-2.5 rounded-full" style="width: {{ system.ram_percent }}%"></div>
            </div>
            <p class="text-sm text-center mt-1">{{ system.ram_used }} / {{ system.ram_total }} GB</p>
        </div>
        <div>
            <label class="text-gray-400">القرص (Disk)</label>
            <div class="w-full bg-gray-700 rounded-full h-2.5">
                <div class="bg-yellow-500 h-2.5 rounded-full" style="width: {{ system.disk_percent }}%"></div>
            </div>
            <p class="text-sm text-center mt-1">{{ system.disk_used }} / {{ system.disk_total }} GB</p>
        </div>
    </div>
    <div class="mt-4 border-t border-gray-700 pt-4">
        <h4 class="text-gray-400">استهلاك الشبكة (منذ التشغيل)</h4>
        <p class="text-white"><span class="font-bold">التنزيل:</span> {{ system.net_recv }} GB | <span class="font-bold">الرفع:</span> {{ system.net_sent }} GB</p>
    </div>
</div>


<!-- Chart and Broadcast -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Chart -->
    <div class="bg-gray-800 p-6 rounded-lg">
        <h3 class="text-xl font-bold mb-4 text-white">نمو المستخدمين (آخر 7 أيام)</h3>
        <canvas id="userGrowthChart"></canvas>
    </div>

    <!-- Broadcast Form -->
    <div class="bg-gray-800 p-6 rounded-lg">
        <h3 class="text-xl font-bold mb-4 text-white">إذاعة للكل</h3>
        <form method="POST" enctype="multipart/form-data">
            <div class="mb-4">
                <label for="message" class="block mb-2 text-sm font-medium text-gray-300">الرسالة (تدعم الماركداون)</label>
                <textarea id="message" name="message" rows="6" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"></textarea>
            </div>
            <div class="mb-4">
                <label for="file" class="block mb-2 text-sm font-medium text-gray-300">أو رفع ملف (اختياري)</label>
                <input type="file" name="file" id="file" class="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700">
            </div>
            <button type="submit" class="w-full text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:outline-none focus:ring-blue-800 font-medium rounded-lg text-sm px-5 py-2.5 text-center">إرسال الإذاعة</button>
        </form>
    </div>
</div>

<script>
    const ctx = document.getElementById('userGrowthChart').getContext('2d');
    const userGrowthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: {{ stats.chart_labels | tojson }},
            datasets: [{
                label: 'مستخدم جديد',
                data: {{ stats.chart_data | tojson }},
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                borderColor: 'rgba(59, 130, 246, 1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            scales: {
                y: { beginAtZero: true, ticks: { color: '#9CA3AF' }, grid: { color: '#374151' } },
                x: { ticks: { color: '#9CA3AF' }, grid: { color: '#374151' } }
            },
            plugins: { legend: { labels: { color: '#D1D5DB' } } }
        }
    });
</script>
{% endblock %}
"""

# --- صفحة المستخدمين ---
USERS_HTML = """
{% extends "layout.html" %}
{% block content %}
<h2 class="text-3xl font-bold mb-6 text-white">قائمة المستخدمين</h2>
<div class="bg-gray-800 p-6 rounded-lg">
    <div class="overflow-x-auto">
        <table class="w-full text-sm text-right text-gray-400">
            <thead class="text-xs uppercase bg-gray-700 text-gray-400">
                <tr>
                    <th scope="col" class="px-6 py-3">معرف المستخدم</th>
                    <th scope="col" class="px-6 py-3">النقاط</th>
                    <th scope="col" class="px-6 py-3">المتصلون حالياً</th>
                    <th scope="col" class="px-6 py-3">تاريخ الانضمام</th>
                    <th scope="col" class="px-6 py-3">الإجراءات</th>
                </tr>
            </thead>
            <tbody>
            {% for user in users %}
                <tr class="border-b bg-gray-800 border-gray-700">
                    <td class="px-6 py-4">{{ user.id }}</td>
                    <td class="px-6 py-4" id="points-{{ user.id }}">{{ user.points }}</td>
                    <td class="px-6 py-4">
                        {% if user.ssh_conns > 0 %}
                            <span class="bg-blue-600 text-white text-xs font-medium mr-2 px-2.5 py-0.5 rounded">SSH: {{ user.ssh_conns }}</span>
                        {% endif %}
                        {% if user.v2ray_conns > 0 %}
                            <span class="bg-green-600 text-white text-xs font-medium mr-2 px-2.5 py-0.5 rounded">V2Ray: {{ user.v2ray_conns }}</span>
                        {% endif %}
                        {% if user.ssh_conns == 0 and user.v2ray_conns == 0 %}
                            <span class="text-gray-500">لا يوجد</span>
                        {% endif %}
                    </td>
                    <td class="px-6 py-4">{{ user.date }}</td>
                    <td class="px-6 py-4">
                        <button onclick="editPoints('{{ user.id }}')" class="font-medium text-blue-500 hover:underline">تعديل النقاط</button>
                    </td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
</div>
<script>
function editPoints(userId) {
    const currentPoints = document.getElementById(`points-${userId}`).innerText;
    const newPoints = prompt(`أدخل العدد الجديد من النقاط للمستخدم ${userId}:`, currentPoints);
    if (newPoints !== null && !isNaN(newPoints)) {
        fetch('/update_points', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, points: newPoints })
        })
        .then(response => response.json())
        .then(data => {
            if(data.success) {
                document.getElementById(`points-${userId}`).innerText = newPoints;
                alert('تم تحديث النقاط بنجاح!');
            } else {
                alert('فشل تحديث النقاط: ' + data.error);
            }
        });
    }
}
</script>
{% endblock %}
"""

# --- باقي قوالب HTML (Codes, Channels, Settings) تبقى كما هي ---
CODES_HTML = """
{% extends "layout.html" %}
{% block content %}
<h2 class="text-3xl font-bold mb-6 text-white">إدارة أكواد الهدايا</h2>
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="lg:col-span-2 bg-gray-800 p-6 rounded-lg">
        <h3 class="text-xl font-bold mb-4 text-white">الأكواد الحالية</h3>
        <div class="overflow-x-auto">
            <table class="w-full text-sm text-right text-gray-400">
                <thead class="text-xs uppercase bg-gray-700 text-gray-400">
                    <tr>
                        <th scope="col" class="px-6 py-3">الكود</th>
                        <th scope="col" class="px-6 py-3">النقاط</th>
                        <th scope="col" class="px-6 py-3">الاستخدام</th>
                        <th scope="col" class="px-6 py-3">الإجراءات</th>
                    </tr>
                </thead>
                <tbody>
                {% for code in codes %}
                    <tr class="border-b bg-gray-800 border-gray-700">
                        <td class="px-6 py-4 font-mono">{{ code.code }}</td>
                        <td class="px-6 py-4">{{ code.points }}</td>
                        <td class="px-6 py-4">{{ code.current_uses }} / {{ code.max_uses }}</td>
                        <td class="px-6 py-4">
                            <form method="POST" action="{{ url_for('delete_code') }}" onsubmit="return confirm('هل أنت متأكد من حذف هذا الكود؟');">
                                <input type="hidden" name="code" value="{{ code.code }}">
                                <button type="submit" class="font-medium text-red-500 hover:underline">حذف</button>
                            </form>
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    <div class="bg-gray-800 p-6 rounded-lg">
        <h3 class="text-xl font-bold mb-4 text-white">إنشاء كود جديد</h3>
        <form method="POST" action="{{ url_for('create_code') }}">
            <div class="mb-4">
                <label for="code" class="block mb-2 text-sm font-medium text-gray-300">اسم الكود</label>
                <input type="text" name="code" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5" required>
            </div>
            <div class="mb-4">
                <label for="points" class="block mb-2 text-sm font-medium text-gray-300">عدد النقاط</label>
                <input type="number" name="points" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5" required>
            </div>
            <div class="mb-4">
                <label for="max_uses" class="block mb-2 text-sm font-medium text-gray-300">أقصى عدد للاستخدام</label>
                <input type="number" name="max_uses" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5" required>
            </div>
            <button type="submit" class="w-full text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5">إنشاء</button>
        </form>
    </div>
</div>
{% endblock %}
"""
CHANNELS_HTML = """
{% extends "layout.html" %}
{% block content %}
<h2 class="text-3xl font-bold mb-6 text-white">إدارة قنوات الربح</h2>
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="lg:col-span-2 bg-gray-800 p-6 rounded-lg">
        <h3 class="text-xl font-bold mb-4 text-white">القنوات الحالية</h3>
        <div class="overflow-x-auto">
            <table class="w-full text-sm text-right text-gray-400">
                <thead class="text-xs uppercase bg-gray-700 text-gray-400">
                    <tr>
                        <th scope="col" class="px-6 py-3">الاسم</th>
                        <th scope="col" class="px-6 py-3">المعرف (ID)</th>
                        <th scope="col" class="px-6 py-3">النقاط</th>
                        <th scope="col" class="px-6 py-3">الإجراءات</th>
                    </tr>
                </thead>
                <tbody>
                {% for channel in channels %}
                    <tr class="border-b bg-gray-800 border-gray-700">
                        <td class="px-6 py-4">{{ channel.channel_name }}</td>
                        <td class="px-6 py-4 font-mono">{{ channel.channel_id }}</td>
                        <td class="px-6 py-4">{{ channel.reward_points }}</td>
                        <td class="px-6 py-4">
                            <form method="POST" action="{{ url_for('delete_channel') }}" onsubmit="return confirm('هل أنت متأكد من حذف هذه القناة؟');">
                                <input type="hidden" name="channel_id" value="{{ channel.channel_id }}">
                                <button type="submit" class="font-medium text-red-500 hover:underline">حذف</button>
                            </form>
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    <div class="bg-gray-800 p-6 rounded-lg">
        <h3 class="text-xl font-bold mb-4 text-white">إضافة قناة جديدة</h3>
        <form method="POST" action="{{ url_for('create_channel') }}">
            <div class="mb-4">
                <label class="block mb-2 text-sm">اسم القناة</label>
                <input type="text" name="name" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5" required>
            </div>
            <div class="mb-4">
                <label class="block mb-2 text-sm">رابط القناة</label>
                <input type="text" name="link" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5" required>
            </div>
            <div class="mb-4">
                <label class="block mb-2 text-sm">معرف القناة (ID)</label>
                <input type="number" name="id" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5" placeholder="-100..." required>
            </div>
            <div class="mb-4">
                <label class="block mb-2 text-sm">نقاط المكافأة</label>
                <input type="number" name="points" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5" required>
            </div>
            <button type="submit" class="w-full text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5">إضافة</button>
        </form>
    </div>
</div>
{% endblock %}
"""
SETTINGS_HTML = """
{% extends "layout.html" %}
{% block content %}
<h2 class="text-3xl font-bold mb-6 text-white">إعدادات الاتصال (SSH)</h2>
<div class="bg-gray-800 p-6 rounded-lg max-w-2xl mx-auto">
    <form method="POST">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
                <label class="block mb-2 text-sm">Hostname</label>
                <input type="text" name="hostname" value="{{ settings.hostname }}" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5">
            </div>
            <div>
                <label class="block mb-2 text-sm">Websocket Ports</label>
                <input type="text" name="ws_ports" value="{{ settings.ws_ports }}" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5">
            </div>
            <div>
                <label class="block mb-2 text-sm">SSL Port</label>
                <input type="text" name="ssl_port" value="{{ settings.ssl_port }}" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5">
            </div>
            <div>
                <label class="block mb-2 text-sm">UDPCUSTOM Port</label>
                <input type="text" name="udpcustom_port" value="{{ settings.udpcustom_port }}" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5">
            </div>
             <div class="md:col-span-2">
                <label class="block mb-2 text-sm">معلومات التواصل مع الأدمن</label>
                <input type="text" name="admin_contact" value="{{ settings.admin_contact }}" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5">
            </div>
            <div class="md:col-span-2">
                <label class="block mb-2 text-sm">Payload</label>
                <textarea name="payload" rows="5" class="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg w-full p-2.5">{{ settings.payload }}</textarea>
            </div>
        </div>
        <button type="submit" class="w-full mt-6 text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5">حفظ التغييرات</button>
    </form>
</div>
{% endblock %}
"""


# =================================================================================
# 4. روابط لوحة التحكم (Routes)
# =================================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == DASHBOARD_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash('كلمة المرور غير صحيحة!', 'danger')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        # Handle broadcast
        conn = db_connect()
        user_ids = [row['telegram_user_id'] for row in conn.execute('SELECT telegram_user_id FROM users').fetchall()]
        conn.close()
        
        if not user_ids:
            flash('لا يوجد مستخدمين في قاعدة البيانات بعد.', 'warning')
            return redirect(url_for('index'))
            
        message = request.form.get('message')
        uploaded_file = request.files.get('file')

        if not message and not uploaded_file.get('file'):
            flash('يجب كتابة رسالة أو رفع ملف على الأقل.', 'danger')
            return redirect(url_for('index'))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def broadcast(user_ids, message=None, file=None, caption=None):
            success_count, fail_count = 0, 0
            for user_id in user_ids:
                try:
                    if file and file.filename != '':
                        file.seek(0)
                        await bot.send_document(chat_id=user_id, document=file, caption=caption)
                    elif message:
                        await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
                    success_count += 1
                    await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"Failed to send to {user_id}: {e}")
                    fail_count += 1
            return success_count, fail_count

        if uploaded_file and uploaded_file.filename != '':
            success, failed = loop.run_until_complete(broadcast(user_ids, file=uploaded_file, caption=message))
        else:
            success, failed = loop.run_until_complete(broadcast(user_ids, message=message))
        
        flash(f'تم إرسال الإذاعة بنجاح إلى {success} مستخدم. فشل الإرسال لـ {failed} مستخدم.', 'success')
        return redirect(url_for('index'))

    # GET request: Show stats
    conn = db_connect()
    today = date.today().isoformat()
    stats = {
        'total': conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'active_today': conn.execute("SELECT COUNT(*) FROM daily_activity WHERE last_seen_date = ?", (today,)).fetchone()[0],
        'new_today': conn.execute("SELECT COUNT(*) FROM users WHERE created_date = ?", (today,)).fetchone()[0],
        'ssh_accounts': conn.execute("SELECT COUNT(*) FROM ssh_accounts").fetchone()[0],
        'v2ray_accounts': conn.execute("SELECT COUNT(*) FROM v2ray_accounts").fetchone()[0]
    }
    
    chart_labels, chart_data = [], []
    for i in range(6, -1, -1):
        day = date.today() - timedelta(days=i)
        chart_labels.append(day.strftime('%m-%d'))
        count = conn.execute("SELECT COUNT(*) FROM users WHERE created_date = ?", (day.isoformat(),)).fetchone()[0]
        chart_data.append(count)
    
    stats['chart_labels'] = chart_labels
    stats['chart_data'] = chart_data
    
    conn.close()
    system_stats = get_system_stats()
    return render_template_string(INDEX_HTML, title="الرئيسية", stats=stats, system=system_stats)

@app.route('/users')
@login_required
def users_list():
    conn = db_connect()
    users_data = conn.execute('SELECT telegram_user_id, points, created_date FROM users ORDER BY points DESC').fetchall()
    
    v2ray_connections = get_v2ray_live_connections()
    
    users_list_with_conns = []
    for user in users_data:
        user_dict = dict(user)
        user_id = user_dict['telegram_user_id']
        
        # Get SSH connections
        ssh_username = f"sshdatbot{user_id}"
        user_dict['ssh_conns'] = get_ssh_connections(ssh_username)
        
        # Get V2Ray connections
        v2ray_email = f"user-{user_id}"
        user_dict['v2ray_conns'] = v2ray_connections.get(v2ray_email, 0)
        
        # Reformat for template
        users_list_with_conns.append({
            'id': user_id,
            'points': user_dict['points'],
            'date': user_dict['created_date'],
            'ssh_conns': user_dict['ssh_conns'],
            'v2ray_conns': user_dict['v2ray_conns']
        })

    conn.close()
    return render_template_string(USERS_HTML, title="المستخدمون", users=users_list_with_conns)

@app.route('/update_points', methods=['POST'])
@login_required
def update_points():
    data = request.json
    try:
        conn = db_connect()
        conn.execute('UPDATE users SET points = ? WHERE telegram_user_id = ?', (int(data['points']), int(data['user_id'])))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/codes', methods=['GET'])
@login_required
def codes_list():
    conn = db_connect()
    codes = conn.execute('SELECT * FROM redeem_codes').fetchall()
    conn.close()
    return render_template_string(CODES_HTML, title="أكواد الهدايا", codes=codes)

@app.route('/codes/create', methods=['POST'])
@login_required
def create_code():
    conn = db_connect()
    conn.execute("INSERT INTO redeem_codes (code, points, max_uses, current_uses) VALUES (?, ?, ?, 0)",
                 (request.form['code'], request.form['points'], request.form['max_uses']))
    conn.commit()
    conn.close()
    flash('تم إنشاء الكود بنجاح!', 'success')
    return redirect(url_for('codes_list'))

@app.route('/codes/delete', methods=['POST'])
@login_required
def delete_code():
    conn = db_connect()
    conn.execute("DELETE FROM redeem_codes WHERE code = ?", (request.form['code'],))
    conn.commit()
    conn.close()
    flash('تم حذف الكود بنجاح!', 'success')
    return redirect(url_for('codes_list'))
    
@app.route('/channels', methods=['GET'])
@login_required
def channels_list():
    conn = db_connect()
    channels = conn.execute('SELECT * FROM reward_channels').fetchall()
    conn.close()
    return render_template_string(CHANNELS_HTML, title="قنوات الربح", channels=channels)

@app.route('/channels/create', methods=['POST'])
@login_required
def create_channel():
    conn = db_connect()
    conn.execute("INSERT INTO reward_channels (channel_id, channel_link, reward_points, channel_name) VALUES (?, ?, ?, ?)",
                 (request.form['id'], request.form['link'], request.form['points'], request.form['name']))
    conn.commit()
    conn.close()
    flash('تمت إضافة القناة بنجاح!', 'success')
    return redirect(url_for('channels_list'))

@app.route('/channels/delete', methods=['POST'])
@login_required
def delete_channel():
    conn = db_connect()
    conn.execute("DELETE FROM reward_channels WHERE channel_id = ?", (request.form['channel_id'],))
    conn.commit()
    conn.close()
    flash('تم حذف القناة بنجاح!', 'success')
    return redirect(url_for('channels_list'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    conn = db_connect()
    if request.method == 'POST':
        settings_keys = ['hostname', 'ws_ports', 'ssl_port', 'udpcustom_port', 'admin_contact', 'payload']
        for key in settings_keys:
            conn.execute("UPDATE connection_settings SET value = ? WHERE key = ?", (request.form[key], key))
        conn.commit()
        flash('تم حفظ الإعدادات بنجاح!', 'success')
        return redirect(url_for('settings'))
    
    settings_data = {row['key']: row['value'] for row in conn.execute('SELECT * FROM connection_settings').fetchall()}
    conn.close()
    return render_template_string(SETTINGS_HTML, title="الإعدادات", settings=settings_data)


# =================================================================================
# 5. نقطة انطلاق لوحة التحكم
# =================================================================================
if __name__ == '__main__':
    print("Dashboard is running on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
