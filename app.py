from flask import Flask, jsonify, render_template_string, request
import os
import sqlite3
from datetime import datetime, date


app = Flask(__name__)

DB_NAME = os.environ.get("DATABASE_PATH", "aceest_fitness.db")


PROGRAMS = {
    "Fat Loss (FL) – 3 day": {
        "factor": 22,
        "desc": "3-day full-body fat loss",
    },
    "Fat Loss (FL) – 5 day": {
        "factor": 24,
        "desc": "5-day split, higher volume fat loss",
    },
    "Muscle Gain (MG) – PPL": {
        "factor": 35,
        "desc": "Push/Pull/Legs hypertrophy",
    },
    "Beginner (BG)": {
        "factor": 26,
        "desc": "3-day simple beginner full-body",
    },
}


def conn():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = conn()
    cursor = connection.cursor()

    cursor.execute(
        """
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
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            workout_type TEXT,
            duration_min INTEGER,
            notes TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            name TEXT,
            sets INTEGER,
            reps INTEGER,
            weight REAL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            weight REAL,
            waist REAL,
            bodyfat REAL
        )
        """
    )

    connection.commit()
    connection.close()


def parse_int(value, default=0):
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def bmi_info(height, weight):
    if height <= 0 or weight <= 0:
        return None

    bmi = round(weight / ((height / 100) ** 2), 1)

    if bmi < 18.5:
        return (
            bmi,
            "Underweight",
            "Potential nutrient deficiency, low energy.",
        )

    if bmi < 25:
        return (
            bmi,
            "Normal",
            "Low risk if active and strong.",
        )

    if bmi < 30:
        return (
            bmi,
            "Overweight",
            "Moderate risk; focus on adherence and progressive activity.",
        )

    return (
        bmi,
        "Obese",
        "Higher risk; prioritize fat loss, consistency, and supervision.",
    )


def html(title, body):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>

<style>
body {{
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #1a1a1a;
    color: #fff;
}}

.header {{
    background: #d4af37;
    color: #000;
    padding: 24px;
    font-size: 28px;
    font-weight: 700;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
}}

.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 18px;
}}

.card {{
    background: #222;
    border: 1px solid #444;
    border-radius: 10px;
    padding: 18px;
    margin-bottom: 18px;
}}

label {{
    display: block;
    margin: 10px 0 5px;
}}

input,
select,
textarea,
button {{
    width: 100%;
    box-sizing: border-box;
    padding: 10px;
    margin-bottom: 10px;
    border-radius: 6px;
    border: 1px solid #666;
}}

input,
select,
textarea {{
    background: #333;
    color: #fff;
}}

button,
.btn {{
    display: inline-block;
    background: #d4af37;
    color: #000;
    border: none;
    text-decoration: none;
    cursor: pointer;
    padding: 10px 14px;
    border-radius: 6px;
}}

.alert {{
    background: #503;
    border: 1px solid #a66;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 16px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th,
td {{
    border: 1px solid #555;
    padding: 8px;
    text-align: left;
}}

th {{
    background: #333;
}}
</style>
</head>

<body>
{body}
</body>
</html>
"""


def render():
    connection = conn()

    clients = connection.execute(
        "SELECT * FROM clients ORDER BY name"
    ).fetchall()

    progress = connection.execute(
        "SELECT * FROM progress ORDER BY id"
    ).fetchall()

    workouts = connection.execute(
        "SELECT * FROM workouts ORDER BY date DESC, id DESC"
    ).fetchall()

    metrics = connection.execute(
        "SELECT * FROM metrics ORDER BY date DESC, id DESC"
    ).fetchall()

    connection.close()

    client_options = "".join(
        f'<option value="{row["name"]}">{row["name"]}</option>'
        for row in clients
    )

    program_options = "".join(
        f'<option value="{program}">{program}</option>'
        for program in PROGRAMS
    )

    client_rows = "".join(
        (
            f'<tr><td>{row["name"]}</td>'
            f'<td>{row["age"] or ""}</td>'
            f'<td>{row["height"] or ""}</td>'
            f'<td>{row["weight"] or ""}</td>'
            f'<td>{row["program"] or ""}</td>'
            f'<td>{row["calories"] or ""}</td>'
            f'<td>{row["target_weight"] or ""}</td>'
            f'<td>{row["target_adherence"] or ""}</td></tr>'
        )
        for row in clients
    )

    progress_rows = "".join(
        (
            f'<tr><td>{row["client_name"]}</td>'
            f'<td>{row["week"]}</td>'
            f'<td>{row["adherence"]}%</td></tr>'
        )
        for row in progress
    )

    workout_rows = "".join(
        (
            f'<tr><td>{row["client_name"]}</td>'
            f'<td>{row["date"]}</td>'
            f'<td>{row["workout_type"]}</td>'
            f'<td>{row["duration_min"]}</td>'
            f'<td>{row["notes"] or ""}</td></tr>'
        )
        for row in workouts
    )

    metric_rows = "".join(
        (
            f'<tr><td>{row["client_name"]}</td>'
            f'<td>{row["date"]}</td>'
            f'<td>{row["weight"]}</td>'
            f'<td>{row["waist"]}</td>'
            f'<td>{row["bodyfat"]}</td></tr>'
        )
        for row in metrics
    )

    body = f"""
<div class="header">ACEest Functional Fitness System</div>

<div class="container">

<div class="grid">

<div class="card">
<h2>Client Management</h2>

<form method="post" action="/client">

<label>Name</label>
<input name="name" required>

<label>Age</label>
<input name="age" type="number">

<label>Height (cm)</label>
<input name="height" type="number" step="0.1">

<label>Weight (kg)</label>
<input name="weight" type="number" step="0.1">

<label>Program</label>
<select name="program">
{program_options}
</select>

<label>Target Weight (kg)</label>
<input name="target_weight" type="number" step="0.1">

<label>Target Adherence %</label>
<input name="target_adherence" type="number" min="0" max="100">

<button type="submit">Save Client</button>

</form>
</div>


<div class="card">

<h2>Weekly Progress</h2>

<form method="post" action="/progress">

<label>Client</label>
<select name="client_name">
{client_options}
</select>

<label>Adherence %</label>
<input name="adherence" type="number" min="0" max="100">

<button type="submit">Save Weekly Progress</button>

</form>

<table>
<tr>
<th>Client</th>
<th>Week</th>
<th>Adherence</th>
</tr>

{progress_rows}

</table>
</div>


<div class="card">

<h2>Workout Logging</h2>

<form method="post" action="/workout">

<label>Client</label>
<select name="client_name">
{client_options}
</select>

<label>Date</label>
<input name="date" value="{date.today().isoformat()}">

<label>Workout Type</label>
<select name="workout_type">
<option>Strength</option>
<option>Hypertrophy</option>
<option>Conditioning</option>
<option>Mixed</option>
<option>Mobility</option>
</select>

<label>Duration (min)</label>
<input name="duration_min" value="60">

<label>Notes</label>
<textarea name="notes"></textarea>

<button type="submit">Log Workout</button>

</form>
</div>


<div class="card">

<h2>Body Metrics</h2>

<form method="post" action="/metrics">

<label>Client</label>
<select name="client_name">
{client_options}
</select>

<label>Date</label>
<input name="date" value="{date.today().isoformat()}">

<label>Weight (kg)</label>
<input name="weight" step="0.1">

<label>Waist (cm)</label>
<input name="waist" step="0.1">

<label>Bodyfat (%)</label>
<input name="bodyfat" step="0.1">

<button type="submit">Log Metrics</button>

</form>
</div>

</div>


<div class="card">

<h2>Clients</h2>

<table>

<tr>
<th>Name</th>
<th>Age</th>
<th>Height</th>
<th>Weight</th>
<th>Program</th>
<th>Calories</th>
<th>Target Weight</th>
<th>Target Adherence</th>
</tr>

{client_rows}

</table>
</div>


<div class="card">

<h2>Workout History</h2>

<table>

<tr>
<th>Client</th>
<th>Date</th>
<th>Type</th>
<th>Duration</th>
<th>Notes</th>
</tr>

{workout_rows}

</table>
</div>


<div class="card">

<h2>Body Metrics History</h2>

<table>

<tr>
<th>Client</th>
<th>Date</th>
<th>Weight</th>
<th>Waist</th>
<th>Bodyfat</th>
</tr>

{metric_rows}

</table>
</div>


<div class="card">

<h2>BMI & Risk Info</h2>

<form method="post" action="/bmi">

<label>Height (cm)</label>
<input name="height">

<label>Weight (kg)</label>
<input name="weight">

<button type="submit">Calculate BMI</button>

</form>

</div>

</div>
"""

    return html(
        "ACEest Fitness & Performance",
        body,
    )


@app.get("/health")
def health():
    return jsonify(status="healthy")


@app.get("/")
def home():
    return render_template_string(render())


@app.post("/client")
def client():
    form = request.form

    name = form.get("name", "").strip()
    program = form.get("program", "").strip()

    if not name or program not in PROGRAMS:
        return (
            render_template_string(
                html(
                    "Error",
                    (
                        '<div class="container">'
                        '<div class="alert">'
                        "Name and a valid program are required."
                        "</div>"
                        '<a class="btn" href="/">Back</a>'
                        "</div>"
                    ),
                )
            ),
            400,
        )

    age = parse_int(form.get("age"))
    height = parse_float(form.get("height"))
    weight = parse_float(form.get("weight"))
    target_weight = parse_float(form.get("target_weight"))
    target_adherence = parse_int(form.get("target_adherence"))

    calories = (
        int(weight * PROGRAMS[program]["factor"])
        if weight > 0
        else None
    )

    connection = conn()

    connection.execute(
        """
        INSERT OR REPLACE INTO clients
        (
            name,
            age,
            height,
            weight,
            program,
            calories,
            target_weight,
            target_adherence
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            age,
            height,
            weight,
            program,
            calories,
            target_weight or None,
            target_adherence or None,
        ),
    )

    connection.commit()
    connection.close()

    return render_template_string(render())


@app.post("/progress")
def progress_add():
    form = request.form

    client_name = form.get("client_name", "").strip()

    if not client_name:
        return jsonify(error="client_name is required"), 400

    adherence = parse_int(form.get("adherence"))

    connection = conn()

    connection.execute(
        """
        INSERT INTO progress
        (client_name, week, adherence)
        VALUES (?, ?, ?)
        """,
        (
            client_name,
            datetime.now().strftime("Week %U - %Y"),
            adherence,
        ),
    )

    connection.commit()
    connection.close()

    return render_template_string(render())


@app.post("/workout")
def workout_add():
    form = request.form

    client_name = form.get("client_name", "").strip()
    workout_type = form.get("workout_type", "").strip()

    if not client_name or not workout_type:
        return (
            jsonify(
                error="client_name and workout_type are required"
            ),
            400,
        )

    workout_date = (
        form.get("date", "").strip()
        or date.today().isoformat()
    )

    duration = parse_int(form.get("duration_min"))
    notes = form.get("notes", "").strip()

    connection = conn()

    connection.execute(
        """
        INSERT INTO workouts
        (
            client_name,
            date,
            workout_type,
            duration_min,
            notes
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            client_name,
            workout_date,
            workout_type,
            duration,
            notes,
        ),
    )

    connection.commit()
    connection.close()

    return render_template_string(render())


@app.post("/metrics")
def metrics_add():
    form = request.form

    client_name = form.get("client_name", "").strip()

    if not client_name:
        return jsonify(error="client_name is required"), 400

    metric_date = (
        form.get("date", "").strip()
        or date.today().isoformat()
    )

    weight = parse_float(form.get("weight"))
    waist = parse_float(form.get("waist"))
    bodyfat = parse_float(form.get("bodyfat"))

    connection = conn()

    connection.execute(
        """
        INSERT INTO metrics
        (
            client_name,
            date,
            weight,
            waist,
            bodyfat
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            client_name,
            metric_date,
            weight,
            waist,
            bodyfat,
        ),
    )

    connection.commit()
    connection.close()

    return render_template_string(render())


@app.post("/bmi")
def bmi():
    height = parse_float(request.form.get("height"))
    weight = parse_float(request.form.get("weight"))

    info = bmi_info(height, weight)

    if not info:
        message = "Invalid height or weight."
        status = 400
    else:
        message = (
            f"BMI: {info[0]} ({info[1]}) "
            f"- Risk note: {info[2]}"
        )
        status = 200

    page = html(
        "BMI Info",
        (
            '<div class="header">BMI Info</div>'
            '<div class="container">'
            f'<div class="alert">{message}</div>'
            '<a class="btn" href="/">Back</a>'
            "</div>"
        ),
    )

    return render_template_string(page), status


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000)
