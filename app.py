from flask import Flask, render_template, jsonify, request
import mysql.connector
import sys
import os

# Добавляем путь к библиотекам
sys.path.append(os.path.join(os.path.dirname(__file__), "python", "libs"))

# Database configuration
db_config = {
    'host': '192.168.46.4',
    'port': 3306,
    'user': 'pashapay',
    'password': 'Q1w2e3r4!@#',
    'database': 'report',
}

app = Flask(__name__, template_folder='flask-dashboard/app/templates')

def execute_query(query, params):
    """Executes an SQL query with given parameters."""
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        result = cursor.fetchall()
        return result
    finally:
        connection.close()

@app.route("/")
def home():
    return render_template("dashboard.html")

# ---------- Новый маршрут с UNION ALL и динамическими датами ----------
@app.route("/report_by_topic")
def get_report_by_topic():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        return jsonify({"error": "Please provide start_date and end_date"}), 400

    query = """
SELECT 
    COALESCE(rt.category_name, '') AS category_or_name,
    DATE(cr.answer_date) AS report_date,
    cr.number AS Number,
    COUNT(*) AS total
FROM call_report cr
LEFT JOIN registered_topic rt ON cr.id = rt.call_report_id
WHERE cr.answer_date >= %s AND cr.answer_date < %s
GROUP BY category_or_name, report_date, Number

UNION ALL

SELECT 
    COALESCE(crt.name, '') AS category_or_name,
    DATE(cr.first_agent_message_date) AS report_date,
    cr.channel_id AS Number,
    COUNT(*) AS total
FROM chat_report cr
LEFT JOIN chat_registered_topic crt ON cr.id = crt.chat_report_id
WHERE cr.first_agent_message_date >= %s AND cr.first_agent_message_date < %s
GROUP BY category_or_name, report_date, Number
    """

    data = execute_query(query, (start_date, end_date, start_date, end_date))
    return jsonify(data)

# ---------- DAILY ----------
@app.route("/daily/data/<tab>")
def get_daily_data(tab):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({"error": "Please provide start_date and end_date"}), 400

    query = {
        "calls": """
            SELECT DATE(c.enter_queue_date) AS report_date, COUNT(*) AS total_calls
            FROM call_report c
            WHERE DATE(c.enter_queue_date) BETWEEN %s AND %s
              AND (c.type = 'in' OR c.type = 'abandon')
            GROUP BY report_date
            ORDER BY report_date;
        """,
        "aht": """
            SELECT DATE(c.enter_queue_date) AS report_date, ROUND(AVG(c.call_duration), 2) AS avg_call_duration
            FROM call_report c
            WHERE DATE(c.enter_queue_date) BETWEEN %s AND %s
            GROUP BY report_date
            ORDER BY report_date;
        """,
        "chats": """
            SELECT DATE(c.assign_date) AS report_date, COUNT(*) AS total_chats
            FROM chat_report c
            WHERE type = 'in'
              AND DATE(c.assign_date) BETWEEN %s AND %s
            GROUP BY report_date
            ORDER BY report_date;
        """,
        "frt": """
            SELECT DATE(c.assign_date) AS report_date, ROUND(AVG(c.chat_frt), 2) AS avg_chat_frt
            FROM chat_report c
            WHERE DATE(c.assign_date) BETWEEN %s AND %s
            GROUP BY report_date
            ORDER BY report_date;
        """,
        "sl": """
            SELECT DATE(c.enter_queue_date) AS report_date,
                   ROUND(SUM(CASE WHEN c.queue_wait_time <= 20 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS sl
            FROM call_report c
            WHERE DATE(c.enter_queue_date) BETWEEN %s AND %s
              AND c.type = 'in'
              AND c.queue_name = 'm10'
            GROUP BY report_date
            ORDER BY report_date;
        """,
        "rt": """
            SELECT DATE(c.assign_date) AS report_date, ROUND(AVG(c.resolution_time_avg), 2) AS resolution_time_avg
            FROM chat_report c
            WHERE DATE(c.assign_date) BETWEEN %s AND %s
            GROUP BY report_date
            ORDER BY report_date;
        """,
        "abandoned": """
            SELECT DATE(c.enter_queue_date) AS report_date, COUNT(*) AS total_abandoned
            FROM call_report c
            WHERE DATE(c.enter_queue_date) BETWEEN %s AND %s
              AND c.type = 'abandon'
            GROUP BY report_date
            ORDER BY report_date;
        """
    }.get(tab)

    if not query:
        return jsonify({"error": "Invalid tab name"}), 400

    data = execute_query(query, (start_date, end_date))
    return jsonify(data)

# ---------- HOURLY ----------
@app.route("/hourly/data/<tab>")
def get_hourly_data(tab):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({"error": "Please provide start_date and end_date"}), 400

    query = {
        "calls": """
            SELECT HOUR(c.enter_queue_date) AS hour, COUNT(*) AS total_calls
            FROM call_report c
            WHERE DATE(c.enter_queue_date) BETWEEN %s AND %s
              AND (c.type = 'in' OR c.type = 'abandon')
            GROUP BY hour
            ORDER BY hour;
        """,
        "aht": """
            SELECT HOUR(answer_date) AS hour, ROUND(AVG(call_duration), 2) AS avg_call_duration
            FROM call_report
            WHERE DATE(answer_date) BETWEEN %s AND %s
            GROUP BY hour
            ORDER BY hour;
        """,
        "chats": """
            SELECT HOUR(c.assign_date) AS hour, COUNT(*) AS total_chats
            FROM chat_report c
            WHERE c.type = 'in'
              AND DATE(assign_date) BETWEEN %s AND %s
            GROUP BY hour
            ORDER BY hour;
        """,
        "frt": """
            SELECT HOUR(assign_date) AS hour, ROUND(AVG(chat_frt), 2) AS avg_chat_frt
            FROM chat_report
            WHERE DATE(assign_date) BETWEEN %s AND %s
            GROUP BY hour
            ORDER BY hour;
        """,
        "sl": """
            SELECT HOUR(enter_queue_date) AS hour,
                   ROUND(SUM(CASE WHEN queue_wait_time <= 20 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS sl
            FROM call_report c
            WHERE DATE(enter_queue_date) BETWEEN %s AND %s
              AND type = 'in'
              AND queue_name = 'm10'
            GROUP BY hour
            ORDER BY hour;
        """,
        "rt": """
            SELECT HOUR(assign_date) AS hour, ROUND(AVG(resolution_time_avg), 2) AS resolution_time_avg
            FROM chat_report c
            WHERE DATE(assign_date) BETWEEN %s AND %s
            GROUP BY hour
            ORDER BY hour;
        """,
        "abandoned": """
            SELECT HOUR(c.enter_queue_date) AS hour, COUNT(*) AS total_abandoned
            FROM call_report c
            WHERE DATE(c.enter_queue_date) BETWEEN %s AND %s
              AND c.type = 'abandon'
            GROUP BY hour
            ORDER BY hour;
        """
    }.get(tab)

    if not query:
        return jsonify({"error": "Invalid tab name"}), 400

    data = execute_query(query, (start_date, end_date))
    return jsonify(data)

# ---------- ONLINE ----------
@app.route("/online/data")
def online_data():
    """
    Возвращает все нужные метрики за текущие сутки (с 00:00 до текущего момента).
      - calls       (из call_report)
      - abandoned   (из call_report)
      - waiting_calls (из summary_request, type='CALL', status='in', queue_duration_time IS NULL)
      - aht         (из call_report)
      - sl          (из call_report)
      - chats       (из summary_request, type='CHAT', status='in')
      - active_chats (из summary_request, type='CHAT', status='in', queue_duration_time IS NULL)
      - frt         (из chat_report)
      - rt          (из chat_report)
    """
    import datetime
    now = datetime.datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # calls (все входящие + bрошенные, из call_report)
    cursor.execute("""
        SELECT COUNT(*) AS total_calls
        FROM call_report
        WHERE (type = 'in' OR type='abandon')
          AND enter_queue_date >= %s
    """, (start_of_day,))
    row_calls = cursor.fetchone()
    total_calls = row_calls["total_calls"] if row_calls and row_calls["total_calls"] else 0

    # abandoned (только bрошенные)
    cursor.execute("""
        SELECT COUNT(*) AS total_abandoned
        FROM call_report
        WHERE type='abandon'
          AND enter_queue_date >= %s
    """, (start_of_day,))
    row_abandoned = cursor.fetchone()
    total_abandoned = row_abandoned["total_abandoned"] if row_abandoned and row_abandoned["total_abandoned"] else 0

    # waiting_calls (summary_request, type='CALL', status='in', queue_duration_time IS NULL)
    cursor.execute("""
        SELECT COUNT(*) AS waiting_calls
        FROM summary_request
        WHERE type='CALL'
          AND status='in'
          AND created_date >= %s
          AND queue_duration_time IS NULL
    """, (start_of_day,))
    row_waiting = cursor.fetchone()
    waiting_calls = row_waiting["waiting_calls"] if row_waiting and row_waiting["waiting_calls"] else 0

    # AHT (call_report, средняя длительность)
    cursor.execute("""
        SELECT ROUND(AVG(call_duration), 2) AS avg_call_duration
        FROM call_report
        WHERE enter_queue_date >= %s
          AND type='in'
    """, (start_of_day,))
    row_aht = cursor.fetchone()
    avg_aht = row_aht["avg_call_duration"] if row_aht and row_aht["avg_call_duration"] else 0

    # SL (уровень сервиса)
    cursor.execute("""
        SELECT
          ROUND(
            SUM(CASE WHEN queue_wait_time <= 20 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2
          ) AS sl
        FROM call_report
        WHERE enter_queue_date >= %s
          AND type='in'
          AND queue_name='m10'
    """, (start_of_day,))
    row_sl = cursor.fetchone()
    sl_value = row_sl["sl"] if row_sl and row_sl["sl"] else 0

    # chats (из summary_request, type='CHAT', status='in')
    cursor.execute("""
        SELECT COUNT(*) AS total_chats
        FROM summary_request
        WHERE type='CHAT'
          AND status='in'
          AND created_date >= %s
    """, (start_of_day,))
    row_chats = cursor.fetchone()
    total_chats = row_chats["total_chats"] if row_chats and row_chats["total_chats"] else 0

    # active_chats (из summary_request, type='CHAT', status='in', queue_duration_time IS NULL)
    cursor.execute("""
        SELECT COUNT(*) AS active_chats
        FROM summary_request
        WHERE type='CHAT'
          AND status='in'
          AND created_date >= %s
          AND queue_duration_time IS NULL
    """, (start_of_day,))
    row_active = cursor.fetchone()
    active_chats = row_active["active_chats"] if row_active and row_active["active_chats"] else 0

    # frt (из chat_report)
    cursor.execute("""
        SELECT ROUND(AVG(chat_frt), 2) AS avg_chat_frt
        FROM chat_report
        WHERE assign_date >= %s
    """, (start_of_day,))
    row_frt = cursor.fetchone()
    avg_frt = row_frt["avg_chat_frt"] if row_frt and row_frt["avg_chat_frt"] else 0

    # rt (из chat_report)
    cursor.execute("""
        SELECT ROUND(AVG(resolution_time_avg), 2) AS resolution_time_avg
        FROM chat_report
        WHERE assign_date >= %s
    """, (start_of_day,))
    row_rt = cursor.fetchone()
    avg_rt = row_rt["resolution_time_avg"] if row_rt and row_rt["resolution_time_avg"] else 0

    connection.close()

    return jsonify({
        "calls": total_calls,
        "abandoned": total_abandoned,
        "waiting_calls": waiting_calls,
        "aht": avg_aht,
        "sl": sl_value,
        "chats": total_chats,
        "active_chats": active_chats,
        "frt": avg_frt,
        "rt": avg_rt
    })

    data = execute_query(query, (start_of_day,))
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
