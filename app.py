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
import os
import secrets
import sqlite3
from io import BytesIO

# FPDF is used by the original Tkinter v3.1.2 application.  The Flask
# conversion can use it when installed, but also has a built-in fallback so
# the application still starts even when the package is not present.
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None


app = Flask(__name__)
app.secret_key = "aceest-dev-key"
DB_NAME = os.environ.get("DATABASE_PATH", "aceest_fitness.db")
SECURE_RANDOM = secrets.SystemRandom()


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

EXERCISES = {
    "Strength": [
        "Squat",
        "Deadlift",
        "Bench Press",
        "Overhead Press",
        "Pull-Up",
        "Barbell Row",
    ],
    "Hypertrophy": [
        "Leg Press",
        "Incline Dumbbell Press",
        "Lat Pulldown",
        "Lateral Raise",
        "Bicep Curl",
        "Tricep Extension",
    ],
    "Conditioning": [
        "Running",
        "Cycling",
        "Rowing",
        "Burpees",
        "Jump Rope",
        "Kettlebell Swings",
    ],
    "Full Body": [
        "Push-Up",
        "Pull-Up",
        "Lunge",
        "Plank",
        "Dumbbell Row",
        "Dumbbell Press",
    ],
}


def html_page(title, body):
    """Return a self-contained HTML page for the Flask UI."""
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
    """Add a column when upgrading from an earlier ACEest milestone database."""
    if column_name not in column_names(connection, table_name):
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


def init_db():
    """Create/migrate the v3.1.2 database without deleting earlier milestone data."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
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
            membership_expiry TEXT
        )
        """
    )

    # Earlier milestones may already have a smaller clients table.  Add the
    # v3.1.2 fields instead of forcing the student to delete the database.
    ensure_column(connection, "clients", "height", "REAL")
    ensure_column(connection, "clients", "target_weight", "REAL")
    ensure_column(connection, "clients", "target_adherence", "INTEGER")
    ensure_column(connection, "clients", "membership_expiry", "TEXT")

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


def login_required():
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


def dashboard_html(message=""):
    connection = get_connection()
    clients = connection.execute("SELECT * FROM clients ORDER BY name").fetchall()
    connection.close()

    client_options = "".join(
        f'<option value="{row["name"]}">{row["name"]}</option>'
        for row in clients
    )
    program_options = "".join(
        f'<option value="{program}">{program}</option>' for program in PROGRAMS
    )
    client_rows = "".join(
        "<tr>"
        f'<td>{row["name"]}</td>'
        f'<td>{row["age"]}</td>'
        f'<td>{row["height"]}</td>'
        f'<td>{row["weight"]}</td>'
        f'<td>{row["program"]}</td>'
        f'<td>{row["calories"]}</td>'
        f'<td>{row["membership_expiry"]}</td>'
        "</tr>"
        for row in clients
    )

    notice = f'<div class="success">{message}</div>' if message else ""

    body = f"""
    <div class="header">ACEest Fitness Dashboard ({session.get('role', '')})</div>
    <div class="container">
      {notice}
      <p><a class="btn secondary" href="/logout">Logout</a></p>

      <div class="grid">
        <div class="card">
          <h2>Add / Save Client</h2>
          <form method="post" action="/client">
            <label>Name</label><input name="name" required>
            <label>Age</label><input name="age" type="number" min="0">
            <label>Height (cm)</label><input name="height" type="number" step="0.1" min="0">
            <label>Weight (kg)</label><input name="weight" type="number" step="0.1" min="0">
            <label>Program</label><select name="program">{program_options}</select>
            <label>Membership Expiry (YYYY-MM-DD)</label><input name="membership_expiry">
            <button type="submit">Save Client</button>
          </form>
        </div>

        <div class="card">
          <h2>Generate AI Program</h2>
          <form method="post" action="/generate">
            <label>Client</label><select name="client_name">{client_options}</select>
            <label>Experience</label>
            <select name="experience">
              <option value="beginner">beginner</option>
              <option value="intermediate">intermediate</option>
              <option value="advanced">advanced</option>
            </select>
            <button type="submit">Generate AI Program</button>
          </form>
        </div>

        <div class="card">
          <h2>Export PDF Report</h2>
          <form method="get" action="/report">
            <label>Client</label><select name="client_name">{client_options}</select>
            <button type="submit">Export PDF Report</button>
          </form>
        </div>

        <div class="card">
          <h2>Check Membership</h2>
          <form method="get" action="/membership">
            <label>Client</label><select name="client_name">{client_options}</select>
            <button type="submit">Check Membership</button>
          </form>
        </div>
      </div>

      <div class="card">
        <h2>Clients</h2>
        <table>
          <tr>
            <th>Name</th><th>Age</th><th>Height</th><th>Weight</th>
            <th>Program</th><th>Calories</th><th>Membership Expiry</th>
          </tr>
          {client_rows}
        </table>
      </div>
    </div>
    """
    return html_page("ACEest Fitness Dashboard", body)


@app.get("/")
def root():
    if login_required():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.get("/dashboard")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))
    return render_template_string(dashboard_html())


@app.post("/client")
def save_client():
    if not login_required():
        return redirect(url_for("login"))

    form = request.form
    name = form.get("name", "").strip()
    program = form.get("program", "")

    if not name:
        return render_template_string(dashboard_html("Name is required")), 400

    try:
        age = int(form.get("age") or 0)
        height = float(form.get("height") or 0)
        weight = float(form.get("weight") or 0)
    except ValueError:
        return render_template_string(
            dashboard_html("Age, height and weight must be valid numbers")
        ), 400

    factor = PROGRAMS.get(program, {}).get("factor", 25)
    calories = int(weight * factor) if weight > 0 else None

    connection = get_connection()
    connection.execute(
        """
        INSERT INTO clients
            (name, age, height, weight, program, calories, membership_expiry)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            age=excluded.age,
            height=excluded.height,
            weight=excluded.weight,
            program=excluded.program,
            calories=excluded.calories,
            membership_expiry=excluded.membership_expiry
        """,
        (
            name,
            age,
            height,
            weight,
            program,
            calories,
            form.get("membership_expiry", "").strip(),
        ),
    )
    connection.commit()
    connection.close()

    return redirect(url_for("dashboard", saved=1))


@app.post("/generate")
def generate():
    if not login_required():
        return redirect(url_for("login"))

    client_name = request.form.get("client_name", "").strip()
    experience = request.form.get("experience", "beginner").lower()

    if experience not in {"beginner", "intermediate", "advanced"}:
        experience = "beginner"

    connection = get_connection()
    row = connection.execute(
        "SELECT program FROM clients WHERE name=?", (client_name,)
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

    program_name = row["program"] or ""
    if "Fat Loss" in program_name:
        focus = "Conditioning"
    elif "Muscle Gain" in program_name:
        focus = "Hypertrophy"
    else:
        focus = "Full Body"

    settings = {
        "beginner": {"days": 3, "sets": (2, 3), "reps": (8, 12)},
        "intermediate": {"days": 4, "sets": (3, 4), "reps": (8, 15)},
        "advanced": {"days": 5, "sets": (4, 5), "reps": (6, 15)},
    }[experience]

    days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][
        : settings["days"]
    ]
    selected = []
    exercises_per_day = 3 if settings["days"] < 4 else 4

    for day in days_list:
        exercises = SECURE_RANDOM.sample(EXERCISES[focus], k=exercises_per_day)
        for exercise in exercises:
            selected.append(
                f"{day}: {exercise} - "
                f"{SECURE_RANDOM.randint(*settings['sets'])} sets x "
                f"{SECURE_RANDOM.randint(*settings['reps'])} reps"
            )

    program_text = "\n".join(selected)
    body = f"""
    <div class="header">Generated AI Program</div>
    <div class="container">
      <div class="card">
        <h2>{client_name}</h2>
        <p>Focus: {focus} | Experience: {experience}</p>
        <pre>{program_text}</pre>
        <a class="btn" href="/dashboard">Back</a>
      </div>
    </div>
    """
    return render_template_string(html_page("Generated Program", body))


@app.get("/membership")
def membership():
    if not login_required():
        return redirect(url_for("login"))

    client_name = request.args.get("client_name", "").strip()
    connection = get_connection()
    row = connection.execute(
        "SELECT name, membership_expiry FROM clients WHERE name=?", (client_name,)
    ).fetchone()
    connection.close()

    if row:
        message = f"Membership Expiry: {row['membership_expiry'] or 'N/A'}"
    else:
        message = "Client not found."

    body = f"""
    <div class="header">Membership</div>
    <div class="container">
      <div class="card">
        <h2>{client_name or 'Client'}</h2>
        <div class="alert">{message}</div>
        <a class="btn" href="/dashboard">Back</a>
      </div>
    </div>
    """
    return render_template_string(html_page("Membership", body))


def pdf_escape(value):
    """Return PDF-safe text compatible with built-in PDF fonts."""
    text = str(value)

    # Normalize common Unicode punctuation unsupported by
    # built-in Helvetica.
    text = (
        text.replace("–", "-")
        .replace("—", "-")
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )

    # Keep the fallback PDF content Latin-1 compatible.
    text = text.encode("latin-1", "replace").decode("latin-1")

    # Escape PDF control characters used by the fallback writer.
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def build_basic_pdf(title, lines):
    """Create a small valid one-page PDF using only Python's standard library."""
    content_lines = ["BT", "/F1 16 Tf", "72 760 Td", f"({pdf_escape(title)}) Tj"]
    for line in lines:
        content_lines.extend(["0 -24 Td", "/F1 12 Tf", f"({pdf_escape(line)}) Tj"])
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
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
    report_lines = [
        f"Name: {client['name']}",
        f"Age: {client['age']}",
        f"Height: {client['height']} cm",
        f"Weight: {client['weight']} kg",
        f"Program: {client['program']}",
        f"Calories: {client['calories']}",
        f"Membership Expiry: {client['membership_expiry']}",
    ]

    if FPDF is None:
        return build_basic_pdf(f"Client Report - {client['name']}", report_lines)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)

    safe_title = pdf_escape(
        f"Client Report - {client['name']}"
    )

    pdf.cell(
        0,
        10,
        safe_title,
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )

    pdf.set_font("Helvetica", "", 12)

    for line in report_lines:
        safe_line = pdf_escape(line)

        pdf.cell(
            0,
            10,
            safe_line,
            new_x="LMARGIN",
            new_y="NEXT",
        )

    result = pdf.output(dest="S")
    if isinstance(result, bytes):
        return result
    if isinstance(result, bytearray):
        return bytes(result)
    return result.encode("latin-1")


@app.get("/report")
def report():
    if not login_required():
        return redirect(url_for("login"))

    client_name = request.args.get("client_name", "").strip()
    connection = get_connection()
    client = connection.execute(
        "SELECT * FROM clients WHERE name=?", (client_name,)
    ).fetchone()
    connection.close()

    if not client:
        body = """
        <div class="header">PDF Report</div>
        <div class="container">
          <div class="alert">Client not found.</div>
          <a class="btn" href="/dashboard">Back</a>
        </div>
        """
        return render_template_string(html_page("PDF Report", body)), 404

    pdf_bytes = create_report_pdf(client)
    output = BytesIO(pdf_bytes)
    output.seek(0)

    safe_name = "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in client_name
    )
    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{safe_name}_report.pdf",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
