# Import required modules
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from datetime import datetime, timedelta, date
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
import calendar

# Initialize Flask application
app = Flask(__name__)
app.secret_key = "your_secret_key"  # Secret key for session management

# Path to the user data file
USER_DB_FILE = "users.json"

# Load users from JSON file
def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r") as file:
            return json.load(file)
    return {}

# Save users to JSON file
def save_users(users):
    with open(USER_DB_FILE, "w") as file:
        json.dump(users, file, indent=4)

# Email validation helper
def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email)

# Password validation helper
def is_valid_password(password):
    return len(password) >= 7 and re.search(r'[!@#$%&()?:;]', password)

# Route to show login page
@app.route('/')
def landing_page():
    return render_template("index.html")

@app.route('/home')
def home():
    return render_template("login.html")

# Route to register a new user
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        users = load_users()
        if not all([first_name, last_name, email, password]):
            flash("All fields are required!", "danger")
        elif not is_valid_email(email):
            flash("Invalid email format!", "danger")
        elif email in users:
            flash("Email already registered!", "danger")
        elif not is_valid_password(password):
            flash("Password must be at least 7 characters and contain 1 special character (!@#$%&()?;).", "danger")
        else:
            users[email] = {
                "first_name": first_name,
                "last_name": last_name,
                "password": password,
                "medications": []
            }
            save_users(users)
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("home"))
    return render_template("register.html")
# Route to handle user login
@app.route('/login', methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]
    users = load_users()

    # Check if credentials match
    if email in users and users[email]["password"] == password:
        session["user"] = email  # Store user in session
        return redirect(url_for("dashboard"))
    else:
        flash("Invalid email or password!", "danger")
        return redirect(url_for("home"))

# Dashboard page showing user info
@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))
    users = load_users()
    user_data = users.get(session["user"])
    return render_template("dashboard.html", user=user_data)

# Profile page for viewing/editing user information
@app.route('/profile', methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current_email = session["user"]
    user_data = users.get(current_email)

    if request.method == "POST":
        # Update user data from form inputs
        user_data["first_name"] = request.form["first_name"]
        user_data["last_name"] = request.form["last_name"]
        user_data["email"] = request.form["email"]
        user_data["password"] = request.form["password"]
        user_data["pre_exist"] = request.form["pre_exist"]
        user_data["phone"] = request.form["phone"]
        user_data["address"] = request.form["address"]
        user_data["dob"] = request.form["dob"]
        user_data["zip_code"] = request.form["zip_code"]
        user_data["city"] = request.form["city"]
        user_data["doctor_email"] = request.form["doctor_email"]

        # Update user entry in dictionary
        if user_data["email"] != current_email:
            if user_data["email"] in users:
                flash("That email is already in use!", "danger")
                return redirect(url_for("profile"))
            users[user_data["email"]] = user_data
            del users[current_email]
            session["user"] = user_data["email"]
        else:
            users[current_email] = user_data

        save_users(users)
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user_data, email=session["user"])

# Log out the user by clearing the session
@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))
# Route to show medications and check which are due soon
@app.route('/track')
def track_medications():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current_user = users.get(session["user"])

    # Flash a warning if any medication is due within the hour
    now = datetime.now()
    for med in current_user["medications"]:
        nd = datetime.strptime(med["next_dose"], "%Y-%m-%d %H:%M")
        time_diff = (nd - now).total_seconds()
        if 0 <= time_diff <= 3600:
            flash(f" It's almost time to take '{med['medication']}' (Next dose at {med['next_dose']})", "danger")

    return render_template("track.html", user=current_user, medications=current_user["medications"])

# Route to add a new medication
@app.route('/add-medication', methods=["GET", "POST"])
def add_medication():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current_user = users.get(session["user"])

    if request.method == "POST":
        # Get form inputs
        medication_name = request.form["medication"]
        frequency = request.form["frequency"]
        dosage = request.form["dosage"]
        start_date = request.form["start_date"]
        notes = request.form.get('notes', '')
        now = datetime.now()

        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")

        # Frequency-to-time mapping
        frequency_map = {
            "once_a_day": timedelta(days=1),
            "twice_a_day": timedelta(hours=12),
            "three_times_a_day": timedelta(hours=8),
            "every_6_hours": timedelta(hours=6),
            "every_8_hours": timedelta(hours=8),
            "every_other_day": timedelta(days=2),
            "weekly": timedelta(weeks=1),
        }

        # Use custom interval if selected
        if frequency == "custom":
            custom_days = int(request.form.get("custom_interval_days", 1))
            interval = timedelta(days=custom_days)
        else:
            interval = frequency_map.get(frequency, timedelta(days=1))

        # Calculate next dose time
        next_dose = start_datetime
        while next_dose <= now:
            next_dose += interval

        # Add new medication to the user's list
        new_medication = {
            "medication": medication_name,
            "frequency": frequency,
            "dosage": dosage,
            "start_date": start_date,
            "notes": notes,
            "next_dose": next_dose.strftime("%Y-%m-%d %H:%M")
        }

        current_user["medications"].append(new_medication)
        save_users(users)

        # Send confirmation email
        send_email_report(
            to_email=session["user"],
            subject="Your Medication Was Added!",
            body=f"Hi {current_user['first_name']},\n\nYou've added {medication_name} with frequency {frequency}.\n\nThanks for using our system!"
        )

        flash(f"Medication '{medication_name}' added. Next dose: {new_medication['next_dose']}", "success")
        return redirect(url_for("track_medications"))

    return render_template("add_medication.html")

# Route to delete a medication
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

# Route to edit an existing medication
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
        # Get updated values from form
        frequency = request.form["frequency"]
        dosage = request.form["dosage"]
        notes = request.form.get('notes', '')
        start_date = request.form["start_date"]

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

        # Save updated medication
        medication["frequency"] = frequency
        medication["dosage"] = dosage
        medication["start_date"] = start_date
        medication["notes"] = notes
        medication["next_dose"] = next_dose.strftime("%Y-%m-%d %H:%M")

        save_users(users)
        flash("Medication updated successfully!", "success")
        return redirect(url_for("track_medications"))

    return render_template("edit_medication.html", medication=medication)
# Route to display the monthly adherence calendar
@app.route('/calendar')
def calendar_view():
    # Ensure user is logged in
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current_user = users.get(session["user"])

    # Get current month and year
    today = date.today()
    year = today.year
    month = today.month

    # Generate the structure of the current month (weeks of dates)
    cal = calendar.Calendar()
    month_days = cal.monthdatescalendar(year, month)

    # Get the adherence map from user's stored data
    adherence_map = current_user.get("adherence", {})  # Format: {"YYYY-MM-DD": True/False}

    return render_template(
        "calendar.html",
        calendar_weeks=month_days,
        adherence_map=adherence_map,
        today_meds=current_user["medications"]
    )

# Route to view/edit medication adherence for a specific day
@app.route('/calendar/<date>', methods=["GET", "POST"])
def view_day(date):
    # Ensure user is logged in
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    user = users.get(session["user"])

    # Initialize adherence if not present
    if "adherence" not in user:
        user["adherence"] = {}

    if request.method == "POST":
        # Get checked medications
        taken = request.form.getlist("taken")
        meds_taken = [user["medications"][int(i)]["medication"] for i in taken]

        # Save meds taken on that date
        user["adherence"][date] = meds_taken
        save_users(users)

        flash(f"Updated adherence for {date}.", "success")
        return redirect(url_for("view_day", date=date))

    meds = user.get("medications", [])
    taken_today = user["adherence"].get(date, [])

    return render_template("day_view.html", date=date, medications=meds, taken_today=taken_today)

# Route to mark a medication as taken for today
@app.route('/mark-taken/<int:index>', methods=["POST"])
def mark_taken(index):
    # Ensure user is logged in
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    user = users.get(session["user"])
    meds = user.get("medications", [])

    if 0 <= index < len(meds):
        # Store the last taken timestamp
        meds[index]["last_taken"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Update today's adherence status
        today_str = datetime.now().date().isoformat()
        if "adherence" not in user:
            user["adherence"] = {}

        # Just store True if at least one med was marked taken — can customize this per med if needed
        user["adherence"][today_str] = True

        save_users(users)
        flash(f"Marked '{meds[index]['medication']}' as taken 💊", "success")
    else:
        flash("Medication not found.", "danger")

    return redirect(url_for("track_medications"))


# Route to view the report in the browser
@app.route('/report')
def generate_report():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    # Renders a page with a summary of all medications
    return render_template("report.html", user=user, medications=medications)

# Route to download the report as a PDF
@app.route('/download-report')
def download_report():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    # Prepare the response as a downloadable PDF
    response = make_response()
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=medication_report.pdf"

    # Use ReportLab to build PDF in memory
    buffer = response.stream
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    story = []
    styles = getSampleStyleSheet()

    # Add title and patient info
    story.append(Paragraph("Daily/Regular Medication List", styles["Title"]))
    story.append(Paragraph(f"Patient name: {user['first_name']} {user['last_name']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Create table data with medication info
    table_data = [["Date", "Medication Name", "Frequency", "Next Dose Time"]]
    for med in medications:
        table_data.append([
            med["start_date"],
            med["medication"],
            med["frequency"],
            med["next_dose"]
        ])

    # Add empty rows for aesthetics
    for _ in range(15 - len(medications)):
        table_data.append(["", "", "", ""])

    # Build the table
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

# Route to send the report to the healthcare provider via email
@app.route('/send-to-provider', methods=["POST"])
def send_to_provider():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    story = []
    styles = getSampleStyleSheet()

    # Add title and patient info
    story.append(Paragraph("Daily/Regular Medication List", styles["Title"]))
    story.append(Paragraph(f"Patient name: {user['first_name']} {user['last_name']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Table data
    table_data = [["Date", "Medication Name", "Frequency", "Next Dose Time"]]
    for med in medications:
        table_data.append([med["start_date"], med["medication"], med["frequency"], med["next_dose"]])
    for _ in range(15 - len(medications)):
        table_data.append(["", "", "", ""])

    # Style table
    table = Table(table_data, colWidths=[90, 160, 120, 140])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(table)

    # Finalize PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Build email body
    subject = f"Medication Report for {user['first_name']} {user['last_name']}"
    body = f"""This is an automated medication report.

Patient: {user['first_name']} {user['last_name']}
Email: {session['user']}

The medication report is attached as a PDF."""

    provider_email = user.get("doctor_email")
    if not provider_email:
        flash("No doctor email found in profile. Please update it.", "danger")
        return redirect(url_for("profile"))

    # Send the email using helper
    send_email_report(
        to_email=provider_email,
        subject=subject,
        body=body,
        attachment_bytes=pdf_bytes
    )

    flash("Medication report with PDF sent to provider!", "success")
    return redirect(url_for("generate_report"))
def send_email_report(to_email, subject, body, attachment_bytes=None, attachment_filename="report.pdf"):
    """
    Sends an email with an optional PDF attachment using Gmail SMTP.
    Arguments:
        - to_email: Recipient's email address
        - subject: Email subject line
        - body: Text content of the email
        - attachment_bytes: PDF content in bytes, if any
        - attachment_filename: Name to give the attached file
    """

    # Sender email and App password generated from Gmail
    sender_email = "medireminder.notifications@gmail.com"
    app_password = "dkrgfbnhiielfkkt"

    # Set up the MIME structure of the email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Attach plain text body to the email
    msg.attach(MIMEText(body, "plain"))

    # If there's an attachment (PDF), add it to the email
    if attachment_bytes:
        part = MIMEApplication(attachment_bytes, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=attachment_filename)
        msg.attach(part)

    # Try to connect and send the email using Gmail's secure SMTP server
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
        print("Email sent successfully!")  # Useful for console debugging
    except Exception as e:
        print("Error sending email:", str(e))  # Print error if sending fails
def is_valid_email(email):
    """
    Validates the format of an email using a regular expression.
    Returns True if the email matches the pattern, otherwise False.
    """
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email)


def is_valid_password(password):
    """
    Checks if the password is valid:
    - Minimum 7 characters
    - At least one special character from !@#$%&()?:;
    Returns True if valid, False otherwise.
    """
    return len(password) >= 7 and re.search(r'[!@#$%&()?:;]', password)
@app.route('/')
def landing_page():
    """
    Route for the landing page ("/").
    Currently redirects to the index.html template (could be a welcome page).
    """
    return render_template("index.html")


@app.route('/home')
def home():
    """
    Route for the login page ("/home").
    Loads the login.html template for user authentication.
    """
    return render_template("login.html")


@app.route('/about')
def about():
    """
    Route for the About page.
    Loads the about.html template with information about the app or developers.
    """
    return render_template("about.html")


@app.route('/contact')
def contact():
    """
    Route for the Contact page.
    Loads the contact.html template, possibly for user feedback or support.
    """
    return render_template("contact.html")
@app.route('/register', methods=["GET", "POST"])
def register():
    """
    Route to handle user registration.
    If GET request: shows the registration form.
    If POST request: processes the submitted form, validates input, and creates a new user.
    """
    if request.method == "POST":
        # Get form inputs
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        users = load_users()

        # Validate form inputs
        if not all([first_name, last_name, email, password]):
            flash("All fields are required!", "danger")
        elif not is_valid_email(email):
            flash("Invalid email format!", "danger")
        elif email in users:
            flash("Email already registered!", "danger")
        elif not is_valid_password(password):
            flash("Password must be at least 7 characters and contain 1 special character (!@#$%&()?;).", "danger")
        else:
            # Store new user info in the JSON file
            users[email] = {
                "first_name": first_name,
                "last_name": last_name,
                "password": password,
                "medications": []
            }
            save_users(users)
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("home"))
    
    # If GET or form failed, re-render registration page
    return render_template("register.html")


@app.route('/login', methods=["POST"])
def login():
    """
    Route for user login.
    Verifies user credentials and logs the user in by setting the session.
    """
    email = request.form["email"]
    password = request.form["password"]
    users = load_users()

    # Check if email exists and password matches
    if email in users and users[email]["password"] == password:
        session["user"] = email  # Save login session
        return redirect(url_for("dashboard"))
    else:
        flash("Invalid email or password!", "danger")
        return redirect(url_for("home"))
@app.route('/dashboard')
def dashboard():
    """
    Displays the dashboard after login.
    Shows the user's basic information and gives access to other features.
    """
    if "user" not in session:
        return redirect(url_for("home"))  # Redirect to login if not logged in

    users = load_users()
    user_data = users.get(session["user"])  # Get current user data

    return render_template("dashboard.html", user=user_data)  # Show dashboard


@app.route('/logout')
def logout():
    """
    Logs out the user by clearing the session.
    Redirects to the login page.
    """
    session.pop("user", None)
    return redirect(url_for("home"))


@app.route('/profile', methods=["GET", "POST"])
def profile():
    """
    View and edit profile info.
    If POST: updates user profile fields.
    If GET: displays current profile data.
    """
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current_email = session["user"]
    user_data = users.get(current_email)

    if request.method == "POST":
        # Get updated values from form
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        pre_exist = request.form["pre_exist"]
        phone = request.form["phone"]
        address = request.form["address"]
        dob = request.form["dob"]
        zip_code = request.form["zip_code"]
        city = request.form["city"]
        doctor_email = request.form["doctor_email"]

        # Update user data
        user_data.update({
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password": password,
            "pre_exist": pre_exist,
            "phone": phone,
            "address": address,
            "dob": dob,
            "zip_code": zip_code,
            "city": city,
            "doctor_email": doctor_email
        })

        # Handle email change
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
# Route to view current medications and upcoming dose reminders
@app.route('/track')
def track_medications():
    if "user" not in session:
        return redirect(url_for("home"))

    # Load current user's data
    users = load_users()
    current_user = users.get(session["user"])

    now = datetime.now()

    # Loop through all medications to find if any dose is due soon (within the hour)
    for med in current_user["medications"]:
        nd = datetime.strptime(med["next_dose"], "%Y-%m-%d %H:%M")
        time_diff = (nd - now).total_seconds()
        if 0 <= time_diff <= 3600:
            flash(f" It's almost time to take '{med['medication']}' (Next dose at {med['next_dose']})", "danger")

    return render_template("track.html", user=current_user, medications=current_user["medications"])


# Route to add a new medication
@app.route('/add-medication', methods=["GET", "POST"])
def add_medication():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current_user = users.get(session["user"])

    if request.method == "POST":
        # Collect form data
        medication_name = request.form["medication"]
        frequency = request.form["frequency"]
        dosage = request.form["dosage"]
        start_date = request.form["start_date"]
        notes = request.form.get('notes', '')
        now = datetime.now()

        # Convert start date to datetime
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")

        # Frequency map to translate user input to timedelta objects
        frequency_map = {
            "once_a_day": timedelta(days=1),
            "twice_a_day": timedelta(hours=12),
            "three_times_a_day": timedelta(hours=8),
            "every_6_hours": timedelta(hours=6),
            "every_8_hours": timedelta(hours=8),
            "every_other_day": timedelta(days=2),
            "weekly": timedelta(weeks=1),
        }

        # Determine interval for next dose
        if frequency == "custom":
            custom_days = int(request.form.get("custom_interval_days", 1))
            interval = timedelta(days=custom_days)
        else:
            interval = frequency_map.get(frequency, timedelta(days=1))

        # Calculate next dose time based on current time
        next_dose = start_datetime
        while next_dose <= now:
            next_dose += interval

        # Store new medication
        new_medication = {
            "medication": medication_name,
            "frequency": frequency,
            "dosage": dosage,
            "start_date": start_date,
            'notes': notes,
            "next_dose": next_dose.strftime("%Y-%m-%d %H:%M")
        }

        # Save to user's profile
        current_user["medications"].append(new_medication)
        save_users(users)

        # Send confirmation email (optional)
        send_email_report(
            to_email=session["user"],
            subject="Your Medication Was Added!",
            body=f"Hi {current_user['first_name']},\n\nYou've added {medication_name} with frequency {frequency}.\n\nThanks for using our system!"
        )

        # Flash message to UI
        flash(f"Medication '{medication_name}' added. Next dose: {new_medication['next_dose']}", "success")
        return redirect(url_for("track_medications"))

    return render_template("add_medication.html")
# Route to delete a medication from user's list
@app.route('/delete-medication', methods=["POST"])
def delete_medication():
    if "user" not in session:
        return redirect(url_for("home"))

    # Get medication name from the form
    medication_name = request.form.get("medication_name")

    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    # Remove medication with matching name
    updated_meds = [m for m in medications if m["medication"] != medication_name]
    if len(updated_meds) < len(medications):
        user["medications"] = updated_meds
        save_users(users)
        flash(f"Deleted '{medication_name}' successfully.", "success")
    else:
        flash("Medication not found.", "danger")

    return redirect(url_for("track_medications"))


# Route to edit an existing medication by its index
@app.route('/edit-medication/<int:index>', methods=["GET", "POST"])
def edit_medication(index):
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    # Check if index is valid
    if index < 0 or index >= len(medications):
        flash("Medication not found.", "danger")
        return redirect(url_for("track_medications"))

    medication = medications[index]

    if request.method == "POST":
        # Get updated data
        frequency = request.form["frequency"]
        dosage = request.form["dosage"]
        notes = request.form.get('notes', '')
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

        # Update medication details
        medication["frequency"] = frequency
        medication["dosage"] = dosage
        medication["start_date"] = start_date
        medication["notes"] = notes
        medication["next_dose"] = next_dose.strftime("%Y-%m-%d %H:%M")

        save_users(users)
        flash("Medication updated successfully!", "success")
        return redirect(url_for("track_medications"))

    return render_template("edit_medication.html", medication=medication)
# Route to render a visual medication report in HTML
@app.route('/report')
def generate_report():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    return render_template("report.html", user=user, medications=medications)


# Route to download the medication report as a PDF
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

    # Add title and patient info
    story.append(Paragraph("Daily/Regular Medication List", styles["Title"]))
    story.append(Paragraph(f"Patient name: {user['first_name']} {user['last_name']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Table headers
    table_data = [["Date", "Medication Name", "Frequency", "Next Dose Time"]]

    # Fill table with medication data
    for med in medications:
        table_data.append([
            med["start_date"],
            med["medication"],
            med["frequency"],
            med["next_dose"]
        ])

    # Add extra blank rows for style
    for _ in range(15 - len(medications)):
        table_data.append(["", "", "", ""])

    # Style the table
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
from io import BytesIO  # Needed for creating in-memory PDF files

# Route to send the PDF medication report to the user's healthcare provider
@app.route('/send-to-provider', methods=["POST"])
def send_to_provider():
    if "user" not in session:
        return redirect(url_for("home"))

    # Load current user data
    users = load_users()
    user = users.get(session["user"])
    medications = user.get("medications", [])

    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    story = []
    styles = getSampleStyleSheet()

    # Add title and patient information
    story.append(Paragraph("Daily/Regular Medication List", styles["Title"]))
    story.append(Paragraph(f"Patient name: {user['first_name']} {user['last_name']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Table structure
    table_data = [["Date", "Medication Name", "Frequency", "Next Dose Time"]]
    for med in medications:
        table_data.append([med["start_date"], med["medication"], med["frequency"], med["next_dose"]])
    
    # Add blank rows to maintain structure
    for _ in range(15 - len(medications)):
        table_data.append(["", "", "", ""])

    # Format the table
    table = Table(table_data, colWidths=[90, 160, 120, 140])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    story.append(table)
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Compose the email
    subject = f"Medication Report for {user['first_name']} {user['last_name']}"
    body = f"""This is an automated medication report.

Patient: {user['first_name']} {user['last_name']}
Email: {session['user']}

The medication report is attached as a PDF."""

    # Get provider's email from the profile
    provider_email = user.get("doctor_email")
    if not provider_email:
        flash("No doctor email found in profile. Please update it.", "danger")
        return redirect(url_for("profile"))

    # Send the email
    send_email_report(
        to_email=provider_email,
        subject=subject,
        body=body,
        attachment_bytes=pdf_bytes
    )

    flash("Medication report with PDF sent to provider!", "success")
    return redirect(url_for("generate_report"))
# Route to mark a specific medication as taken for today
@app.route('/mark-taken/<int:index>', methods=["POST"])
def mark_taken(index):
    if "user" not in session:
        return redirect(url_for("home"))

    # Load current user data
    users = load_users()
    user = users.get(session["user"])
    meds = user.get("medications", [])

    # Ensure valid index and update "last_taken" time
    if 0 <= index < len(meds):
        meds[index]["last_taken"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Record adherence for today
        today_str = datetime.now().date().isoformat()
        if "adherence" not in user:
            user["adherence"] = {}
        user["adherence"][today_str] = True  # You could also store a list of meds taken

        save_users(users)
        flash(f"Marked '{meds[index]['medication']}' as taken 💊", "success")
    else:
        flash("Medication not found.", "danger")

    return redirect(url_for("track_medications"))
