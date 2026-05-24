from werkzeug.utils import secure_filename
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from flask import Flask, render_template, request, redirect, session, send_file 
import sqlite3
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os



app = Flask(__name__)
app.secret_key = "anti_doping_secret"

# Load ML Model
model = joblib.load("model/doping_model.pkl")

# Database connection
def connect_db():
    conn = sqlite3.connect("anti_doping.db")
    conn.row_factory = sqlite3.Row
    return conn


# Create table
def create_table():
    conn = connect_db()
    cursor = conn.cursor()

    # Create table
def create_table():

    conn = connect_db()
    cursor = conn.cursor()

    # Athletes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS athletes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        sport TEXT,
        performance_growth REAL,
        recovery_rate REAL,
        hormone_level REAL,
        supplement_use INTEGER,
        risk_level TEXT,
        photo TEXT
    )
    """)

    # Prediction History table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prediction_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        athlete_name TEXT,
        risk_level TEXT,
        prediction_date TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    
create_table()


# Login Page
@app.route("/", methods=["GET", "POST"])
def login():

    error = ""

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["user"] = username
            return redirect("/dashboard")

        else:
            error = "Invalid Username or Password"

    return render_template(
        "login.html",
        error=error
    )


# Dashboard
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    search = request.args.get("search", "")

    conn = connect_db()

    if search:
        athletes = conn.execute(
            "SELECT * FROM athletes WHERE name LIKE ?",
            ('%' + search + '%',)
        ).fetchall()
    else:
        athletes = conn.execute(
            "SELECT * FROM athletes"
        ).fetchall()

    total = len(athletes)

    # Count risk levels
    low = len([a for a in athletes if a["risk_level"] == "Low"])
    medium = len([a for a in athletes if a["risk_level"] == "Medium"])
    high = len([a for a in athletes if a["risk_level"] == "High"])

       # ---------- Bar Graph ----------
    plt.figure(figsize=(5, 4))

    plt.bar(
        ["Low", "Medium", "High"],
        [low, medium, high]
    )

    plt.title("Doping Risk Analysis")
    plt.xlabel("Risk Level")
    plt.ylabel("Number of Athletes")

    graph_path = "static/graph.png"
    plt.savefig(graph_path)
    plt.close()

        # ---------- Pie Chart ----------
    plt.figure(figsize=(5, 5))

    risk_counts = [
        low,
        medium,
        high
    ]

    labels = [
        "Low",
        "Medium",
        "High"
    ]

# Prevent crash if no athlete exists
    if sum(risk_counts) > 0:

        plt.pie(
            risk_counts,
            labels=labels,
            autopct='%1.1f%%'
        )

    else:

        plt.text(
            0.5,
            0.5,
            "No Athlete Data",
            ha="center",
            va="center",
            fontsize=14
        )

    plt.title(
        "Risk Distribution"
    )

    pie_path = (
        "static/pie_chart.png"
    )

    plt.savefig(
        pie_path
    )

    plt.close()

# ---------- Sport Analysis Graph ----------
    sports = {}

    for athlete in athletes:

        sport = athlete["sport"]

        if sport in sports:
            sports[sport] += 1
        else:
            sports[sport] = 1

    plt.figure(figsize=(6, 4))

    plt.bar(
        sports.keys(),
        sports.values()
    )

    plt.title(
        "Athletes by Sport"
    )

    plt.xlabel("Sport")
    plt.ylabel("Number of Athletes")

    plt.xticks(rotation=20)

    sport_graph_path = (
        "static/sport_graph.png"
    )

    plt.savefig(
        sport_graph_path
    )

    plt.close()

    conn.close()

    return render_template(
    "dashboard.html",
    athletes=athletes,
    total=total,
    low=low,
    medium=medium,
    high=high,
    search=search
)


# Add Athlete
@app.route("/add", methods=["GET", "POST"])
def add_athlete():

    if "user" not in session:
        return redirect("/")

    if request.method == "POST":

        name = request.form["name"]
        age = int(request.form["age"])
        sport = request.form["sport"]
        performance_growth = float(
            request.form["performance_growth"]
        )
        recovery_rate = float(
            request.form["recovery_rate"]
        )
        hormone_level = float(
            request.form["hormone_level"]
        )
        supplement_use = int(
            request.form["supplement_use"]
        )
        photo = request.files["photo"]

        filename = ""

        if photo and photo.filename != "":

            filename = secure_filename(
                photo.filename
            )

            upload_path = os.path.join(
                "static",
                "uploads",
                filename
            )

            photo.save(
                upload_path
            )
        # ML Prediction
        data = np.array([[
            age,
            performance_growth,
            recovery_rate,
            hormone_level,
            supplement_use
        ]])

        prediction = model.predict(data)[0]

        risk_map = {
            0: "Low",
            1: "Medium",
            2: "High"
        }

        risk_level = risk_map[prediction]

        conn = connect_db()

        conn.execute("""
        INSERT INTO athletes(
        name, age, sport,
        performance_growth,
        recovery_rate,
        hormone_level,
        supplement_use,
        risk_level
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            age,
            sport,
            performance_growth,
            recovery_rate,
            hormone_level,
            supplement_use,
            risk_level
        ))

        # Save prediction history
        conn.execute("""
        INSERT INTO prediction_history(
            athlete_name,
            risk_level
        )
        VALUES (?, ?)
        """, (
            name,
            risk_level
        ))

        conn.commit()
        conn.close()

        return render_template(
            "predict.html",
            name=name,
            risk_level=risk_level
        )
        conn.close()

        return render_template(
    "predict.html",
    name=name,
    risk_level=risk_level
)

    return render_template("add_athlete.html")


# Substance Checker
@app.route("/substances", methods=["GET", "POST"])
def substances():

    if "user" not in session:
        return redirect("/")

    banned_substances = [
        "Steroids",
        "EPO",
        "Human Growth Hormone",
        "Stimulants",
        "Beta Blockers",
        "Anabolic Steroids",
        "Testosterone",
        "Nandrolone"
    ]

    result = ""

    if request.method == "POST":

        substance = request.form[
            "substance"
        ].strip()

        found = False

        for item in banned_substances:

            if substance.lower() == item.lower():

                result = (
                    f"{substance} "
                    f"is BANNED"
                )

                found = True
                break

        if not found:
            result = (
                f"{substance} "
                f"is SAFE"
            )

    return render_template(
        "substances.html",
        substances=banned_substances,
        result=result
    )

# Athlete Profile
@app.route("/athlete/<int:id>")
def athlete_profile(id):

    if "user" not in session:
        return redirect("/")

    conn = connect_db()

    athlete = conn.execute(
        "SELECT * FROM athletes WHERE id=?",
        (id,)
    ).fetchone()

    conn.close()

        # ---------- Medical Analysis ----------

    analysis = ""
    recommendation = ""

    if athlete["risk_level"] == "High":

        analysis = (
            "High hormone level, "
            "rapid performance growth "
            "and recovery indicate "
            "possible doping risk."
        )

        recommendation = (
            "Immediate anti-doping "
            "screening required."
        )

    elif athlete["risk_level"] == "Medium":

        analysis = (
            "Some suspicious indicators "
            "detected in athlete data."
        )

        recommendation = (
            "Regular monitoring "
            "recommended."
        )

    else:

        analysis = (
            "Athlete parameters "
            "appear normal."
        )

        recommendation = (
            "No immediate concern."
        )

    return render_template(
        "athlete_profile.html",
        athlete=athlete,
        analysis=analysis,
        recommendation=recommendation
    )


# Edit Athlete
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_athlete(id):

    if "user" not in session:
        return redirect("/")

    conn = connect_db()

    athlete = conn.execute(
        "SELECT * FROM athletes WHERE id=?",
        (id,)
    ).fetchone()

    if request.method == "POST":

        name = request.form["name"]
        age = request.form["age"]
        sport = request.form["sport"]

        conn.execute("""
        UPDATE athletes
        SET name=?,
        age=?,
        sport=?
        WHERE id=?
        """, (
            name,
            age,
            sport,
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    conn.close()

    return render_template(
        "edit_athlete.html",
        athlete=athlete
    )

# Delete Athlete
@app.route("/delete/<int:id>")
def delete_athlete(id):

    conn = connect_db()

    conn.execute(
        "DELETE FROM athletes WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# Upload Dataset
@app.route("/upload", methods=["GET", "POST"])
def upload_dataset():
    
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":

        file = request.files["dataset"]

        if file:

            df = pd.read_csv(file)

            conn = connect_db()

            for _, row in df.iterrows():

                age = int(row["age"])
                performance_growth = float(
                    row["performance_growth"]
                )
                recovery_rate = float(
                    row["recovery_rate"]
                )
                hormone_level = float(
                    row["hormone_level"]
                )
                supplement_use = int(
                    row["supplement_use"]
                )

                # ML Prediction
                data = np.array([[
                    age,
                    performance_growth,
                    recovery_rate,
                    hormone_level,
                    supplement_use
                ]])

                prediction = model.predict(data)[0]

                risk_map = {
                    0: "Low",
                    1: "Medium",
                    2: "High"
                }

                risk_level = risk_map[prediction]

                conn.execute("""
                INSERT INTO athletes(
                name, age, sport,
                performance_growth,
                recovery_rate,
                hormone_level,
                supplement_use,
                risk_level
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["name"],
                    age,
                    row["sport"],
                    performance_growth,
                    recovery_rate,
                    hormone_level,
                    supplement_use,
                    risk_level
                ))

            conn.commit()
            conn.close()

            return redirect("/dashboard")

    return render_template("upload.html")

# Download Report CSV
@app.route("/download")
def download_report():
    if "user" not in session:
       return redirect("/")

    conn = connect_db()

    query = """
    SELECT
    id,
    name,
    age,
    sport,
    risk_level
    FROM athletes
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    file_name = "athlete_report.csv"

    df.to_csv(file_name, index=False)

    return send_file(
        file_name,
        as_attachment=True
    )
# Download PDF Report
@app.route("/download-pdf")
def download_pdf():
    if "user" not in session:
       return redirect("/")

    conn = connect_db()

    athletes = conn.execute("""
    SELECT
    id,
    name,
    age,
    sport,
    risk_level
    FROM athletes
    """).fetchall()

    conn.close()

    file_name = "athlete_report.pdf"

    pdf = SimpleDocTemplate(file_name)

    data = [
        [
            "ID",
            "Name",
            "Age",
            "Sport",
            "Risk Level"
        ]
    ]

    for athlete in athletes:
        data.append([
            athlete["id"],
            athlete["name"],
            athlete["age"],
            athlete["sport"],
            athlete["risk_level"]
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige)
    ]))

    elements = [table]

    pdf.build(elements)

    return send_file(
        file_name,
        as_attachment=True
    )

# Prediction History
@app.route("/history")
def history():

    if "user" not in session:
        return redirect("/")

    conn = connect_db()

    history_data = conn.execute("""
    SELECT * FROM prediction_history
    ORDER BY prediction_date DESC
    """).fetchall()

    conn.close()

    return render_template(
        "history.html",
        history=history_data
    )


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)