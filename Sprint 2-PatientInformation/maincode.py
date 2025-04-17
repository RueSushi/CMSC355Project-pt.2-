from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from datetime import datetime, timedelta
import json
import os
import re
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "your_secret_key"
USER_DB_FILE = "users.json"

def load_users():
    """Load the user data from the JSON file."""
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r") as file:
            return json.load(file)
    return {}

def save_users(users):
    """Save the updated user data to the JSON file."""
    with open(USER_DB_FILE, "w") as file:
        json.dump(users, file, indent=4)

def is_valid_email(email):
    """Check if the email format is valid."""
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email)

def is_valid_password(password):
    """Check if the password meets the criteria (at least 7 characters and 1 special character)."""
    return len(password) >= 7 and re.search(r'[!@#$%&()?:;]', password)

@app.route('/')
def home():
    return render_template("login.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    """User registration route."""
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        users = load_users()

        if not all([first_name, last_name, email, password]):
            flash("All fields are required!", "danger")
        if not email or not password:
            flash("Email and password are required!", "danger")
        elif not is_valid_email(email):
            flash("Invalid email format!", "danger")
        elif email in users:
            flash("Email already registered!", "danger")
        elif not is_valid_password(password):
            flash("Password must be at least 7 characters and contain 1 special character (!@#$%&()?;).", "danger")
        else:
            users[email] = {"first_name": first_name, "last_name": last_name, "password": password, "medications": []}
            save_users(users)
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("home"))
    return render_template("register.html")

@app.route('/login', methods=["POST"])
def login():
    """User login route."""
    email = request.form["email"]
    password = request.form["password"]
    users = load_users()

    if email in users and users[email]["password"] == password:
        session["user"] = email
        return redirect(url_for("dashboard"))
    else:
        flash("Invalid email or password!", "danger")
        return redirect(url_for("home"))

@app.route('/dashboard')
def dashboard():
    """User dashboard route to show their information and medications."""
    if "user" not in session:
        return redirect(url_for("home"))
    users = load_users()
    user_data = users.get(session["user"])

    # Render dashboard with medications list
    return render_template("dashboard.html", user=user_data)

@app.route('/profile', methods=["GET", "POST"])
def profile():
    """User profile route for viewing and editing profile information."""
    if "user" not in session:
        return redirect(url_for("home"))
    
    users = load_users()
    current_email = session["user"]
    user_data = users.get(current_email)

    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        password = request.form["password"]
        pre_exist = request.form["pre_exist"]
        phone = request.form["phone"]
        address = request.form["address"]
        dob = request.form["dob"]
        zip_code = request.form["zip_code"]
        city = request.form["city"]
        email = request.form["email"]

        user_data["email"] = email
        user_data["first_name"] = first_name
        user_data["last_name"] = last_name
        user_data["password"] = password
        user_data["pre_exist"] = pre_exist
        user_data["phone"] = phone
        user_data["address"] = address
        user_data["dob"] = dob
        user_data["zip_code"] = zip_code
        user_data["city"] = city
        users[session["user"]] = user_data

        if email != current_email:
            if email in users:
                flash("That email is already in use!", "danger")
                return redirect(url_for("profile"))
            users[email] = user_data
            del users[current_email]
            session["user"] = email  
        else:
            users[current_email] = user_data

        save_users(users)
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user_data, email=session["user"])

@app.route('/logout')
def logout():
    """Log out the user by removing session data."""
    session.pop("user", None)
    return redirect(url_for("home"))


@app.route('/track')
def track_medications():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current_user = users.get(session["user"])

    now = datetime.now()
    for med in current_user["medications"]:
        nd = datetime.strptime(med["next_dose"], "%Y-%m-%d %H:%M")
        time_diff = (nd - now).total_seconds()
        if 0 <= time_diff <= 3600:
            flash(f" It's almost time to take '{med['medication']}' (Next dose at {med['next_dose']})", "danger")

    return render_template("track.html", user=current_user, medications=current_user["medications"])

@app.route('/add-medication', methods=["GET", "POST"])
def add_medication():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current_user = users.get(session["user"])

    if request.method == "POST":
        medication_name = request.form["medication"]
        frequency = request.form["frequency"]
        start_date = request.form["start_date"]
        now = datetime.now()

        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")

        frequency_map = {
            "once_a_day": timedelta(days=1),
            "twice_a_day": timedelta(hours=12),
            "three_times_a_day": timedelta(hours=8),
            "every_6_hours": timedelta(hours=6),
            "every_8_hours": timedelta(hours=8),
            "every_other_day": timedelta(days=2),
            "weekly": timedelta(weeks=1),
        }

        if frequency == "custom":
            custom_days = int(request.form.get("custom_interval_days", 1))
            interval = timedelta(days=custom_days)
        else:
            interval = frequency_map.get(frequency, timedelta(days=1))

        next_dose = start_datetime
        while next_dose <= now:
            next_dose += interval

        new_medication = {
            "medication": medication_name,
            "frequency": frequency,
            "start_date": start_date,
            "next_dose": next_dose.strftime("%Y-%m-%d %H:%M")
        }

        current_user["medications"].append(new_medication)
        save_users(users)

        flash(f"Medication '{medication_name}' added. Next dose: {new_medication['next_dose']}", "success")
        return redirect(url_for("track_medications"))

    return render_template("add_medication.html")

@app.route('/delete-medication', methods=["POST"])
def delete_medication():
    if "user" not in session:
        return redirect(url_for("home"))

    medication_name = request.form.get("medication_name")

    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    updated_meds = [m for m in medications if m["medication"] != medication_name]
    if len(updated_meds) < len(medications):
        user["medications"] = updated_meds
        save_users(users)
        flash(f"Deleted '{medication_name}' successfully.", "success")
    else:
        flash("Medication not found.", "danger")

    return redirect(url_for("track_medications"))

@app.route('/edit-medication/<int:index>', methods=["GET", "POST"])
def edit_medication(index):
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    if index < 0 or index >= len(medications):
        flash("Medication not found.", "danger")
        return redirect(url_for("track_medications"))

    medication = medications[index]

    if request.method == "POST":
        frequency = request.form["frequency"]
        start_date = request.form["start_date"]

        # Recalculate next dose
        frequency_map = {
            "once_a_day": timedelta(days=1),
            "twice_a_day": timedelta(hours=12),
            "three_times_a_day": timedelta(hours=8),
            "every_6_hours": timedelta(hours=6),
            "every_8_hours": timedelta(hours=8),
            "every_other_day": timedelta(days=2),
            "weekly": timedelta(weeks=1),
        }

        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        now = datetime.now()
        interval = frequency_map.get(frequency, timedelta(days=1))

        next_dose = start_datetime
        while next_dose <= now:
            next_dose += interval

        medication["frequency"] = frequency
        medication["start_date"] = start_date
        medication["next_dose"] = next_dose.strftime("%Y-%m-%d %H:%M")

        save_users(users)
        flash("Medication updated successfully!", "success")
        return redirect(url_for("track_medications"))

    return render_template("edit_medication.html", medication=medication)
    return render_template("edit_medication.html", medication=med_to_edit)

@app.route('/report')
def generate_report():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    return render_template("report.html", user=user, medications=medications)

@app.route('/download-report')
def download_report():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    response = make_response()
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=medication_report.pdf"

    buffer = response.stream
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    story = []
    styles = getSampleStyleSheet()

    # Title
    story.append(Paragraph("Daily/Regular Medication List", styles["Title"]))
    story.append(Paragraph(f"Patient name: {user['first_name']} {user['last_name']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Header row
    table_data = [["Date", "Medication Name", "Frequency", "Next Dose Time"]]

    # Add user's actual medications
    for med in medications:
        table_data.append([
            med["start_date"],
            med["medication"],
            med["frequency"],
            med["next_dose"]
        ])

    # Add blank rows to match the form style
    for _ in range(15 - len(medications)):
        table_data.append(["", "", "", ""])

    table = Table(table_data, colWidths=[90, 160, 120, 140])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
    ]))

    story.append(table)
    doc.build(story)
    return response

if __name__ == "__main__":
    app.run(debug=True, port=5006)