from datetime import datetime
import sqlite3

from flask import Flask, jsonify, request
from markupsafe import escape


app = Flask(__name__)

DB_NAME = 'aceest_fitness.db'

PROGRAMS = {
    'Fat Loss (FL)': {'factor': 22},
    'Muscle Gain (MG)': {'factor': 35},
    'Beginner (BG)': {'factor': 26},
}


def html(title, body):
    """Build a small self-contained HTML page for the Flask UI."""
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
input, select, button {{
    width: 100%;
    box-sizing: border-box;
    padding: 10px;
    margin-bottom: 10px;
    border-radius: 6px;
    border: 1px solid #666;
}}
input, select {{
    background: #333;
    color: #fff;
}}
button, .btn {{
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
.muted {{
    color: #aaa;
}}
table {{
    width: 100%;
    border-collapse: collapse;
}}
th, td {{
    border: 1px solid #555;
    padding: 8px;
    text-align: left;
}}
th {{
    background: #333;
}}
svg {{
    width: 100%;
    height: auto;
    background: #111;
    border-radius: 8px;
}}
</style>
</head>
<body>
{body}
</body>
</html>"""


def get_conn():
    """Create a SQLite database connection."""
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Create application tables when they do not already exist."""
    connection = get_conn()

    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            age INTEGER,
            weight REAL,
            program TEXT,
            calories INTEGER
        )
        '''
    )

    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
        )
        '''
    )

    connection.commit()
    connection.close()


init_db()


@app.get('/health')
def health():
    """Return application health information."""
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

    connection = get_conn()

    connection.execute(
        '''
        INSERT OR REPLACE INTO clients
        (name, age, weight, program, calories)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (name, age, weight, program, calories),
    )

    connection.commit()
    connection.close()

    return 'Client data saved'


def save_progress():
    """Validate and save weekly adherence progress."""
    name = request.form.get('name', '').strip()

    if not name:
        return 'Enter client name first'

    try:
        adherence = int(float(request.form.get('adherence') or 0))
    except ValueError:
        return 'Adherence must be numeric'

    adherence = max(0, min(100, adherence))
    week = datetime.now().strftime('Week %U - %Y')

    connection = get_conn()

    connection.execute(
        '''
        INSERT INTO progress
        (client_name, week, adherence)
        VALUES (?, ?, ?)
        ''',
        (name, week, adherence),
    )

    connection.commit()
    connection.close()

    return 'Weekly progress logged'


def load_data():
    """Load client and progress data for the dashboard."""
    connection = get_conn()

    clients = connection.execute(
        'SELECT * FROM clients ORDER BY name'
    ).fetchall()

    progress = connection.execute(
        'SELECT * FROM progress ORDER BY id'
    ).fetchall()

    connection.close()

    return clients, progress


def chart(rows):
    """Generate a simple SVG adherence chart."""
    if not rows:
        return '<p class="muted">No progress data available.</p>'

    values = [int(row['adherence']) for row in rows]

    width = 720
    height = 280
    padding = 40
    maximum = max(100, max(values))

    step = (
        (width - (2 * padding)) / max(1, len(values) - 1)
    )

    points = []

    for index, value in enumerate(values):
        x_position = padding + (index * step)
        y_position = (
            height
            - padding
            - (value / maximum) * (height - (2 * padding))
        )

        points.append(
            f'{x_position:.1f},{y_position:.1f}'
        )

    circles = ''.join(
        (
            f'<circle '
            f'cx="{point.split(",")[0]}" '
            f'cy="{point.split(",")[1]}" '
            f'r="5" fill="#d4af37"/>'
        )
        for point in points
    )

    point_text = ' '.join(points)

    return (
        f'<svg viewBox="0 0 {width} {height}">'
        f'<polyline points="{point_text}" '
        f'fill="none" stroke="#d4af37" stroke-width="3"/>'
        f'{circles}'
        f'</svg>'
    )


def build_client_table(clients):
    """Generate table rows for saved clients."""
    return ''.join(
        (
            '<tr>'
            f'<td>{escape(row["name"])}</td>'
            f'<td>{escape(row["program"])}</td>'
            f'<td>{row["calories"]}</td>'
            '</tr>'
        )
        for row in clients
    )


def build_progress_table(rows):
    """Generate table rows for saved progress."""
    return ''.join(
        (
            '<tr>'
            f'<td>{escape(row["client_name"])}</td>'
            f'<td>{escape(row["week"])}</td>'
            f'<td>{row["adherence"]}%</td>'
            '</tr>'
        )
        for row in rows
    )


def build_program_options():
    """Generate program selection options."""
    return ''.join(
        f'<option value="{escape(name)}">{escape(name)}</option>'
        for name in PROGRAMS
    )


def render_dashboard(message=''):
    """Render the ACEest v2.2.1 dashboard."""
    clients, progress = load_data()

    client_table = build_client_table(clients)
    progress_table = build_progress_table(progress)
    program_options = build_program_options()
    progress_chart = chart(progress)

    alert = ''

    if message:
        alert = f'<div class="alert">{escape(message)}</div>'

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

<input
    type="hidden"
    name="action"
    value="save"
>

<label>Name</label>
<input name="name">

<label>Age</label>
<input
    name="age"
    type="number"
>

<label>Weight (kg)</label>
<input
    name="weight"
    type="number"
    step="0.1"
>

<label>Program</label>

<select name="program">
{program_options}
</select>

<button>Save Client</button>

</form>

</div>


<div class="card">

<h2>Save Progress</h2>

<form method="post">

<input
    type="hidden"
    name="action"
    value="progress"
>

<label>Client Name</label>
<input name="name">

<label>Weekly Adherence (%)</label>

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
<th>Program</th>
<th>Calories</th>
</tr>

{client_table}

</table>

</div>


<div class="card">

<h2>Weekly Adherence Progress</h2>

{progress_chart}

</div>


<div class="card">

<h2>Progress Data</h2>

<table>

<tr>
<th>Client</th>
<th>Week</th>
<th>Adherence</th>
</tr>

{progress_table}

</table>

</div>

</div>
"""

    return html('ACEest v2.2.1', body)


def process_post():
    """Process the requested dashboard action."""
    action = request.form.get('action', '')

    if action == 'save':
        return save_client()

    if action == 'progress':
        return save_progress()

    return ''


@app.route('/', methods=['GET', 'POST'])
def home():
    """Display the dashboard and process form submissions."""
    message = ''

    if request.method == 'POST':
        message = process_post()

    return render_dashboard(message)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
