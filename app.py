"""
ACEest Fitness & Gym - Flask Web Application
============================================
A Flask-based REST API for gym management, serving program data,
member management, and health metrics endpoints.
"""

import os

from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "dev")
APP_TRACK = os.getenv("APP_TRACK", "local")
APP_EXPERIMENT = os.getenv("APP_EXPERIMENT", "control")
APP_COLOR = os.getenv("APP_COLOR", "n/a")

# ─── In-Memory Data Store ────────────────────────────────────────────────────

PROGRAMS = {
    "FL": {
        "name": "Fat Loss",
        "workout": [
            "Mon: 5x5 Back Squat + AMRAP",
            "Tue: EMOM 20min Assault Bike",
            "Wed: Bench Press + 21-15-9",
            "Thu: 10RFT Deadlifts/Box Jumps",
            "Fri: 30min Active Recovery"
        ],
        "diet": {
            "breakfast": "3 Egg Whites + Oats Idli",
            "lunch": "Grilled Chicken + Brown Rice",
            "dinner": "Fish Curry + Millet Roti",
            "target_kcal": 2000
        },
        "color": "#e74c3c"
    },
    "MG": {
        "name": "Muscle Gain",
        "workout": [
            "Mon: Squat 5x5",
            "Tue: Bench Press 5x5",
            "Wed: Deadlift 4x6",
            "Thu: Front Squat 4x8",
            "Fri: Incline Press 4x10",
            "Sat: Barbell Rows 4x10"
        ],
        "diet": {
            "breakfast": "4 Eggs + PB Oats",
            "lunch": "Chicken Biryani (250g Chicken)",
            "dinner": "Mutton Curry + Jeera Rice",
            "target_kcal": 3200
        },
        "color": "#2ecc71"
    },
    "BG": {
        "name": "Beginner",
        "workout": [
            "Circuit Training: Air Squats, Ring Rows, Push-ups",
            "Focus: Technique Mastery & Form (90% Threshold)"
        ],
        "diet": {
            "breakfast": "Idli + Sambar",
            "lunch": "Rice + Dal + Vegetables",
            "dinner": "Chapati + Sabzi",
            "target_kcal": 2200
        },
        "color": "#3498db"
    }
}

MEMBERS  = {}
_member_id_counter = [1]


def _next_id():
    mid = _member_id_counter[0]
    _member_id_counter[0] += 1
    return mid



def get_program(program_code: str) -> dict | None:
    """Return program data for a given code, or None if not found."""
    return PROGRAMS.get(program_code.upper())


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate BMI from weight (kg) and height (cm)."""
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Weight and height must be positive values.")
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 2)


def classify_bmi(bmi: float) -> str:
    """Return WHO BMI classification string."""
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25.0:
        return "Normal weight"
    elif bmi < 30.0:
        return "Overweight"
    else:
        return "Obese"


def calculate_calories(weight_kg: float, height_cm: float,
                       age: int, gender: str, activity: str) -> int:
    """
    Mifflin-St Jeor BMR with activity multiplier.
    gender: 'male' | 'female'
    activity: 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active'
    """
    if gender.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    elif gender.lower() == "female":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    else:
        raise ValueError("Gender must be 'male' or 'female'.")

    multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }
    if activity not in multipliers:
        raise ValueError(f"Activity must be one of {list(multipliers.keys())}")

    return int(bmr * multipliers[activity])


def add_member(name: str, age: int, program_code: str) -> dict:
    """Add a member to the in-memory store and return the record."""
    if not name or not name.strip():
        raise ValueError("Member name cannot be empty.")
    if age <= 0 or age > 120:
        raise ValueError("Age must be between 1 and 120.")
    if program_code.upper() not in PROGRAMS:
        raise ValueError(f"Program '{program_code}' does not exist.")

    member = {
        "id": _next_id(),
        "name": name.strip(),
        "age": age,
        "program": program_code.upper(),
        "status": "active"
    }
    MEMBERS[member["id"]] = member
    return member


def get_member(member_id: int) -> dict | None:
    """Retrieve a member by ID."""
    return MEMBERS.get(member_id)


def deployment_metadata() -> dict:
    """Expose deployment labels so rollout strategies are easy to verify."""
    return {
        "version": APP_VERSION,
        "track": APP_TRACK,
        "experiment": APP_EXPERIMENT,
        "color": APP_COLOR,
    }



HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>ACEest Fitness & Gym</title>
  <style>
    body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; padding: 40px; }
    h1 { color: #d4af37; }
    a { color: #3498db; }
    .endpoint { background: #333; padding: 10px; margin: 8px 0; border-radius: 6px; }
    code { color: #2ecc71; }
  </style>
</head>
<body>
  <h1>🏋️ ACEest Fitness & Gym API</h1>
  <p>Welcome to the ACEest REST API. Available endpoints:</p>
  <div class="endpoint"><code>GET  /health</code> — Health check</div>
  <div class="endpoint"><code>GET  /programs</code> — List all programs</div>
  <div class="endpoint"><code>GET  /programs/&lt;code&gt;</code> — Get single program (FL, MG, BG)</div>
  <div class="endpoint"><code>POST /bmi</code> — Calculate BMI { weight_kg, height_cm }</div>
  <div class="endpoint"><code>POST /calories</code> — Calculate TDEE { weight_kg, height_cm, age, gender, activity }</div>
  <div class="endpoint"><code>POST /members</code> — Add member { name, age, program }</div>
  <div class="endpoint"><code>GET  /members/&lt;id&gt;</code> — Get member by ID</div>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HOME_HTML)


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "ACEest Fitness & Gym API",
        "deployment": deployment_metadata(),
    })


@app.route("/programs")
def list_programs():
    """Return all available training programs."""
    summary = {
        code: {"name": data["name"], "color": data["color"]}
        for code, data in PROGRAMS.items()
    }
    return jsonify({"programs": summary, "count": len(summary)})


@app.route("/programs/<string:code>")
def get_program_route(code):
    """Return full details for a single program."""
    program = get_program(code)
    if program is None:
        return jsonify({"error": f"Program '{code}' not found. Valid codes: FL, MG, BG"}), 404
    return jsonify({"code": code.upper(), **program})


@app.route("/bmi", methods=["POST"])
def bmi_route():
    """Calculate BMI from JSON body: { weight_kg, height_cm }."""
    data = request.get_json(force=True) or {}
    try:
        weight = float(data["weight_kg"])
        height = float(data["height_cm"])
        bmi = calculate_bmi(weight, height)
        return jsonify({
            "bmi": bmi,
            "classification": classify_bmi(bmi),
            "weight_kg": weight,
            "height_cm": height
        })
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/calories", methods=["POST"])
def calories_route():
    """Calculate daily calorie needs."""
    data = request.get_json(force=True) or {}
    try:
        tdee = calculate_calories(
            weight_kg=float(data["weight_kg"]),
            height_cm=float(data["height_cm"]),
            age=int(data["age"]),
            gender=str(data["gender"]),
            activity=str(data["activity"])
        )
        return jsonify({"tdee_kcal": tdee, "input": data})
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/members", methods=["POST"])
def add_member_route():
    """Register a new gym member."""
    data = request.get_json(force=True) or {}
    try:
        member = add_member(
            name=str(data["name"]),
            age=int(data["age"]),
            program_code=str(data["program"])
        )
        return jsonify({"message": "Member added successfully", "member": member}), 201
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/members/<int:member_id>")
def get_member_route(member_id):
    """Retrieve a member record by ID."""
    member = get_member(member_id)
    if member is None:
        return jsonify({"error": f"Member with ID {member_id} not found"}), 404
    return jsonify({"member": member})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True) or {}

    try:
        name = data["name"]
        member_id = int(data["member_id"])

        member = MEMBERS.get(member_id)

        if member and member["name"].lower() == name.lower():
            return jsonify({
                "message": "Login successful",
                "member": member
            })
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400


WORKOUT_LOGS = []

@app.route("/workout-log", methods=["POST"])
def log_workout():
    data = request.get_json(force=True) or {}

    try:
        log = {
            "member_id": int(data["member_id"]),
            "workout": data["workout"],
            "duration_minutes": int(data["duration_minutes"])
        }

        WORKOUT_LOGS.append(log)

        return jsonify({
            "message": "Workout logged successfully",
            "log": log
        }), 201

    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400


PROGRESS = {}

@app.route("/progress", methods=["POST"])
def track_progress():
    data = request.get_json(force=True) or {}

    try:
        member_id = int(data["member_id"])
        weight = float(data["weight_kg"])

        if member_id not in PROGRESS:
            PROGRESS[member_id] = []

        PROGRESS[member_id].append(weight)

        return jsonify({
            "message": "Progress updated",
            "weights": PROGRESS[member_id]
        })

    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400


DIET_LOGS = []

@app.route("/diet-log", methods=["POST"])
def diet_log():
    data = request.get_json(force=True) or {}

    try:
        log = {
            "member_id": int(data["member_id"]),
            "meal": data["meal"],
            "calories": int(data["calories"])
        }

        DIET_LOGS.append(log)

        return jsonify({
            "message": "Meal logged",
            "log": log
        }), 201

    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400


@app.route("/dashboard/<int:member_id>")
def dashboard(member_id):

    member = MEMBERS.get(member_id)

    if not member:
        return jsonify({"error": "Member not found"}), 404

    workouts = [w for w in WORKOUT_LOGS if w["member_id"] == member_id]
    meals = [d for d in DIET_LOGS if d["member_id"] == member_id]
    progress = PROGRESS.get(member_id, [])

    return jsonify({
        "member": member,
        "total_workouts": len(workouts),
        "meals_logged": len(meals),
        "weight_history": progress
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
