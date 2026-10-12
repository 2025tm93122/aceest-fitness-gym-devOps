from flask import Flask, jsonify, render_template_string, request, redirect, url_for
import os
import sqlite3
from datetime import datetime, date

app = Flask(__name__)
DB_NAME = os.environ.get('DATABASE_PATH', 'aceest_fitness.db')

PROGRAMS = {
    'Fat Loss (FL) – 3 day': {'factor': 22, 'desc': '3-day full-body fat loss'},
    'Fat Loss (FL) – 5 day': {'factor': 24, 'desc': '5-day split, higher volume fat loss'},
    'Muscle Gain (MG) – PPL': {'factor': 35, 'desc': 'Push/Pull/Legs hypertrophy'},
    'Beginner (BG)': {'factor': 26, 'desc': '3-day simple beginner full-body'},
}


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            age INTEGER,
            height REAL,
            weight REAL,
            program TEXT,
            calories INTEGER,
            target_weight REAL,
            target_adherence INTEGER
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            workout_type TEXT,
            duration_min INTEGER,
            notes TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            name TEXT,
            sets INTEGER,
            reps INTEGER,
            weight REAL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            weight REAL,
            waist REAL,
            bodyfat REAL
        )
    ''')
    conn.commit()
    conn.close()


def calculate_bmi(height_cm, weight_kg):
    if height_cm <= 0 or weight_kg <= 0:
        return None

    bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 1)

    if bmi < 18.5:
        category = 'Underweight'
        risk = 'Potential nutrient deficiency, low energy.'
    elif bmi < 25:
        category = 'Normal'
        risk = 'Low risk if active and strong.'
    elif bmi < 30:
        category = 'Overweight'
        risk = 'Moderate risk; focus on adherence and progressive activity.'
    else:
        category = 'Obese'
        risk = 'Higher risk; prioritize fat loss, consistency, and supervision.'

    return {
        'bmi': bmi,
        'category': category,
        'risk': risk,
    }


def parse_float(value, default=0.0):
    try:
        return float(value) if value not in (None, '') else default
    except (TypeError, ValueError):
        return default


def parse_int(value, default=0):
    try:
        return int(float(value)) if value not in (None, '') else default
    except (TypeError, ValueError):
        return default


def html_page(title, body):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{ margin:0; font-family:Arial,Helvetica,sans-serif; background:#1a1a1a; color:#fff; }}
.header {{ background:#d4af37; color:#000; padding:24px; font-size:28px; font-weight:700; }}
.container {{ max-width:1250px; margin:0 auto; padding:20px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:18px; }}
.card {{ background:#222; border:1px solid #444; border-radius:10px; padding:18px; margin-bottom:18px; }}
label {{ display:block; margin:8px 0 5px; }}
input, select, textarea, button {{ width:100%; box-sizing:border-box; padding:10px; margin-bottom:10px; border-radius:6px; border:1px solid #666; }}
input, select, textarea {{ background:#333; color:#fff; }}
button, .btn {{ display:inline-block; background:#d4af37; color:#000; border:none; text-decoration:none; cursor:pointer; padding:10px 14px; border-radius:6px; }}
.secondary {{ background:#555; color:#fff; }}
.muted {{ color:#aaa; }}
.success {{ background:#153d22; border:1px solid #4d9b62; padding:12px; border-radius:6px; margin-bottom:16px; }}
.error {{ background:#503; border:1px solid #a66; padding:12px; border-radius:6px; margin-bottom:16px; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ border:1px solid #555; padding:8px; text-align:left; }}
th {{ background:#333; }}
.small {{ font-size:13px; color:#bbb; }}
</style>
</head>
<body>{body}</body>
</html>'''


def dashboard():
    conn = get_conn()
    clients = conn.execute('SELECT * FROM clients ORDER BY name').fetchall()
    progress = conn.execute('SELECT * FROM progress ORDER BY id').fetchall()
    workouts = conn.execute('SELECT * FROM workouts ORDER BY date DESC, id DESC').fetchall()
    metrics = conn.execute('SELECT * FROM metrics ORDER BY date DESC, id DESC').fetchall()
    conn.close()

    client_options = ''.join(
        f'<option value="{row["name"]}">{row["name"]}</option>' for row in clients
    )

    client_rows = ''.join(
        f'<tr><td>{row["name"]}</td><td>{row["age"] or ""}</td>'
        f'<td>{row["height"] or ""}</td><td>{row["weight"] or ""}</td>'
        f'<td>{row["program"] or ""}</td><td>{row["calories"] or ""}</td>'
        f'<td>{row["target_weight"] or ""}</td><td>{row["target_adherence"] or ""}</td></tr>'
        for row in clients
    )

    progress_rows = ''.join(
        f'<tr><td>{row["client_name"]}</td><td>{row["week"]}</td>'
        f'<td>{row["adherence"]}%</td></tr>'
        for row in progress
    )

    workout_rows = ''.join(
        f'<tr><td>{row["client_name"]}</td><td>{row["date"]}</td>'
        f'<td>{row["workout_type"]}</td><td>{row["duration_min"]}</td>'
        f'<td>{row["notes"] or ""}</td></tr>'
        for row in workouts
    )

    metric_rows = ''.join(
        f'<tr><td>{row["client_name"]}</td><td>{row["date"]}</td>'
        f'<td>{row["weight"]}</td><td>{row["waist"]}</td>'
        f'<td>{row["bodyfat"]}</td></tr>'
        for row in metrics
    )

    program_options = ''.join(f'<option value="{name}">{name}</option>' for name in PROGRAMS)

    body = f'''
<div class="header">ACEest Functional Fitness System</div>
<div class="container">
    <div class="card">
        <h2>Client Management</h2>
        <p class="small">Equivalent Flask web flow for the supplied v2.2.4 Tkinter client-management features.</p>
        <form method="post" action="/">
            <label>Name</label>
            <input name="name" required>
            <label>Age</label>
            <input name="age" type="number" min="0">
            <label>Height (cm)</label>
            <input name="height" type="number" step="0.1" min="0">
            <label>Weight (kg)</label>
            <input name="weight" type="number" step="0.1" min="0">
            <label>Program</label>
            <select name="program" required>{program_options}</select>
            <label>Target Weight (kg)</label>
            <input name="target_weight" type="number" step="0.1" min="0">
            <label>Target Adherence %</label>
            <input name="target_adherence" type="number" min="0" max="100">
            <button type="submit">Save Client</button>
        </form>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Weekly Progress</h2>
            <form method="post" action="/progress">
                <label>Client</label>
                <select name="client_name" required>{client_options}</select>
                <label>Adherence %</label>
                <input name="adherence" type="number" min="0" max="100" required>
                <button type="submit">Save Weekly Progress</button>
            </form>
            <table>
                <tr><th>Client</th><th>Week</th><th>Adherence</th></tr>
                {progress_rows or '<tr><td colspan="3">No progress data</td></tr>'}
            </table>
        </div>

        <div class="card">
            <h2>Workout Logging</h2>
            <form method="post" action="/workout">
                <label>Client</label>
                <select name="client_name" required>{client_options}</select>
                <label>Date</label>
                <input name="date" value="{date.today().isoformat()}" required>
                <label>Workout Type</label>
                <select name="workout_type" required>
                    <option>Strength</option>
                    <option>Hypertrophy</option>
                    <option>Conditioning</option>
                    <option>Mixed</option>
                    <option>Mobility</option>
                </select>
                <label>Duration (min)</label>
                <input name="duration_min" type="number" min="0" value="60" required>
                <label>Notes</label>
                <textarea name="notes"></textarea>
                <label>Exercise Name</label>
                <input name="exercise_name">
                <label>Sets</label>
                <input name="sets" type="number" min="0" value="3">
                <label>Reps</label>
                <input name="reps" type="number" min="0" value="10">
                <label>Exercise Weight (kg)</label>
                <input name="exercise_weight" type="number" min="0" step="0.1" value="0">
                <button type="submit">Log Workout</button>
            </form>
        </div>

        <div class="card">
            <h2>Body Metrics</h2>
            <form method="post" action="/metrics">
                <label>Client</label>
                <select name="client_name" required>{client_options}</select>
                <label>Date</label>
                <input name="date" value="{date.today().isoformat()}" required>
                <label>Weight (kg)</label>
                <input name="weight" type="number" step="0.1" min="0">
                <label>Waist (cm)</label>
                <input name="waist" type="number" step="0.1" min="0">
                <label>Bodyfat (%)</label>
                <input name="bodyfat" type="number" step="0.1" min="0">
                <button type="submit">Log Metrics</button>
            </form>
        </div>

        <div class="card">
            <h2>BMI & Risk Info</h2>
            <form method="post" action="/bmi">
                <label>Height (cm)</label>
                <input name="height" type="number" step="0.1" min="0" required>
                <label>Weight (kg)</label>
                <input name="weight" type="number" step="0.1" min="0" required>
                <button type="submit">Calculate BMI</button>
            </form>
        </div>
    </div>

    <div class="card">
        <h2>Clients</h2>
        <table>
            <tr><th>Name</th><th>Age</th><th>Height</th><th>Weight</th><th>Program</th><th>Calories</th><th>Target Weight</th><th>Target Adherence</th></tr>
            {client_rows or '<tr><td colspan="8">No clients saved</td></tr>'}
        </table>
    </div>

    <div class="card">
        <h2>Workout History</h2>
        <table>
            <tr><th>Client</th><th>Date</th><th>Type</th><th>Duration</th><th>Notes</th></tr>
            {workout_rows or '<tr><td colspan="5">No workouts logged</td></tr>'}
        </table>
    </div>

    <div class="card">
        <h2>Body Metrics History</h2>
        <table>
            <tr><th>Client</th><th>Date</th><th>Weight</th><th>Waist</th><th>Bodyfat</th></tr>
            {metric_rows or '<tr><td colspan="5">No body metrics logged</td></tr>'}
        </table>
    </div>
</div>
'''
    return html_page('ACEest Fitness & Performance', body)


@app.route('/', methods=['GET', 'POST'])
def home():
    """GET shows the dashboard; POST supports the original Save Client flow."""
    if request.method == 'POST':
        return save_client()
    return render_template_string(dashboard())


@app.get('/health')
def health():
    return jsonify(status='healthy')


@app.post('/client')
def client_route():
    return save_client()


@app.post('/api/clients')
def api_create_client():
    """JSON equivalent of the v2.2.4 Save Client action."""
    payload = request.get_json(silent=True) or request.form
    name = str(payload.get('name', '')).strip()
    if not name:
        return jsonify(error='Name is required'), 400

    program = str(payload.get('program', '')).strip()
    if program not in PROGRAMS:
        return jsonify(error='Valid program is required'), 400

    age = parse_int(payload.get('age'))
    height = parse_float(payload.get('height'))
    weight = parse_float(payload.get('weight'))
    target_weight = parse_float(payload.get('target_weight'))
    target_adherence = parse_int(payload.get('target_adherence'))
    calories = int(weight * PROGRAMS[program]['factor']) if weight > 0 else None

    conn = get_conn()
    conn.execute('''
        INSERT OR REPLACE INTO clients
        (name, age, height, weight, program, calories, target_weight, target_adherence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, age, height, weight, program, calories, target_weight or None, target_adherence or None))
    conn.commit()
    row = conn.execute('SELECT * FROM clients WHERE name=?', (name,)).fetchone()
    conn.close()

    return jsonify(dict(row)), 201


def save_client():
    if request.method == 'POST' and request.path == '/api/clients':
        return api_create_client()

    source = request.form
    name = source.get('name', '').strip()
    program = source.get('program', '').strip()

    if not name or program not in PROGRAMS:
        return render_template_string(
            html_page('Error', '<div class="container"><div class="error">Name and a valid program are required.</div><a class="btn" href="/">Back</a></div>'),
            400,
        )

    age = parse_int(source.get('age'))
    height = parse_float(source.get('height'))
    weight = parse_float(source.get('weight'))
    target_weight = parse_float(source.get('target_weight'))
    target_adherence = parse_int(source.get('target_adherence'))
    calories = int(weight * PROGRAMS[program]['factor']) if weight > 0 else None

    conn = get_conn()
    conn.execute('''
        INSERT OR REPLACE INTO clients
        (name, age, height, weight, program, calories, target_weight, target_adherence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, age, height, weight, program, calories, target_weight or None, target_adherence or None))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))


@app.post('/progress')
def add_progress():
    payload = request.form if request.form else (request.get_json(silent=True) or {})
    client_name = str(payload.get('client_name', '')).strip()
    adherence = parse_int(payload.get('adherence'))
    if not client_name:
        return jsonify(error='client_name is required'), 400

    conn = get_conn()
    conn.execute(
        'INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)',
        (client_name, datetime.now().strftime('Week %U - %Y'), adherence),
    )
    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify(message='Weekly progress logged', client_name=client_name, adherence=adherence), 201
    return redirect(url_for('home'))


@app.post('/workout')
def add_workout():
    payload = request.form if request.form else (request.get_json(silent=True) or {})
    client_name = str(payload.get('client_name', '')).strip()
    workout_date = str(payload.get('date', '')).strip() or date.today().isoformat()
    workout_type = str(payload.get('workout_type', '')).strip()
    duration = parse_int(payload.get('duration_min'))
    notes = str(payload.get('notes', '')).strip()

    if not client_name or not workout_type:
        return jsonify(error='client_name and workout_type are required'), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) VALUES (?, ?, ?, ?, ?)',
        (client_name, workout_date, workout_type, duration, notes),
    )
    workout_id = cur.lastrowid

    exercise_name = str(payload.get('exercise_name', '')).strip()
    if exercise_name:
        cur.execute(
            'INSERT INTO exercises (workout_id, name, sets, reps, weight) VALUES (?, ?, ?, ?, ?)',
            (
                workout_id,
                exercise_name,
                parse_int(payload.get('sets'), 3),
                parse_int(payload.get('reps'), 10),
                parse_float(payload.get('exercise_weight')),
            ),
        )

    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify(message='Workout logged successfully', workout_id=workout_id), 201
    return redirect(url_for('home'))


@app.post('/metrics')
def add_metrics():
    payload = request.form if request.form else (request.get_json(silent=True) or {})
    client_name = str(payload.get('client_name', '')).strip()
    metric_date = str(payload.get('date', '')).strip() or date.today().isoformat()
    weight = parse_float(payload.get('weight'))
    waist = parse_float(payload.get('waist'))
    bodyfat = parse_float(payload.get('bodyfat'))

    if not client_name:
        return jsonify(error='client_name is required'), 400

    conn = get_conn()
    conn.execute(
        'INSERT INTO metrics (client_name, date, weight, waist, bodyfat) VALUES (?, ?, ?, ?, ?)',
        (client_name, metric_date, weight, waist, bodyfat),
    )
    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify(message='Metrics logged successfully', client_name=client_name), 201
    return redirect(url_for('home'))


@app.post('/bmi')
def bmi():
    payload = request.form if request.form else (request.get_json(silent=True) or {})
    height = parse_float(payload.get('height'))
    weight = parse_float(payload.get('weight'))
    result = calculate_bmi(height, weight)

    if not result:
        if request.is_json:
            return jsonify(error='Valid height and weight are required'), 400
        body = '<div class="container"><div class="error">Enter valid height and weight.</div><a class="btn" href="/">Back</a></div>'
        return render_template_string(html_page('BMI Info', body)), 400

    if request.is_json:
        return jsonify(result)

    body = (
        '<div class="header">BMI Info</div>'
        '<div class="container">'
        f'<div class="success"><h2>BMI: {result["bmi"]}</h2>'
        f'<p>Category: {result["category"]}</p>'
        f'<p>Risk note: {result["risk"]}</p></div>'
        '<a class="btn" href="/">Back</a></div>'
    )
    return render_template_string(html_page('BMI Info', body))


@app.get('/api/bmi/<client_name>')
def api_bmi_for_client(client_name):
    """JSON BMI endpoint for the supplied client, fixing the missing route used by the previous conversion."""
    conn = get_conn()
    client = conn.execute(
        'SELECT name, height, weight FROM clients WHERE name=?',
        (client_name,),
    ).fetchone()
    conn.close()

    if not client:
        return jsonify(error='Client not found'), 404

    result = calculate_bmi(client['height'] or 0, client['weight'] or 0)
    if not result:
        return jsonify(error='Client has missing or invalid height/weight'), 400

    return jsonify({'client': client['name'], **result})


@app.get('/api/clients')
def api_clients():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM clients ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.get('/api/clients/<client_name>')
def api_get_client(client_name):
    conn = get_conn()
    row = conn.execute('SELECT * FROM clients WHERE name=?', (client_name,)).fetchone()
    conn.close()
    if not row:
        return jsonify(error='Client not found'), 404
    return jsonify(dict(row))


@app.get('/api/progress/<client_name>')
def api_progress(client_name):
    conn = get_conn()
    rows = conn.execute(
        'SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id',
        (client_name,),
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.get('/api/workouts/<client_name>')
def api_workouts(client_name):
    conn = get_conn()
    rows = conn.execute(
        'SELECT date, workout_type, duration_min, notes FROM workouts WHERE client_name=? ORDER BY date DESC, id DESC',
        (client_name,),
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.get('/api/metrics/<client_name>')
def api_metrics(client_name):
    conn = get_conn()
    rows = conn.execute(
        'SELECT date, weight, waist, bodyfat FROM metrics WHERE client_name=? ORDER BY date DESC, id DESC',
        (client_name,),
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
