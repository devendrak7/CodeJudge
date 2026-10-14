"""Unit tests for the database layer."""

import os
import tempfile
import pytest
from database import db_handler


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_handler.init_db(db_path=path, seed_samples=False)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def test_init_and_seed_db(temp_db):
    # Test seeding
    db_handler.init_db(db_path=temp_db, seed_samples=True)
    assignments = db_handler.get_assignments(db_path=temp_db)
    assert len(assignments) >= 3
    assert any("Sum of Multiples" in a["title"] for a in assignments)


def test_create_and_get_assignment(temp_db):
    test_cases = [
        {"input_data": "1 2\n", "expected_output": "3", "is_hidden": 0, "points": 10},
        {"input_data": "5 5\n", "expected_output": "10", "is_hidden": 1, "points": 20},
    ]
    assignment_id = db_handler.create_assignment(
        title="Add Two Numbers",
        description="Read two ints and output sum.",
        time_limit=1.5,
        test_cases=test_cases,
        db_path=temp_db,
    )
    assert assignment_id > 0

    assignment = db_handler.get_assignment(assignment_id, db_path=temp_db)
    assert assignment is not None
    assert assignment["title"] == "Add Two Numbers"
    assert assignment["time_limit"] == 1.5
    assert assignment["total_tests"] == 2
    assert assignment["max_points"] == 30


def test_hidden_test_cases_filtering(temp_db):
    test_cases = [
        {"input_data": "visible_in", "expected_output": "visible_out", "is_hidden": 0, "points": 10},
        {"input_data": "secret_in", "expected_output": "secret_out", "is_hidden": 1, "points": 15},
    ]
    assignment_id = db_handler.create_assignment(
        title="Privacy Test",
        description="Testing privacy",
        time_limit=2.0,
        test_cases=test_cases,
        db_path=temp_db,
    )

    # Student perspective (include_hidden = False)
    student_cases = db_handler.get_test_cases(assignment_id, include_hidden=False, db_path=temp_db)
    assert len(student_cases) == 1
    assert student_cases[0]["input_data"] == "visible_in"
    assert student_cases[0]["is_hidden"] == 0

    # Instructor perspective (include_hidden = True)
    all_cases = db_handler.get_test_cases(assignment_id, include_hidden=True, db_path=temp_db)
    assert len(all_cases) == 2


def test_submission_and_masking(temp_db):
    test_cases = [
        {"input_data": "10\n", "expected_output": "20", "is_hidden": 0, "points": 50},
        {"input_data": "99\n", "expected_output": "198", "is_hidden": 1, "points": 50},
    ]
    assignment_id = db_handler.create_assignment(
        title="Double It",
        description="Output x * 2",
        time_limit=2.0,
        test_cases=test_cases,
        db_path=temp_db,
    )
    tcs = db_handler.get_test_cases(assignment_id, include_hidden=True, db_path=temp_db)

    results = [
        {
            "test_case_id": tcs[0]["id"],
            "passed": True,
            "status": "PASSED",
            "actual_output": "20",
            "error_message": "",
            "execution_time_ms": 12.5,
            "points_awarded": 50,
        },
        {
            "test_case_id": tcs[1]["id"],
            "passed": False,
            "status": "FAILED",
            "actual_output": "100",
            "error_message": "",
            "execution_time_ms": 15.0,
            "points_awarded": 0,
        },
    ]

    sub_id = db_handler.save_submission(
        assignment_id=assignment_id,
        student_name="Alice",
        language="python",
        code="print(int(input()) * 2)",
        score=50,
        max_score=100,
        status="Wrong Answer",
        execution_time_ms=27.5,
        test_results=results,
        db_path=temp_db,
    )

    # Check student view: hidden outputs MUST be masked
    student_details = db_handler.get_submission_details(sub_id, is_instructor=False, db_path=temp_db)
    assert student_details is not None
    assert len(student_details["results"]) == 2
    hidden_res = [r for r in student_details["results"] if r["is_hidden"] == 1][0]
    assert "[Hidden" in hidden_res["input_data"]
    assert "[Hidden" in hidden_res["expected_output"]
    assert "[Output Suppressed" in hidden_res["actual_output"]

    # Check instructor view: instructor sees everything
    instructor_details = db_handler.get_submission_details(sub_id, is_instructor=True, db_path=temp_db)
    inst_hidden_res = [r for r in instructor_details["results"] if r["is_hidden"] == 1][0]
    assert inst_hidden_res["input_data"] == "99\n"
    assert inst_hidden_res["expected_output"] == "198"
    assert inst_hidden_res["actual_output"] == "100"


def test_leaderboard_ranking(temp_db):
    assignment_id = db_handler.create_assignment(
        title="Fast Math",
        description="Speed math",
        time_limit=1.0,
        test_cases=[{"input_data": "1", "expected_output": "1", "is_hidden": 0, "points": 100}],
        db_path=temp_db,
    )
    tc = db_handler.get_test_cases(assignment_id, include_hidden=True, db_path=temp_db)[0]

    # Student 1: Bob, score 100, time 50ms
    db_handler.save_submission(
        assignment_id, "Bob", "cpp", "int main(){}", 100, 100, "Accepted", 50.0,
        [{"test_case_id": tc["id"], "passed": True, "status": "PASSED", "actual_output": "1", "error_message": "", "execution_time_ms": 50.0, "points_awarded": 100}],
        db_path=temp_db,
    )
    # Student 2: Alice, score 100, time 20ms (Alice should be rank 1 because faster)
    db_handler.save_submission(
        assignment_id, "Alice", "python", "print(1)", 100, 100, "Accepted", 20.0,
        [{"test_case_id": tc["id"], "passed": True, "status": "PASSED", "actual_output": "1", "error_message": "", "execution_time_ms": 20.0, "points_awarded": 100}],
        db_path=temp_db,
    )
    # Student 3: Charlie, score 80
    db_handler.save_submission(
        assignment_id, "Charlie", "python", "print(0)", 80, 100, "Wrong Answer", 10.0,
        [{"test_case_id": tc["id"], "passed": False, "status": "FAILED", "actual_output": "0", "error_message": "", "execution_time_ms": 10.0, "points_awarded": 0}],
        db_path=temp_db,
    )

    lb = db_handler.get_leaderboard(assignment_id=assignment_id, db_path=temp_db)
    assert len(lb) == 3
    assert lb[0]["student_name"] == "Alice"
    assert lb[0]["rank"] == 1
    assert lb[1]["student_name"] == "Bob"
    assert lb[1]["rank"] == 2
    assert lb[2]["student_name"] == "Charlie"
    assert lb[2]["rank"] == 3
