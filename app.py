from flask import Flask, jsonify, render_template_string, request

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

PROGRAMS = {
    "Fat Loss (FL)": {
        "workout": "Mon: 5x5 Back Squat + AMRAP\nTue: EMOM 20min Assault Bike\nWed: Bench Press + 21-15-9\nThu: 10RFT Deadlifts/Box Jumps\nFri: 30min Active Recovery",
        "diet": "B: 3 Egg Whites + Oats Idli\nL: Grilled Chicken + Brown Rice\nD: Fish Curry + Millet Roti\nTarget: 2,000 kcal",
        "color": "#e74c3c",
    },
    "Muscle Gain (MG)": {
        "workout": "Mon: Squat 5x5\nTue: Bench 5x5\nWed: Deadlift 4x6\nThu: Front Squat 4x8\nFri: Incline Press 4x10\nSat: Barbell Rows 4x10",
        "diet": "B: 4 Eggs + PB Oats\nL: Chicken Biryani (250g Chicken)\nD: Mutton Curry + Jeera Rice\nTarget: 3,200 kcal",
        "color": "#2ecc71",
    },
    "Beginner (BG)": {
        "workout": "Circuit Training: Air Squats, Ring Rows, Push-ups.\nFocus: Technique Mastery & Form (90% Threshold)",
        "diet": "Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati.\nProtein: 120g/day",
        "color": "#3498db",
    },
}

SITE_METRICS = "CAPACITY: 150 Users\\nAREA: 10,000 sq ft\\nBREAK-EVEN: 250 Members"

@app.get('/health')
def health():
    return jsonify(status='healthy')

@app.route('/', methods=['GET', 'POST'])
def home():
    selected = request.form.get('program') if request.method == 'POST' else request.args.get('program')
    data = PROGRAMS.get(selected)
    body = f'''<div class="header">ACEest FUNCTIONAL FITNESS</div><div class="container">
    <div class="grid"><div class="card"><h2>Client Profile</h2><form method="post">
    <label>Select Program</label><select name="program" onchange="this.form.submit()"><option value="">Select a profile</option>{''.join(f'<option {'selected' if k==selected else ''} value="{k}">{k}</option>' for k in PROGRAMS)}</select></form>
    <pre>{SITE_METRICS}</pre></div>
    <div class="card"><h2>Weekly Workout Chart</h2><pre>{data['workout'] if data else 'Select a profile to view workout'}</pre></div>
    <div class="card"><h2>Daily Nutrition Plan (Tamil Nadu Context)</h2><pre>{data['diet'] if data else 'Select a profile to view diet'}</pre></div></div></div>'''
    return render_template_string(html('ACEest Fitness and Gym', body))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
