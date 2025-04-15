from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import json
import os
import re

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

@app.route('/medications', methods=["GET", "POST"])
def medications():
    """Add and view medications."""
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current_user = users.get(session["user"])

    if request.method == "POST":
        medication_name = request.form["medication"]
        frequency = request.form["frequency"]
        start_date = request.form["start_date"]

        # Add medication to the user's medication list
        new_medication = {
            "medication": medication_name,
            "frequency": frequency,
            "start_date": start_date
        }
        current_user["medications"].append(new_medication)
        save_users(users)

        flash(f"Medication {medication_name} added with {frequency} frequency starting on {start_date}.", "success")

    return render_template("medications.html", user=current_user, medications=current_user["medications"])

if __name__ == "__main__":
    app.run(debug=True)
