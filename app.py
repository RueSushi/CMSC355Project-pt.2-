from flask import Flask, render_template, request, redirect, session
from models_file import db, Medication

print("📦 models_file successfully imported!")

# Use the renamed folder path (NO spaces!)
app = Flask(__name__, template_folder='Sprint 1_LoginPage/templates')
app.secret_key = 'medsecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

# ✅ Create tables immediately using app context (Flask 3+)
with app.app_context():
    db.create_all()

@app.route('/add', methods=['GET', 'POST'])
def add_medication():
    session['patient_id'] = 'demo_patient'
    if request.method == 'POST':
        med = Medication(
            name=request.form['name'],
            dosage=request.form['dosage'],
            frequency=request.form['frequency'],
            time_of_day=request.form['time_of_day'],
            patient_id=session['patient_id']
        )
        db.session.add(med)
        db.session.commit()
        return redirect('/add')
    return render_template('add_medication.html')

if __name__ == '__main__':
    print("✅ Flask app is starting...")
    app.run(debug=True, port=5000)  # 👈 Run on port 5001 to avoid conflict


