"""
Dark Pattern Detector - Main Flask Application
Run: python app.py
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
import json
from datetime import datetime

from detector import analyze_url, analyze_text
from database import init_db, save_result, get_history, save_feedback

app = Flask(__name__)
app.secret_key = "dark_pattern_detector_2024"

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "app.db")

with app.app_context():
    init_db(DB_PATH)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyzer")
def analyzer():
    return render_template("analyzer.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    url = request.form.get("url", "").strip()
    if not url:
        return render_template("analyzer.html", error="Please enter a URL.")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    result = analyze_url(url)
    if result.get("error"):
        return render_template("analyzer.html", error=result["error"])
    save_result(DB_PATH, url, result["score"], json.dumps(result["patterns"]))
    return render_template("result.html", result=result, url=url)


@app.route("/analyze_text", methods=["POST"])
def analyze_text_route():
    data = request.get_json()
    text = data.get("text", "")
    result = analyze_text(text)
    return jsonify(result)


@app.route("/compare")
def compare():
    return render_template("compare.html")


@app.route("/compare_urls", methods=["POST"])
def compare_urls():
    url1 = request.form.get("url1", "").strip()
    url2 = request.form.get("url2", "").strip()
    if not url1 or not url2:
        return render_template("compare.html", error="Please enter both URLs.")
    if not url1.startswith(("http://", "https://")):
        url1 = "https://" + url1
    if not url2.startswith(("http://", "https://")):
        url2 = "https://" + url2
    result1 = analyze_url(url1)
    result2 = analyze_url(url2)
    return render_template("compare.html", result1=result1, result2=result2, url1=url1, url2=url2)


@app.route("/dashboard")
def dashboard():
    history = get_history(DB_PATH, limit=50)
    pattern_totals = {"urgency": 0, "scarcity": 0, "social_pressure": 0, "confirmshaming": 0}
    for row in history:
        try:
            patterns = json.loads(row["patterns"])
            for k in pattern_totals:
                pattern_totals[k] += len(patterns.get(k, []))
        except Exception:
            pass
    return render_template("dashboard.html", history=history, pattern_totals=pattern_totals)


@app.route("/history")
def history():
    rows = get_history(DB_PATH, limit=100)
    return render_template("history.html", history=rows)


@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json()
    url = data.get("url", "")
    vote = data.get("vote", "")
    save_feedback(DB_PATH, url, vote)
    return jsonify({"status": "ok"})


@app.route("/screenshot", methods=["POST"])
def screenshot():
    try:
        import pytesseract
        from PIL import Image
        import io
        file = request.files.get("image")
        if not file:
            return jsonify({"error": "No image uploaded."})
        img = Image.open(io.BytesIO(file.read()))
        text = pytesseract.image_to_string(img)
        if not text.strip():
            return jsonify({"error": "No text found in image."})
        result = analyze_text(text)
        return jsonify(result)
    except ImportError:
        return jsonify({"error": "OCR not available. Install pytesseract and Pillow to enable this feature."})
    except Exception as e:
        return jsonify({"error": f"OCR failed: {str(e)}"})


@app.route("/learn")
def learn():
    return render_template("learn.html")


@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    print("\n  Dark Pattern Detector starting...")
    print("   Visit: http://localhost:5000\n")
    app.run(debug=True, port=5000)
