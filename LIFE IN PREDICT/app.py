from flask import Flask, render_template, request, redirect, url_for, session, send_file, Response
import mysql.connector
import pandas as pd
import pickle
import io

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Load the model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# MySQL config
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Nspatil@05",
    "database": "life_insurance_db"
}

# Insert prediction into DB
def insert_to_db(age, sex, bmi, children, smoker, region, insurance_risk):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO insurance_data (age, sex, bmi, children, smoker, region, insurance_risk)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (age, sex, bmi, children, smoker, region, insurance_risk))
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")

@app.route("/")
def root():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin123":
            session["username"] = request.form["username"]
            return redirect(url_for("home"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error)

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/home")
def home():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("home.html", username=session["username"])

@app.route("/predict", methods=["GET", "POST"])
def predict():
    if "username" not in session:
        return redirect(url_for("login"))

    prediction, raw_prediction = "", ""
    confidence_level = ""  # New variable for confidence level
    if request.method == "POST":
        try:
            data = {
                "age": int(request.form["age"]),
                "sex": request.form["sex"],
                "bmi": float(request.form["bmi"]),
                "children": int(request.form["children"]),
                "smoker": request.form["smoker"],
                "region": request.form["region"]
            }

            input_df = pd.DataFrame([data])
            result = model.predict_proba(input_df)[0][1]  # Get probability for the positive class
            confidence_level = f"{result * 100:.2f}%"  # Confidence level as percentage

            insurance_risk = int(result >= 0.5)
            prediction = "High Risk of High Charges" if insurance_risk else "Low Risk of High Charges"

            # Insert prediction into DB
            insert_to_db(data["age"], data["sex"], data["bmi"], data["children"], data["smoker"], data["region"],
                         insurance_risk)

        except Exception as e:
            prediction = f"Error: {str(e)}"

    return render_template("index.html", prediction=prediction, raw_prediction=confidence_level)  # Pass confidence level to template

@app.route("/recent-predictions")
def recent_predictions():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM insurance_data ORDER BY id DESC LIMIT 5")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("recent_predictions.html", data=data)

@app.route("/history")
def history():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM insurance_data ORDER BY id DESC")
    history_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("history.html", history=history_data)

@app.route("/export-csv")
def export_csv():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = mysql.connector.connect(**db_config)
    df = pd.read_sql("SELECT * FROM insurance_data", conn)
    conn.close()
    csv_data = df.to_csv(index=False)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=insurance_predictions.csv"}
    )

@app.route("/stats")
def stats():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS total, SUM(insurance_risk) AS high_risk FROM insurance_data")
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("stats.html", total=result["total"], high_risk=result["high_risk"])

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    message = ""
    if request.method == "POST":
        message = "Thanks for your feedback!"
    return render_template("feedback.html", message=message)

@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    message = ""
    if request.method == "POST":
        if request.form["current_password"] == "admin123":
            message = "Password changed successfully! (Mock)"
        else:
            message = "Incorrect current password."
    return render_template("change_password.html", message=message)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    message = ""
    if request.method == "POST":
        email = request.form["email"]
        message = f"Reset link sent to {email} (Mock)"
    return render_template("forgot_password.html", message=message)

if __name__ == "__main__":
    app.run(debug=True)
