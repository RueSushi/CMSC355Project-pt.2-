from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from datetime import datetime, timedelta
import json
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
from datetime import date, datetime, timedelta
import calendar
from flask import request

# Initialize the Flask application
app = Flask(__name__)

# Route to view a specific day in the calendar and handle medication adherence
@app.route('/calendar/<date>', methods=["GET", "POST"])
def view_day(date):
    # Redirect to home if user is not logged in
    if "user" not in session:
        return redirect(url_for("home"))

    # Load user data
    users = load_users()
    user = users.get(session["user"])

    # Initialize adherence tracking if it doesn't exist
    if "adherence" not in user:
        user["adherence"] = {}

    # Handle POST request to update medication adherence for this day
    if request.method == "POST":
        taken = request.form.getlist("taken")  # Get list of medication indices that were taken
        meds_taken = [user["medications"][int(i)]["medication"] for i in taken]  # Get medication names
        user["adherence"][date] = meds_taken  # Store which medications were taken on this date
        save_users(users)  # Save the updated user data
        flash(f"Updated adherence for {date}.", "success")
        return redirect(url_for("view_day", date=date))

    # Get user's medications and which ones were taken today
    meds = user.get("medications", [])
    taken_today = user["adherence"].get(date, [])

    return render_template("day_view.html", date=date, medications=meds, taken_today=taken_today)

# Route to view the monthly calendar with adherence tracking
@app.route('/calendar')
def calendar_view():
    # Redirect to home if user is not logged in
    if "user" not in session:
        return redirect(url_for("home"))

    # Load user data
    users = load_users()
    current_user = users.get(session["user"])

    # Get current date information
    today = date.today()
    year = today.year
    month = today.month

    # Generate calendar data for current month
    cal = calendar.Calendar()
    month_days = cal.monthdatescalendar(year, month)

    # Get adherence data for the user
    adherence_map = current_user.get("adherence", {})  # Should be a dict like {"2025-04-22": True, ...}

    return render_template(
        "calendar.html",
        calendar_weeks=month_days,
        adherence_map=adherence_map,
        today_meds=current_user["medications"]
    )

# Set Flask application secret key
app.secret_key = "your_secret_key"
# Define the file path for storing user data
USER_DB_FILE = "users.json"

# Function to load user data from JSON file
def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r") as file:
            return json.load(file)
    return {}  # Return empty dict if file doesn't exist

# Function to save user data to JSON file
def save_users(users):
    with open(USER_DB_FILE, "w") as file:
        json.dump(users, file, indent=4)

# Function to send email reports to users or healthcare providers
def send_email_report(to_email, subject, body, attachment_bytes=None, attachment_filename="report.pdf"):
    sender_email = "medireminder.notifications@gmail.com"
    app_password = "dkrgfbnhiielfkkt"  # App-specific password for Gmail

    # Create email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Add PDF attachment if provided
    if attachment_bytes:
        part = MIMEApplication(attachment_bytes, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=attachment_filename)
        msg.attach(part)

    # Send the email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print("Error sending email:", str(e))

# Function to validate email format
def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email)

# Function to validate password strength
def is_valid_password(password):
    # Password must be at least 7 characters and contain at least one special character
    return len(password) >= 7 and re.search(r'[!@#$%&()?:;]', password)

# Landing page route
@app.route('/')
def landing_page():
    return render_template("index.html")

# Home/login page route
@app.route('/home')
def home():
    return render_template("login.html")

# About page route
@app.route('/about')
def about():
    return render_template("about.html")

# Contact page route
@app.route('/contact')
def contact():
    return render_template("contact.html")

# User registration route
@app.route('/register', methods=["GET", "POST"])
def register():
    """User registration route."""
    if request.method == "POST":
        # Get form data
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        users = load_users()

        # Validate form data
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
            # Create new user and save to database
            users[email] = {"first_name": first_name, "last_name": last_name, "password": password, "medications": []}
            save_users(users)
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("home"))
    return render_template("register.html")

# User login route
@app.route('/login', methods=["POST"])
def login():
    """User login route."""
    email = request.form["email"]
    password = request.form["password"]
    users = load_users()

    # Check if email exists and password matches
    if email in users and users[email]["password"] == password:
        session["user"] = email  # Store user email in session
        return redirect(url_for("dashboard"))
    else:
        flash("Invalid email or password!", "danger")
        return redirect(url_for("home"))

# User dashboard route
@app.route('/dashboard')
def dashboard():
    """User dashboard route to show their information and medications."""
    # Redirect if not logged in
    if "user" not in session:
        return redirect(url_for("home"))
    
    # Load user data
    users = load_users()
    user_data = users.get(session["user"])

    # Render dashboard with medications list
    return render_template("dashboard.html", user=user_data)

# User profile route for viewing and updating user information
@app.route('/profile', methods=["GET", "POST"])
def profile():
    """User profile route for viewing and editing profile information."""
    # Redirect if not logged in
    if "user" not in session:
        return redirect(url_for("home"))
    
    # Load user data
    users = load_users()
    current_email = session["user"]
    user_data = users.get(current_email)

    # Handle profile update form submission
    if request.method == "POST":
        # Get form data
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
        doctor_email = request.form["doctor_email"]

        # Update user data
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
        user_data["doctor_email"] = doctor_email

        # Handle email change (requires updating the user dictionary key)
        if email != current_email:
            if email in users:
                flash("That email is already in use!", "danger")
                return redirect(url_for("profile"))
            users[email] = user_data  # Add user data under new email
            del users[current_email]  # Remove old email entry
            session["user"] = email   # Update session
        else:
            users[current_email] = user_data  # Update existing user data

        # Save changes and show success message
        save_users(users)
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user_data, email=session["user"])

# Logout route
@app.route('/logout')
def logout():
    """Log out the user by removing session data."""
    session.pop("user", None)  # Remove user from session
    return redirect(url_for("home"))

# Route to track medications and show upcoming doses
@app.route('/track')
def track_medications():
    # Redirect if not logged in
    if "user" not in session:
        return redirect(url_for("home"))

    # Load user data
    users = load_users()
    current_user = users.get(session["user"])

    # Check for upcoming medication doses (within next hour)
    now = datetime.now()
    for med in current_user["medications"]:
        nd = datetime.strptime(med["next_dose"], "%Y-%m-%d %H:%M")
        time_diff = (nd - now).total_seconds()
        if 0 <= time_diff <= 3600:  # Within the next hour (3600 seconds)
            flash(f" It's almost time to take '{med['medication']}' (Next dose at {med['next_dose']})", "danger")

    return render_template("track.html", user=current_user, medications=current_user["medications"])

# Route to add new medications
@app.route('/add-medication', methods=["GET", "POST"])
def add_medication():
    # Redirect if not logged in
    if "user" not in session:
        return redirect(url_for("home"))

    # Load user data
    users = load_users()
    current_user = users.get(session["user"])

    # Handle form submission
    if request.method == "POST":
        # Get form data
        medication_name = request.form["medication"]
        frequency = request.form["frequency"]
        dosage = request.form["dosage"]
        start_date = request.form["start_date"]
        notes = request.form.get('notes', '')
        now = datetime.now()
        taken = False

        # Parse start date
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")

        # Define frequency intervals
        frequency_map = {
            "once_a_day": timedelta(days=1),
            "twice_a_day": timedelta(hours=12),
            "three_times_a_day": timedelta(hours=8),
            "every_6_hours": timedelta(hours=6),
            "every_8_hours": timedelta(hours=8),
            "every_other_day": timedelta(days=2),
            "weekly": timedelta(weeks=1),
        }

        # Handle custom frequency
        if frequency == "custom":
            custom_days = int(request.form.get("custom_interval_days", 1))
            interval = timedelta(days=custom_days)
        else:
            interval = frequency_map.get(frequency, timedelta(days=1))

        # Calculate next dose time
        next_dose = start_datetime
        while next_dose <= now:
            next_dose += interval

        # Create new medication entry
        new_medication = {
            "medication": medication_name,
            "frequency": frequency,
            "dosage": dosage,
            "start_date": start_date,
            'notes': notes,
            "taken": False,
            "next_dose": next_dose.strftime("%Y-%m-%d %H:%M")
        }

        # Add medication to user's list and save
        current_user["medications"].append(new_medication)
        save_users(users)
        
        # Send confirmation email
        send_email_report(
            to_email=session["user"],
            subject="Your Medication Was Added!",
            body=f"Hi {current_user['first_name']},\n\nYou've added {medication_name} with frequency {frequency}.\n\nThanks for using our system!"
        )

        # Show success message and redirect
        flash(f"Medication '{medication_name}' added. Next dose: {new_medication['next_dose']}", "success")
        return redirect(url_for("track_medications"))

    return render_template("add_medication.html")

# Route to delete a medication
@app.route('/delete-medication', methods=["POST"])
def delete_medication():
    # Redirect if not logged in
    if "user" not in session:
        return redirect(url_for("home"))

    # Get medication name from form
    medication_name = request.form.get("medication_name")

    # Load user data
    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    # Remove medication from list
    updated_meds = [m for m in medications if m["medication"] != medication_name]
    if len(updated_meds) < len(medications):
        user["medications"] = updated_meds
        save_users(users)
        flash(f"Deleted '{medication_name}' successfully.", "success")
    else:
        flash("Medication not found.", "danger")

    return redirect(url_for("track_medications"))

# Route to edit an existing medication
@app.route('/edit-medication/<int:index>', methods=["GET", "POST"])
def edit_medication(index):
    # Redirect if not logged in
    if "user" not in session:
        return redirect(url_for("home"))

    # Load user data
    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    # Validate medication index
    if index < 0 or index >= len(medications):
        flash("Medication not found.", "danger")
        return redirect(url_for("track_medications"))

    medication = medications[index]

    # Handle form submission
    if request.method == "POST":
        # Get form data
        frequency = request.form["frequency"]
        dosage = request.form["dosage"]
        notes = request.form.get('notes', '')
        start_date = request.form["start_date"]

        # Define frequency intervals
        frequency_map = {
            "once_a_day": timedelta(days=1),
            "twice_a_day": timedelta(hours=12),
            "three_times_a_day": timedelta(hours=8),
            "every_6_hours": timedelta(hours=6),
            "every_8_hours": timedelta(hours=8),
            "every_other_day": timedelta(days=2),
            "weekly": timedelta(weeks=1),
        }

        # Recalculate next dose based on updated frequency
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        now = datetime.now()
        interval = frequency_map.get(frequency, timedelta(days=1))

        next_dose = start_datetime
        while next_dose <= now:
            next_dose += interval

        # Update medication data
        medication["frequency"] = frequency
        medication["dosage"] = dosage
        medication["start_date"] = start_date
        medication["notes"] = notes
        medication["next_dose"] = next_dose.strftime("%Y-%m-%d %H:%M")

        # Save changes
        save_users(users)
        flash("Medication updated successfully!", "success")
        return redirect(url_for("track_medications"))

    return render_template("edit_medication.html", medication=medication)

# Route to generate medication report
@app.route('/report')
def generate_report():
    # Redirect if not logged in
    if "user" not in session:
        return redirect(url_for("home"))

    # Load user data
    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    return render_template("report.html", user=user, medications=medications)

# Route to download medication report as PDF
@app.route('/download-report')
def download_report():
    # Redirect if not logged in
    if "user" not in session:
        return redirect(url_for("home"))

    # Load user data
    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    # Create HTTP response for PDF download
    response = make_response()
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=medication_report.pdf"

    # Create PDF using ReportLab
    buffer = response.stream
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    story = []
    styles = getSampleStyleSheet()

    # Add title and patient info
    story.append(Paragraph("Daily/Regular Medication List", styles["Title"]))
    story.append(Paragraph(f"Patient name: {user['first_name']} {user['last_name']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Create table with header row
    table_data = [["Date", "Medication Name", "Frequency", "Next Dose Time"]]

    # Add user's actual medications
    for med in medications:
        table_data.append([
            med["start_date"],
            med["medication"],
            med["frequency"],
            med["next_dose"]
        ])

    # Add blank rows to match the form style (total of 15 rows)
    for _ in range(15 - len(medications)):
        table_data.append(["", "", "", ""])

    # Define table style
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

    # Build PDF and return response
    story.append(table)
    doc.build(story)
    return response

# Route to send medication report to healthcare provider
@app.route('/send-to-provider', methods=["POST"])
def send_to_provider():
    # Redirect if not logged in
    if "user" not in session:
        return redirect(url_for("home"))

    # Load user data
    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    # Create PDF in memory buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    story = []
    styles = getSampleStyleSheet()

    # Add title and patient info
    story.append(Paragraph("Daily/Regular Medication List", styles["Title"]))
    story.append(Paragraph(f"Patient name: {user['first_name']} {user['last_name']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Create table with medications
    table_data = [["Date", "Medication Name", "Frequency", "Next Dose Time"]]
    for med in medications:
        table_data.append([med["start_date"], med["medication"], med["frequency"], med["next_dose"]])
    for _ in range(15 - len(medications)):
        table_data.append(["", "", "", ""])

    # Define table style
    table = Table(table_data, colWidths=[90, 160, 120, 140])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(table)

    # Build PDF and get bytes
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Create email content
    subject = f"Medication Report for {user['first_name']} {user['last_name']}"
    body = f"""This is an automated medication report.

Patient: {user['first_name']} {user['last_name']}
Email: {session['user']}

The medication report is attached as a PDF."""

    # Check if doctor email is available
    provider_email = user.get("doctor_email")
    if not provider_email:
       flash("No doctor email found in profile. Please update it.", "danger")
       return redirect(url_for("profile"))

    # Send email with PDF attachment
    send_email_report(
        to_email=provider_email,
        subject=subject,
        body=body,
        attachment_bytes=pdf_bytes
    )

    flash("Medication report with PDF sent to provider!", "success")
    return redirect(url_for("generate_report"))

# Route to mark a medication as taken
@app.route('/mark-taken/<int:index>', methods=["POST"])
def mark_taken(index):
    # Redirect if not logged in
    if "user" not in session:
        return redirect(url_for("home"))

    # Load user data
    users = load_users()
    user = users.get(session["user"])
    meds = user.get("medications", [])

    # Check if medication index is valid
    if 0 <= index < len(meds):
        # Update last taken timestamp
        meds[index]["last_taken"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Update adherence record for today
        today_str = datetime.now().date().isoformat()
        taken = True
        if "adherence" not in user:
            user["adherence"] = {}
        user["adherence"][today_str] = True

        # Save changes
        save_users(users)
        flash(f"Marked '{meds[index]['medication']}' as taken 💊", "success")
    else:
        flash("Medication not found.", "danger")

    return redirect(url_for("track_medications"))

# Run the application if this script is executed directly
if __name__ == "__main__":
    app.run(debug=True, port=5900)