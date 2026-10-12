from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_file,
    session,
    url_for,
)
from datetime import date
from io import BytesIO
import os
import secrets
import sqlite3

# The original Tkinter v3.2.4 uses FPDF. Make it optional so this milestone
# can run even when fpdf2 has not yet been installed in the virtual env.
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None


app = Flask(__name__)
app.secret_key = "aceest-dev-key"
DB_NAME = os.environ.get("DATABASE_PATH", "aceest_fitness.db")
SECURE_RANDOM = secrets.SystemRandom()

PROGRAM_TEMPLATES = {
    "Fat Loss": ["Full Body HIIT", "Circuit Training", "Cardio + Weights"],
    "Muscle Gain": ["Push/Pull/Legs", "Upper/Lower Split", "Full Body Strength"],
    "Beginner": ["Full Body 3x/week", "Light Strength + Mobility"],
}


def html_page(title, body):
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
.success {{ background:#153d22; border:1px solid #3c8c55; padding:12px; border-radius:6px; margin-bottom:16px; }}
pre {{ white-space:pre-wrap; line-height:1.5; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ border:1px solid #555; padding:8px; text-align:left; }}
th {{ background:#333; }}
</style>
</head>
<body>{body}</body>
</html>"""


def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def column_names(connection, table_name):
    return {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def ensure_column(connection, table_name, column_name, definition):
    """Add fields required by v3.2.4 when an older milestone DB already exists."""
    if column_name not in column_names(connection, table_name):
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


def init_db():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
        """
    )
    cursor.execute(
        "INSERT OR IGNORE INTO users(username, password, role) VALUES (?, ?, ?)",
        ("admin", "admin", "Admin"),
    )

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
            target_adherence INTEGER,
            membership_status TEXT,
            membership_end TEXT
        )
        """
    )

    # Preserve data from v2.x/v3.1.2 instead of forcing the DB to be deleted.
    ensure_column(connection, "clients", "height", "REAL")
    ensure_column(connection, "clients", "target_weight", "REAL")
    ensure_column(connection, "clients", "target_adherence", "INTEGER")
    ensure_column(connection, "clients", "membership_status", "TEXT")
    ensure_column(connection, "clients", "membership_end", "TEXT")

    # If v3.1.2 created membership_expiry, copy it into membership_end where possible.
    columns = column_names(connection, "clients")
    if "membership_expiry" in columns:
        connection.execute(
            """
            UPDATE clients
            SET membership_end = COALESCE(NULLIF(membership_end, ''), membership_expiry)
            WHERE membership_expiry IS NOT NULL
            """
        )

    connection.execute(
        "UPDATE clients SET membership_status='Active' "
        "WHERE membership_status IS NULL OR membership_status=''"
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


init_db()


def logged_in():
    return "user" in session


@app.get("/health")
def health():
    return jsonify(status="healthy")


@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        connection = get_connection()
        row = connection.execute(
            "SELECT role FROM users WHERE username=? AND password=?",
            (username, password),
        ).fetchone()
        connection.close()

        if row:
            session["user"] = username
            session["role"] = row["role"]
            return redirect(url_for("dashboard"))

        message = "Invalid credentials. Try admin / admin."

    alert = f'<div class="alert">{message}</div>' if message else ""
    body = f"""
    <div class="header">ACEest Login</div>
    <div class="container">
      <div class="card">
        <h2>Login</h2>
        {alert}
        <form method="post">
          <label>Username</label>
          <input name="username" required>
          <label>Password</label>
          <input name="password" type="password" required>
          <button type="submit">Login</button>
        </form>
      </div>
    </div>
    """
    return render_template_string(html_page("ACEest Login", body))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
def root():
    return redirect(url_for("dashboard")) if logged_in() else redirect(url_for("login"))


def dashboard_html(message=""):
    connection = get_connection()
    clients = connection.execute("SELECT * FROM clients ORDER BY name").fetchall()
    workouts = connection.execute(
        "SELECT * FROM workouts ORDER BY date DESC, id DESC"
    ).fetchall()
    progress = connection.execute("SELECT * FROM progress ORDER BY id").fetchall()
    connection.close()

    options = "".join(
        f'<option value="{row["name"]}">{row["name"]}</option>' for row in clients
    )
    client_rows = "".join(
        "<tr>"
        f'<td>{row["name"]}</td>'
        f'<td>{row["program"] or ""}</td>'
        f'<td>{row["calories"] if row["calories"] is not None else ""}</td>'
        f'<td>{row["membership_status"] or ""}</td>'
        f'<td>{row["membership_end"] or ""}</td>'
        "</tr>"
        for row in clients
    )
    workout_rows = "".join(
        "<tr>"
        f'<td>{row["client_name"]}</td>'
        f'<td>{row["date"]}</td>'
        f'<td>{row["workout_type"]}</td>'
        f'<td>{row["duration_min"]}</td>'
        f'<td>{row["notes"] or ""}</td>'
        "</tr>"
        for row in workouts
    )
    progress_rows = "".join(
        "<tr>"
        f'<td>{row["client_name"]}</td>'
        f'<td>{row["week"]}</td>'
        f'<td>{row["adherence"]}%</td>'
        "</tr>"
        for row in progress
    )

    notice = f'<div class="success">{message}</div>' if message else ""
    body = f"""
    <div class="header">ACEest Dashboard ({session.get('role', 'Admin')})</div>
    <div class="container">
      {notice}
      <p><a class="btn secondary" href="/logout">Logout</a></p>

      <div class="grid">
        <div class="card">
          <h2>Add / Save Client</h2>
          <form method="post" action="/client">
            <label>Name</label><input name="name" required>
            <label>Age</label><input name="age" type="number">
            <label>Height</label><input name="height" type="number" step="0.1">
            <label>Weight</label><input name="weight" type="number" step="0.1">
            <label>Program</label><input name="program">
            <label>Target Weight</label><input name="target_weight" type="number" step="0.1">
            <label>Target Adherence</label><input name="target_adherence" type="number">
            <label>Membership Status</label><input name="membership_status" value="Active">
            <label>Membership End</label><input name="membership_end" placeholder="YYYY-MM-DD">
            <button type="submit">Save Client</button>
          </form>
        </div>

        <div class="card">
          <h2>Generate AI Program</h2>
          <form method="get" action="/generate">
            <label>Client</label><select name="client_name">{options}</select>
            <button type="submit">Generate AI Program</button>
          </form>

          <h2>Generate PDF Report</h2>
          <form method="get" action="/report">
            <label>Client</label><select name="client_name">{options}</select>
            <button type="submit">Generate PDF Report</button>
          </form>

          <h2>Check Membership</h2>
          <form method="get" action="/membership">
            <label>Client</label><select name="client_name">{options}</select>
            <button type="submit">Check Membership</button>
          </form>
        </div>
      </div>

      <div class="card">
        <h2>Client Summary</h2>
        <table>
          <tr><th>Name</th><th>Program</th><th>Calories</th><th>Membership</th><th>End</th></tr>
          {client_rows}
        </table>
      </div>

      <div class="card">
        <h2>Progress</h2>
        <table>
          <tr><th>Client</th><th>Week</th><th>Adherence</th></tr>
          {progress_rows}
        </table>
      </div>

      <div class="card">
        <h2>Workouts & Exercises</h2>
        <form method="post" action="/workout">
          <label>Client</label><select name="client_name">{options}</select>
          <label>Date</label><input name="date" value="{date.today().isoformat()}">
          <label>Type</label>
          <select name="workout_type">
            <option>Strength</option>
            <option>Hypertrophy</option>
            <option>Cardio</option>
            <option>Mobility</option>
          </select>
          <label>Duration (min)</label><input name="duration_min" value="60" type="number">
          <label>Notes</label><input name="notes">
          <button type="submit">Add Workout</button>
        </form>
        <table>
          <tr><th>Client</th><th>Date</th><th>Type</th><th>Duration</th><th>Notes</th></tr>
          {workout_rows}
        </table>
      </div>
    </div>
    """
    return html_page("ACEest Dashboard", body)


@app.get("/dashboard")
def dashboard():
    if not logged_in():
        return redirect(url_for("login"))
    return render_template_string(dashboard_html())


@app.post("/client")
def save_client():
    if not logged_in():
        return redirect(url_for("login"))

    form = request.form
    name = form.get("name", "").strip()
    if not name:
        return render_template_string(dashboard_html("Name is required")), 400

    try:
        age = int(form.get("age") or 0)
        height = float(form.get("height") or 0)
        weight = float(form.get("weight") or 0)
        target_weight = float(form.get("target_weight") or 0) or None
        target_adherence = int(float(form.get("target_adherence") or 0)) or None
    except ValueError:
        return render_template_string(
            dashboard_html("Age, height, weight and targets must be valid numbers")
        ), 400

    program = form.get("program", "").strip()
    # v3.2.4 no longer has the earlier program-factor dictionary. Keep the
    # conversion's simple default factor for the optional calorie summary.
    calories = int(weight * 25) if weight > 0 else None

    connection = get_connection()
    connection.execute(
        """
        INSERT INTO clients
            (name, age, height, weight, program, calories,
             target_weight, target_adherence, membership_status, membership_end)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            age=excluded.age,
            height=excluded.height,
            weight=excluded.weight,
            program=excluded.program,
            calories=excluded.calories,
            target_weight=excluded.target_weight,
            target_adherence=excluded.target_adherence,
            membership_status=excluded.membership_status,
            membership_end=excluded.membership_end
        """,
        (
            name,
            age,
            height,
            weight,
            program,
            calories,
            target_weight,
            target_adherence,
            form.get("membership_status", "Active").strip() or "Active",
            form.get("membership_end", "").strip(),
        ),
    )
    connection.commit()
    connection.close()
    return redirect(url_for("dashboard", saved=1))


@app.post("/workout")
def add_workout():
    if not logged_in():
        return redirect(url_for("login"))

    form = request.form
    try:
        duration = int(float(form.get("duration_min") or 0))
    except ValueError:
        return render_template_string(dashboard_html("Duration must be a number")), 400

    connection = get_connection()
    connection.execute(
        """
        INSERT INTO workouts(client_name, date, workout_type, duration_min, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            form.get("client_name", ""),
            form.get("date", ""),
            form.get("workout_type", ""),
            duration,
            form.get("notes", ""),
        ),
    )
    connection.commit()
    connection.close()
    return redirect(url_for("dashboard"))


@app.get("/generate")
def generate_program():
    if not logged_in():
        return redirect(url_for("login"))

    name = request.args.get("client_name", "").strip()
    connection = get_connection()
    row = connection.execute(
        "SELECT program FROM clients WHERE name=?", (name,)
    ).fetchone()
    connection.close()

    if not row:
        return render_template_string(
            html_page(
                "Generated Program",
                '<div class="header">Generated AI Program</div>'
                '<div class="container"><div class="alert">Client not found.</div>'
                '<a class="btn" href="/dashboard">Back</a></div>',
            )
        ), 404

    current_program = row["program"] or ""
    if "Fat Loss" in current_program:
        program_type = "Fat Loss"
    elif "Muscle" in current_program:
        program_type = "Muscle Gain"
    elif "Beginner" in current_program:
        program_type = "Beginner"
    else:
        # The original v3.2.4 chooses randomly from the program templates.
        program_type = SECURE_RANDOM.choice(list(PROGRAM_TEMPLATES.keys()))

    program_detail = SECURE_RANDOM.choice(PROGRAM_TEMPLATES[program_type])

    connection = get_connection()
    connection.execute(
        "UPDATE clients SET program=? WHERE name=?", (program_detail, name)
    )
    connection.commit()
    connection.close()

    body = f"""
    <div class="header">Program Generated</div>
    <div class="container">
      <div class="card">
        <h2>{name}</h2>
        <p>Program: {program_detail}</p>
        <a class="btn" href="/dashboard">Back</a>
      </div>
    </div>
    """
    return render_template_string(html_page("Program Generated", body))


@app.get("/membership")
def membership():
    if not logged_in():
        return redirect(url_for("login"))

    name = request.args.get("client_name", "").strip()
    connection = get_connection()
    row = connection.execute(
        "SELECT membership_status, membership_end FROM clients WHERE name=?", (name,)
    ).fetchone()
    connection.close()

    if row:
        message = (
            f"Membership: {row['membership_status'] or 'N/A'}\n"
            f"Renewal Date: {row['membership_end'] or 'N/A'}"
        )
    else:
        message = "Client not found."

    body = f"""
    <div class="header">Membership</div>
    <div class="container">
      <div class="card">
        <h2>{name or 'Client'}</h2>
        <pre>{message}</pre>
        <a class="btn" href="/dashboard">Back</a>
      </div>
    </div>
    """
    return render_template_string(html_page("Membership", body))


def pdf_escape(value):
    """Return text safe for the built-in PDF fonts."""
    text = str(value)

    text = (
        text.replace("–", "-")
        .replace("—", "-")
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )

    text = text.encode("latin-1", "replace").decode("latin-1")

    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )

def build_basic_pdf(title, lines):
    """Build a valid one-page PDF without third-party packages."""
    content_lines = ["BT", "/F1 16 Tf", "72 760 Td", f"({pdf_escape(title)}) Tj"]
    for line in lines:
        content_lines.extend(
            ["0 -24 Td", "/F1 12 Tf", f"({pdf_escape(line)}) Tj"]
        )
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def create_report_pdf(client):
    labels = [
        ("ID", "id"),
        ("Name", "name"),
        ("Age", "age"),
        ("Height", "height"),
        ("Weight", "weight"),
        ("Program", "program"),
        ("Calories", "calories"),
        ("Target Weight", "target_weight"),
        ("Target Adherence", "target_adherence"),
        ("Membership", "membership_status"),
        ("End", "membership_end"),
    ]
    lines = [f"{label}: {client[key]}" for label, key in labels]

    if FPDF is None:
        return build_basic_pdf(f"ACEest Client Report - {client['name']}", lines)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)

    pdf.cell(
        0,
        10,
        pdf_escape(f"ACEest Client Report - {client['name']}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font("Helvetica", "", 12)

    for line in lines:
        pdf.cell(
            0,
            10,
            pdf_escape(line),
            new_x="LMARGIN",
            new_y="NEXT",
        )

    result = pdf.output(dest="S")
    if isinstance(result, bytes):
        return result
    if isinstance(result, bytearray):
        return bytes(result)
    return str(result).encode("latin-1", "replace")


@app.get("/report")
def report():
    if not logged_in():
        return redirect(url_for("login"))

    name = request.args.get("client_name", "").strip()
    connection = get_connection()
    client = connection.execute(
        "SELECT * FROM clients WHERE name=?", (name,)
    ).fetchone()
    connection.close()

    if not client:
        return render_template_string(
            html_page(
                "PDF Report",
                '<div class="header">PDF Report</div>'
                '<div class="container"><div class="alert">Client not found.</div>'
                '<a class="btn" href="/dashboard">Back</a></div>',
            )
        ), 404

    pdf_bytes = create_report_pdf(client)
    output = BytesIO(pdf_bytes)
    output.seek(0)
    safe_name = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_")) or "client"

    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{safe_name}_report.pdf",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
