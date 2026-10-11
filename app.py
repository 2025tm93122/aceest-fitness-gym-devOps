from flask import Flask, jsonify, request
from markupsafe import escape
import sqlite3
from datetime import datetime


app = Flask(__name__)


def html(title, body):
    """Build a small self-contained HTML page for the Flask UI."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{ margin:0; font-family:Arial,Helvetica,sans-serif; background:#1a1a1a; color:#fff; }}
.header {{ background:#d4af37; color:#000; padding:24px; font-size:28px; font-weight:700; }}
.container {{ max-width:1200px; margin:0 auto; padding:24px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:18px; }}
.card {{ background:#222; border:1px solid #444; border-radius:10px; padding:18px; margin-bottom:18px; }}
label {{ display:block; margin:10px 0 5px; }}
input, select, button {{ width:100%; box-sizing:border-box; padding:10px; margin-bottom:10px; border-radius:6px; border:1px solid #666; }}
input, select {{ background:#333; color:#fff; }}
button, .btn {{ display:inline-block; background:#d4af37; color:#000; border:none; text-decoration:none; cursor:pointer; padding:10px 14px; border-radius:6px; margin:4px 4px 4px 0; }}
.secondary {{ background:#555; color:#fff; }}
.alert {{ background:#503; border:1px solid #a66; padding:12px; border-radius:6px; margin-bottom:16px; }}
.metric {{ font-weight:700; margin-top:12px; color:#d4af37; }}
.muted {{ color:#aaa; }}
pre {{ white-space:pre-wrap; line-height:1.5; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ border:1px solid #555; padding:8px; text-align:left; }}
th {{ background:#333; }}
svg {{ width:100%; height:auto; background:#111; border-radius:8px; }}
</style>
</head>
<body>{body}</body>
</html>"""


DB_NAME = 'aceest_fitness.db'

PROGRAMS = {
    "Fat Loss (FL)": {
        "factor": 22
    },
    "Muscle Gain (MG)": {
        "factor": 35
    },
    "Beginner (BG)": {
        "factor": 26
    }
}


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        'CREATE TABLE IF NOT EXISTS clients '
        '(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'name TEXT UNIQUE, '
        'age INTEGER, '
        'weight REAL, '
        'program TEXT, '
        'calories INTEGER)'
    )

    cur.execute(
        'CREATE TABLE IF NOT EXISTS progress '
        '(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'client_name TEXT, '
        'week TEXT, '
        'adherence INTEGER)'
    )

    conn.commit()
    conn.close()


init_db()


@app.get('/health')
def health():
    return jsonify(status='healthy')


def save_client():
    """Validate and save client information."""
    name = request.form.get('name', '').strip()
    program = request.form.get('program', '').strip()

    if not name or program not in PROGRAMS:
        return 'Name and Program required'

    try:
        age = int(request.form.get('age') or 0)
        weight = float(request.form.get('weight') or 0)
    except ValueError:
        return 'Age and weight must be numeric'

    calories = int(weight * PROGRAMS[program]['factor'])

    conn = get_conn()

    conn.execute(
        'INSERT OR REPLACE INTO clients '
        '(name, age, weight, program, calories) '
        'VALUES (?, ?, ?, ?, ?)',
        (name, age, weight, program, calories)
    )

    conn.commit()
    conn.close()

    return 'Client data saved'


def save_progress():
    """Validate and save weekly progress."""
    name = request.form.get('name', '').strip()

    if not name:
        return 'Enter client name first'

    try:
        adherence = int(float(request.form.get('adherence') or 0))
    except ValueError:
        adherence = 0

    week = datetime.now().strftime('Week %U - %Y')

    conn = get_conn()

    conn.execute(
        'INSERT INTO progress '
        '(client_name, week, adherence) '
        'VALUES (?, ?, ?)',
        (name, week, adherence)
    )

    conn.commit()
    conn.close()

    return 'Weekly progress logged'


def load_dashboard_data():
    """Load clients and progress records from SQLite."""
    conn = get_conn()

    clients = conn.execute(
        'SELECT * FROM clients ORDER BY name'
    ).fetchall()

    progress = conn.execute(
        'SELECT * FROM progress ORDER BY id DESC'
    ).fetchall()

    conn.close()

    return clients, progress


def build_client_rows(clients):
    """Create HTML rows for client data."""
    return ''.join(
        f'<tr>'
        f'<td>{escape(row["name"])}</td>'
        f'<td>{row["age"]}</td>'
        f'<td>{row["weight"]}</td>'
        f'<td>{escape(row["program"])}</td>'
        f'<td>{row["calories"]}</td>'
        f'</tr>'
        for row in clients
    )


def build_progress_rows(progress):
    """Create HTML rows for progress data."""
    return ''.join(
        f'<tr>'
        f'<td>{escape(row["client_name"])}</td>'
        f'<td>{escape(row["week"])}</td>'
        f'<td>{row["adherence"]}%</td>'
        f'</tr>'
        for row in progress
    )


def render_dashboard(message=''):
    """Render the main ACEest dashboard."""
    clients, progress = load_dashboard_data()

    rows = build_client_rows(clients)
    prows = build_progress_rows(progress)

    options = ''.join(
        f'<option value="{escape(name)}">{escape(name)}</option>'
        for name in PROGRAMS
    )

    alert = (
        f'<div class="alert">{escape(message)}</div>'
        if message
        else ''
    )

    body = f"""
<div class="header">
    ACEest Functional Fitness System
</div>

<div class="container">

{alert}

<div class="grid">

<div class="card">
<h2>Client Management</h2>

<form method="post">

<input type="hidden" name="action" value="save">

<label>Name</label>
<input name="name">

<label>Age</label>
<input name="age" type="number">

<label>Weight (kg)</label>
<input name="weight" type="number" step="0.1">

<label>Program</label>
<select name="program">
{options}
</select>

<button>Save Client</button>

</form>
</div>


<div class="card">

<h2>Weekly Progress</h2>

<form method="post">

<input type="hidden" name="action" value="progress">

<label>Client Name</label>
<input name="name">

<label>Adherence %</label>
<input
    name="adherence"
    type="number"
    min="0"
    max="100"
>

<button>Save Progress</button>

</form>
</div>

</div>


<div class="card">

<h2>Clients</h2>

<table>

<tr>
<th>Name</th>
<th>Age</th>
<th>Weight</th>
<th>Program</th>
<th>Calories</th>
</tr>

{rows}

</table>

</div>


<div class="card">

<h2>Progress</h2>

<table>

<tr>
<th>Client</th>
<th>Week</th>
<th>Adherence</th>
</tr>

{prows}

</table>

</div>

</div>
"""

    return html('ACEest v2.0.1', body)


@app.route('/', methods=['GET', 'POST'])
def home():
    """Display the dashboard and route POST actions."""
    if request.method != 'POST':
        return render_dashboard()

    action = request.form.get('action')

    if action == 'save':
        return render_dashboard(save_client())

    if action == 'progress':
        return render_dashboard(save_progress())

    return render_dashboard()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
