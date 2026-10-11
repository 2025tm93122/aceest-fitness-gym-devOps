from flask import Flask, render_template_string, request

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
    "Fat Loss (FL)": {"workout":"Mon: Back Squat 5x5 + Core\nTue: EMOM 20min Assault Bike\nWed: Bench Press + 21-15-9\nThu: Deadlift + Box Jumps\nFri: Zone 2 Cardio 30min", "diet":"Breakfast: Egg Whites + Oats\nLunch: Grilled Chicken + Brown Rice\nDinner: Fish Curry + Millet Roti\nTarget: ~2000 kcal", "color":"#e74c3c", "calorie_factor":22},
    "Muscle Gain (MG)": {"workout":"Mon: Squat 5x5\nTue: Bench 5x5\nWed: Deadlift 4x6\nThu: Front Squat 4x8\nFri: Incline Press 4x10\nSat: Barbell Rows 4x10", "diet":"Breakfast: Eggs + Peanut Butter Oats\nLunch: Chicken Biryani\nDinner: Mutton Curry + Rice\nTarget: ~3200 kcal", "color":"#2ecc71", "calorie_factor":35},
    "Beginner (BG)": {"workout":"Full Body Circuit:\n- Air Squats\n- Ring Rows\n- Push-ups\nFocus: Technique & Consistency", "diet":"Balanced Tamil Meals\nIdli / Dosa / Rice + Dal\nProtein Target: 120g/day", "color":"#3498db", "calorie_factor":26},
}

@app.get('/health')
def health(): return {"status":"healthy"}

def build_home_body(name, age, weight, selected, adherence, data, calories, message):
    body = f'''<div class="header">ACEest FUNCTIONAL FITNESS SYSTEM</div><div class="container">{'<div class="alert">'+message+'</div>' if message else ''}
    <form method="post"><div class="grid"><div class="card"><h2>Client Profile</h2>
    <label>Name</label><input name="name" value="{name}"><label>Age</label><input name="age" type="number" value="{age}"><label>Weight (kg)</label><input name="weight" type="number" step="0.1" value="{weight}">
    <label>Program</label><select name="program"><option value="">Select</option>{''.join(f'<option {'selected' if k==selected else ''} value="{k}">{k}</option>' for k in PROGRAMS)}</select>
    <label>Weekly Adherence (%)</label><input name="adherence" type="number" min="0" max="100" value="{adherence}">
    <button name="action" value="save">Save Client</button><button class="secondary" name="action" value="reset">Reset</button></div>
    <div class="card"><h2>Weekly Training Plan</h2><pre>{data['workout'] if data else 'Select a profile'}</pre></div>
    <div class="card"><h2>Nutrition Plan (TN Context)</h2><pre>{data['diet'] if data else 'Select a profile'}</pre><div class="metric">Estimated Calories: {str(calories)+' kcal' if calories is not None else '--'}</div></div></div></form></div>'''
    return body

@app.route('/', methods=['GET','POST'])
def home():
    message = None
    form = request.form if request.method == 'POST' else request.args
    selected = form.get('program','')
    name = form.get('name','')
    age = form.get('age','')
    weight = form.get('weight','')
    adherence = form.get('adherence','0')
    if request.method == 'POST' and request.form.get('action') == 'save':
        if not name or not selected:
            message = 'Please fill client name and program.'
        else:
            message = f'Client {name} saved successfully. Adherence: {adherence}%'
    data = PROGRAMS.get(selected)
    calories = None
    try:
        if data and float(weight) > 0: calories = int(float(weight) * data['calorie_factor'])
    except (ValueError, TypeError): pass
    body = build_home_body(name, age, weight, selected, adherence, data, calories, message)
    return render_template_string(html('ACEest Fitness & Performance', body))

if __name__ == '__main__': app.run(host='127.0.0.1', port=5000)
