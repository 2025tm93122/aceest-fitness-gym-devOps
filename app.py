from flask import Flask, render_template_string, request, send_file
from io import StringIO, BytesIO
import csv

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
clients = []
PROGRAMS = {
    "Fat Loss (FL)": {"workout":"Back Squat, Cardio, Bench, Deadlift, Recovery", "diet":"Egg Whites, Chicken, Fish Curry", "color":"#e74c3c", "calorie_factor":22},
    "Muscle Gain (MG)": {"workout":"Squat, Bench, Deadlift, Press, Rows", "diet":"Eggs, Biryani, Mutton Curry", "color":"#2ecc71", "calorie_factor":35},
    "Beginner (BG)": {"workout":"Air Squats, Ring Rows, Push-ups", "diet":"Balanced Tamil Meals", "color":"#3498db", "calorie_factor":26},
}

@app.get('/health')
def health(): return {"status":"healthy"}

def page(message=''):
    selected = request.form.get('program','')
    workout = PROGRAMS.get(selected,{}).get('workout','Select a profile')
    diet = PROGRAMS.get(selected,{}).get('diet','Select a profile')
    rows=''.join(f'<tr><td>{c[0]}</td><td>{c[1]}</td><td>{c[2]}</td><td>{c[3]}</td><td>{c[4]}</td><td>{c[5]}</td></tr>' for c in clients)
    chart = ''.join(f'<div><strong>{c[0]}</strong> - {c[4]}%</div>' for c in clients) or '<span class="muted">No clients yet.</span>'
    body=f'''<div class="header">ACEest FUNCTIONAL FITNESS SYSTEM v2</div><div class="container">{'<div class="alert">'+message+'</div>' if message else ''}<form method="post">
    <div class="grid"><div class="card"><h2>Client Profile</h2><label>Name</label><input name="name"><label>Age</label><input name="age" type="number"><label>Weight (kg)</label><input name="weight" type="number" step="0.1"><label>Program</label><select name="program">{''.join(f'<option value="{k}">{k}</option>' for k in PROGRAMS)}</select><label>Weekly Adherence (%)</label><input name="adherence" type="number" min="0" max="100"><label>Coach Notes</label><input name="notes"><button>Save Client</button><a class="btn secondary" href="/export.csv">Export CSV</a><a class="btn secondary" href="/reset">Reset</a></div>
    <div class="card"><h2>Weekly Training Plan</h2><pre>{workout}</pre></div><div class="card"><h2>Nutrition Plan</h2><pre>{diet}</pre></div></div></form>
    <div class="card"><h2>Client List</h2><table><tr><th>Name</th><th>Age</th><th>Weight</th><th>Program</th><th>Adherence</th><th>Notes</th></tr>{rows}</table></div>
    <div class="card"><h2>Progress Chart</h2>{chart}</div></div>'''
    return render_template_string(html('ACEest v1.1.2',body))

@app.route('/', methods=['GET','POST'])
def home():
    if request.method=='POST':
        try: client=(request.form.get('name',''), int(request.form.get('age') or 0), float(request.form.get('weight') or 0), request.form.get('program',''), int(float(request.form.get('adherence') or 0)), request.form.get('notes',''))
        except ValueError: return page('Age, weight and adherence must be numeric.')
        if not client[0] or not client[3]: return page('Please fill client name and program.')
        clients.append(client)
        return page(f'Client {client[0]} saved successfully.')
    return page()

@app.get('/export.csv')
def export_csv():
    s=StringIO(); w=csv.writer(s); w.writerow(['Name','Age','Weight','Program','Adherence','Notes']); w.writerows(clients)
    return send_file(BytesIO(s.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='aceest_clients.csv')

@app.get('/reset')
def reset():
    clients.clear(); return page('Client list reset.')

if __name__=='__main__': app.run(host='0.0.0.0',port=5000)
