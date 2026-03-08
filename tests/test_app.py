"""
ACEest Fitness & Gym - Pytest Test Suite
=========================================
Covers all helper functions and Flask API endpoints.
Run with:  pytest tests/ -v --cov=app
"""

import pytest
import json

# We import the app module directly so pure-logic functions can be tested
# without spinning up the full server.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import (
    app,
    get_program,
    calculate_bmi,
    classify_bmi,
    calculate_calories,
    add_member,
    get_member,
    PROGRAMS,
    MEMBERS,
    _member_id_counter,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Flask test client with testing mode enabled."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_members():
    """Clear in-memory member store before every test for isolation."""
    MEMBERS.clear()
    _member_id_counter[0] = 1
    yield
    MEMBERS.clear()
    _member_id_counter[0] = 1


# ─── Unit Tests: get_program ─────────────────────────────────────────────────

class TestGetProgram:
    def test_returns_fl_program(self):
        prog = get_program("FL")
        assert prog is not None
        assert prog["name"] == "Fat Loss"

    def test_returns_mg_program(self):
        prog = get_program("MG")
        assert prog is not None
        assert prog["name"] == "Muscle Gain"

    def test_returns_bg_program(self):
        prog = get_program("BG")
        assert prog is not None
        assert prog["name"] == "Beginner"

    def test_case_insensitive(self):
        assert get_program("fl") is not None
        assert get_program("Fl") is not None

    def test_invalid_code_returns_none(self):
        assert get_program("INVALID") is None
        assert get_program("XX") is None
        assert get_program("") is None

    def test_program_has_workout_key(self):
        prog = get_program("MG")
        assert "workout" in prog
        assert isinstance(prog["workout"], list)

    def test_program_has_diet_key(self):
        prog = get_program("FL")
        assert "diet" in prog
        assert "target_kcal" in prog["diet"]


class TestCalculateBMI:
    def test_normal_bmi(self):
        bmi = calculate_bmi(70, 175)
        assert bmi == pytest.approx(22.86, abs=0.1)

    def test_overweight_bmi(self):
        bmi = calculate_bmi(90, 170)
        assert bmi > 25.0

    def test_underweight_bmi(self):
        bmi = calculate_bmi(45, 170)
        assert bmi < 18.5

    def test_zero_height_raises(self):
        with pytest.raises(ValueError):
            calculate_bmi(70, 0)

    def test_zero_weight_raises(self):
        with pytest.raises(ValueError):
            calculate_bmi(0, 170)

    def test_negative_height_raises(self):
        with pytest.raises(ValueError):
            calculate_bmi(70, -170)

    def test_returns_float(self):
        result = calculate_bmi(70, 175)
        assert isinstance(result, float)



class TestClassifyBMI:
    def test_underweight(self):
        assert classify_bmi(17.0) == "Underweight"

    def test_normal_lower_boundary(self):
        assert classify_bmi(18.5) == "Normal weight"

    def test_normal_upper_boundary(self):
        assert classify_bmi(24.9) == "Normal weight"

    def test_overweight(self):
        assert classify_bmi(27.0) == "Overweight"

    def test_obese(self):
        assert classify_bmi(32.0) == "Obese"

    def test_exactly_25(self):
        assert classify_bmi(25.0) == "Overweight"

    def test_exactly_30(self):
        assert classify_bmi(30.0) == "Obese"



class TestCalculateCalories:
    def test_male_sedentary(self):
        tdee = calculate_calories(70, 175, 25, "male", "sedentary")
        assert isinstance(tdee, int)
        assert 1500 < tdee < 3000

    def test_female_active(self):
        tdee = calculate_calories(60, 165, 30, "female", "active")
        assert tdee > 1800

    def test_very_active_higher_than_sedentary(self):
        sedentary = calculate_calories(80, 180, 35, "male", "sedentary")
        very_active = calculate_calories(80, 180, 35, "male", "very_active")
        assert very_active > sedentary

    def test_invalid_gender_raises(self):
        with pytest.raises(ValueError):
            calculate_calories(70, 175, 25, "other", "moderate")

    def test_invalid_activity_raises(self):
        with pytest.raises(ValueError):
            calculate_calories(70, 175, 25, "male", "extreme")

    def test_male_bmr_formula(self):
        # Manual: BMR_male = 10*70 + 6.25*175 - 5*25 + 5
        #                   = 700 + 1093.75 - 125 + 5 = 1673.75
        # sedentary: 1673.75 * 1.2 = 2008.5 → int = 2008
        tdee = calculate_calories(70, 175, 25, "male", "sedentary")
        assert tdee == 2008


class TestMemberManagement:
    def test_add_member_returns_dict(self):
        m = add_member("Rahul", 28, "FL")
        assert isinstance(m, dict)
        assert m["name"] == "Rahul"

    def test_add_member_assigns_id(self):
        m = add_member("Priya", 25, "MG")
        assert "id" in m
        assert m["id"] == 1

    def test_add_multiple_members_unique_ids(self):
        m1 = add_member("Alice", 22, "BG")
        m2 = add_member("Bob", 30, "FL")
        assert m1["id"] != m2["id"]

    def test_add_member_stores_program(self):
        m = add_member("Carlos", 35, "mg")
        assert m["program"] == "MG"

    def test_add_member_status_active(self):
        m = add_member("Diana", 27, "BG")
        assert m["status"] == "active"

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            add_member("", 25, "FL")

    def test_invalid_age_raises(self):
        with pytest.raises(ValueError):
            add_member("Test", 0, "FL")
        with pytest.raises(ValueError):
            add_member("Test", 200, "FL")

    def test_invalid_program_raises(self):
        with pytest.raises(ValueError):
            add_member("Test", 25, "YOGA")

    def test_get_member_returns_correct_record(self):
        m = add_member("Eve", 29, "MG")
        fetched = get_member(m["id"])
        assert fetched is not None
        assert fetched["name"] == "Eve"

    def test_get_nonexistent_member_returns_none(self):
        assert get_member(9999) is None


class TestHealthRoute:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_ok_status(self, client):
        data = resp = client.get("/health").get_json()
        assert data["status"] == "ok"

    def test_health_returns_service_name(self, client):
        data = client.get("/health").get_json()
        assert "ACEest" in data["service"]


class TestIndexRoute:
    def test_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_index_contains_api_title(self, client):
        resp = client.get("/")
        assert b"ACEest" in resp.data


class TestProgramsRoute:
    def test_list_programs_200(self, client):
        resp = client.get("/programs")
        assert resp.status_code == 200

    def test_list_programs_has_three_entries(self, client):
        data = client.get("/programs").get_json()
        assert data["count"] == 3

    def test_get_fl_program(self, client):
        resp = client.get("/programs/FL")
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Fat Loss"

    def test_get_mg_program(self, client):
        resp = client.get("/programs/MG")
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Muscle Gain"

    def test_get_bg_program(self, client):
        resp = client.get("/programs/BG")
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Beginner"

    def test_invalid_program_returns_404(self, client):
        resp = client.get("/programs/ZUMBA")
        assert resp.status_code == 404

    def test_program_response_has_workout(self, client):
        data = client.get("/programs/MG").get_json()
        assert "workout" in data
        assert isinstance(data["workout"], list)


class TestBMIRoute:
    def test_valid_bmi_returns_200(self, client):
        resp = client.post("/bmi",
                           json={"weight_kg": 70, "height_cm": 175},
                           content_type="application/json")
        assert resp.status_code == 200

    def test_bmi_value_in_response(self, client):
        data = client.post("/bmi",
                           json={"weight_kg": 70, "height_cm": 175},
                           content_type="application/json").get_json()
        assert "bmi" in data
        assert "classification" in data

    def test_bmi_missing_field_returns_400(self, client):
        resp = client.post("/bmi",
                           json={"weight_kg": 70},
                           content_type="application/json")
        assert resp.status_code == 400

    def test_bmi_zero_height_returns_400(self, client):
        resp = client.post("/bmi",
                           json={"weight_kg": 70, "height_cm": 0},
                           content_type="application/json")
        assert resp.status_code == 400


class TestCaloriesRoute:
    def _payload(self, **overrides):
        base = {
            "weight_kg": 70, "height_cm": 175,
            "age": 25, "gender": "male", "activity": "moderate"
        }
        base.update(overrides)
        return base

    def test_valid_calories_returns_200(self, client):
        resp = client.post("/calories", json=self._payload(),
                           content_type="application/json")
        assert resp.status_code == 200

    def test_tdee_in_response(self, client):
        data = client.post("/calories", json=self._payload(),
                           content_type="application/json").get_json()
        assert "tdee_kcal" in data
        assert isinstance(data["tdee_kcal"], int)

    def test_missing_field_returns_400(self, client):
        resp = client.post("/calories",
                           json={"weight_kg": 70},
                           content_type="application/json")
        assert resp.status_code == 400

    def test_invalid_gender_returns_400(self, client):
        resp = client.post("/calories",
                           json=self._payload(gender="alien"),
                           content_type="application/json")
        assert resp.status_code == 400


class TestMembersRoute:
    def test_add_member_returns_201(self, client):
        resp = client.post("/members",
                           json={"name": "Arjun", "age": 30, "program": "MG"},
                           content_type="application/json")
        assert resp.status_code == 201

    def test_add_member_response_has_id(self, client):
        data = client.post("/members",
                           json={"name": "Sita", "age": 22, "program": "FL"},
                           content_type="application/json").get_json()
        assert "member" in data
        assert "id" in data["member"]

    def test_get_member_after_add(self, client):
        post_data = client.post("/members",
                                json={"name": "Ravi", "age": 28, "program": "BG"},
                                content_type="application/json").get_json()
        mid = post_data["member"]["id"]
        resp = client.get(f"/members/{mid}")
        assert resp.status_code == 200
        assert resp.get_json()["member"]["name"] == "Ravi"

    def test_get_nonexistent_member_404(self, client):
        resp = client.get("/members/9999")
        assert resp.status_code == 404

    def test_missing_name_returns_400(self, client):
        resp = client.post("/members",
                           json={"age": 25, "program": "FL"},
                           content_type="application/json")
        assert resp.status_code == 400

    def test_invalid_program_returns_400(self, client):
        resp = client.post("/members",
                           json={"name": "Test", "age": 25, "program": "YOGA"},
                           content_type="application/json")
        assert resp.status_code == 400


class TestLoginRoute:

    def test_login_success(self, client):
        member = add_member("Kavin", 25, "MG")

        resp = client.post("/login",
                           json={"name": "Kavin", "member_id": member["id"]},
                           content_type="application/json")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["member"]["name"] == "Kavin"

    def test_login_invalid_credentials(self, client):
        member = add_member("Rahul", 28, "FL")

        resp = client.post("/login",
                           json={"name": "Wrong", "member_id": member["id"]},
                           content_type="application/json")

        assert resp.status_code == 401

    def test_login_missing_field(self, client):
        resp = client.post("/login",
                           json={"name": "Kavin"},
                           content_type="application/json")

        assert resp.status_code == 400


class TestWorkoutLogRoute:

    def test_log_workout_success(self, client):
        member = add_member("Ravi", 27, "MG")

        resp = client.post("/workout-log",
                           json={
                               "member_id": member["id"],
                               "workout": "Bench Press 5x5",
                               "duration_minutes": 45
                           },
                           content_type="application/json")

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["log"]["workout"] == "Bench Press 5x5"

    def test_log_workout_missing_field(self, client):
        resp = client.post("/workout-log",
                           json={"member_id": 1},
                           content_type="application/json")

        assert resp.status_code == 400