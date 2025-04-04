from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import json
import os
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"
USER_DB_FILE = "users.json"

def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r") as file:
            return json.load(file)
    return {}

def save_users(users):
    with open(USER_DB_FILE, "w") as file:
        json.dump(users, file, indent=4)

def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email)

def is_valid_password(password):
    return len(password) >= 7 and re.search(r'[!@#$%&()?:;]', password)

@app.route('/')
def home():
    return render_template("login.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        users = load_users()

        if not email or not password:
            flash("Both fields are required!", "danger")
        elif not is_valid_email(email):
            flash("Invalid email format!", "danger")
        elif email in users:
            flash("Email already registered!", "danger")
        elif not is_valid_password(password):
            flash("Invalid password must be atleast 7 characters and contain 1 special character !@#$%&()?;;", "danger")
        else:
            users[email] = password
            save_users(users)
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("home"))
    return render_template("register.html")
#Create Name First and Last when registering.

@app.route('/login', methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]
    users = load_users()

    if email in users and users[email] == password:
        session["user"] = email
        return redirect(url_for("dashboard"))
    else:
        flash("Invalid email or password!", "danger")
        return redirect(url_for("home"))

@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template("dashboard.html", user=session["user"])

@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

@app.route('/medications', methods=["GET", "POST"])
def medications():
    if "user" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        medication_name = request.form["medication"]
        frequency = request.form["frequency"]
        start_date = request.form["start_date"]

        # For now, just flash a confirmation message
        flash(f"Medication '{medication_name}' added with {frequency} frequency starting on {start_date}.", "success")

    return render_template("medications.html", user=session["user"])



if __name__ == "__main__":
    app.run(debug=True)
