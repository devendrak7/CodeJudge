"""Database handler for Code & Chaos Grader using SQLite with parameterized queries."""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "grader.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and configure a SQLite connection with foreign keys and WAL mode."""
    target_path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(db_path: Optional[str] = None, seed_samples: bool = True) -> None:
    """Initialize the SQLite database with the schema and optional starter assignments."""
    conn = get_connection(db_path)
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_script = f.read()
        conn.executescript(schema_script)
        conn.commit()

        if seed_samples:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM assignments")
            count = cursor.fetchone()[0]
            if count == 0:
                _seed_initial_data(conn)
    finally:
        conn.close()


def _seed_initial_data(conn: sqlite3.Connection) -> None:
    """Seed initial demo assignments for presentation and testing."""
    sample_assignments = [
        (
            "Sum of Multiples (3 & 5)",
            (
                "### Problem Statement\n"
                "If we list all natural numbers below 10 that are multiples of 3 or 5, we get 3, 5, 6 and 9. "
                "The sum of these multiples is 23.\n\n"
                "Write a program that reads an integer `N` from standard input and prints the sum of all "
                "multiples of 3 or 5 strictly less than `N`.\n\n"
                "#### Input Format\n"
                "A single integer `N` (1 <= N <= 100,000).\n\n"
                "#### Output Format\n"
                "A single integer representing the sum."
            ),
            2.0,
            [
                ("10\n", "23", 0, 20),
                ("20\n", "78", 0, 20),
                ("1\n", "0", 1, 10),
                ("100\n", "2318", 1, 25),
                ("1000\n", "233168", 1, 25),
            ],
        ),
        (
            "Strict Palindrome Checker",
            (
                "### Problem Statement\n"
                "Given a single-line string, determine whether it reads the exact same forwards and backwards "
                "(case-sensitive, including spaces and symbols).\n\n"
                "Print `YES` if it is a palindrome, or `NO` otherwise.\n\n"
                "#### Input Format\n"
                "A single line of text.\n\n"
                "#### Output Format\n"
                "`YES` or `NO` (all uppercase)."
            ),
            1.5,
            [
                ("racecar\n", "YES", 0, 25),
                ("Hello World\n", "NO", 0, 25),
                ("radar\n", "YES", 1, 25),
                ("kayak\n", "YES", 1, 25),
            ],
        ),
        (
            "Reverse Array / Sequence",
            (
                "### Problem Statement\n"
                "Read an integer `N`, followed by `N` space-separated integers on the next line. "
                "Output the numbers in reversed order, separated by single spaces.\n\n"
                "#### Input Format\n"
                "Line 1: Integer `N`\n"
                "Line 2: `N` space-separated integers\n\n"
                "#### Output Format\n"
                "The reversed sequence separated by spaces."
            ),
            2.0,
            [
                ("4\n1 2 3 4\n", "4 3 2 1", 0, 30),
                ("1\n99\n", "99", 0, 20),
                ("5\n10 20 30 40 50\n", "50 40 30 20 10", 1, 25),
                ("3\n-5 0 5\n", "5 0 -5", 1, 25),
            ],
        ),
    ]

    cursor = conn.cursor()
    for title, desc, limit, test_cases in sample_assignments:
        cursor.execute(
            "INSERT INTO assignments (title, description, time_limit) VALUES (?, ?, ?)",
            (title, desc, limit),
        )
        assignment_id = cursor.lastrowid
        for inp, exp, hidden, pts in test_cases:
            cursor.execute(
                "INSERT INTO test_cases (assignment_id, input_data, expected_output, is_hidden, points) "
                "VALUES (?, ?, ?, ?, ?)",
                (assignment_id, inp, exp, hidden, pts),
            )
    conn.commit()


def create_assignment(
    title: str,
    description: str,
    time_limit: float,
    test_cases: List[Dict[str, Any]],
    db_path: Optional[str] = None,
) -> int:
    """Create a new assignment along with its test cases inside a transaction."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO assignments (title, description, time_limit) VALUES (?, ?, ?)",
                (title.strip(), description.strip(), float(time_limit)),
            )
            assignment_id = cursor.lastrowid

            for tc in test_cases:
                cursor.execute(
                    "INSERT INTO test_cases (assignment_id, input_data, expected_output, is_hidden, points) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        assignment_id,
                        tc.get("input_data", ""),
                        tc.get("expected_output", "").strip(),
                        1 if tc.get("is_hidden") else 0,
                        int(tc.get("points", 10)),
                    ),
                )
            return int(assignment_id)
    finally:
        conn.close()


def get_assignments(
    assignment_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve all assignments or a single assignment by ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                a.id, 
                a.title, 
                a.description, 
                a.time_limit, 
                a.created_at,
                COUNT(tc.id) as total_tests,
                COALESCE(SUM(tc.points), 0) as max_points
            FROM assignments a
            LEFT JOIN test_cases tc ON a.id = tc.assignment_id
        """
        params: List[Any] = []
        if assignment_id is not None:
            query += " WHERE a.id = ?"
            params.append(assignment_id)

        query += " GROUP BY a.id ORDER BY a.id ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_assignment(assignment_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single assignment by ID."""
    rows = get_assignments(assignment_id=assignment_id, db_path=db_path)
    return rows[0] if rows else None


def delete_assignment(assignment_id: int, db_path: Optional[str] = None) -> bool:
    """Delete an assignment and all cascade-related data."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()


def get_test_cases(
    assignment_id: int,
    include_hidden: bool = False,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve test cases for an assignment.
    If include_hidden is False, returns only visible test cases.
    CRITICAL: Used by student UI to strictly avoid leaking hidden test inputs and expected outputs.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        query = (
            "SELECT id, assignment_id, input_data, expected_output, is_hidden, points "
            "FROM test_cases WHERE assignment_id = ?"
        )
        if not include_hidden:
            query += " AND is_hidden = 0"
        query += " ORDER BY id ASC"
        cursor.execute(query, (assignment_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def save_submission(
    assignment_id: int,
    student_name: str,
    language: str,
    code: str,
    score: int,
    max_score: int,
    status: str,
    execution_time_ms: float,
    test_results: List[Dict[str, Any]],
    db_path: Optional[str] = None,
) -> int:
    """Record a submission and its individual test execution results."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO submissions 
                (assignment_id, student_name, language, code, score, max_score, status, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assignment_id,
                    student_name.strip(),
                    language.lower(),
                    code,
                    int(score),
                    int(max_score),
                    status,
                    float(execution_time_ms),
                ),
            )
            submission_id = cursor.lastrowid

            for res in test_results:
                cursor.execute(
                    """
                    INSERT INTO submission_results 
                    (submission_id, test_case_id, passed, status, actual_output, error_message, execution_time_ms, points_awarded)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        submission_id,
                        res.get("test_case_id"),
                        1 if res.get("passed") else 0,
                        res.get("status", "FAILED"),
                        res.get("actual_output", ""),
                        res.get("error_message", ""),
                        float(res.get("execution_time_ms", 0.0)),
                        int(res.get("points_awarded", 0)),
                    ),
                )
            return int(submission_id)
    finally:
        conn.close()


def get_submissions(
    assignment_id: Optional[int] = None,
    student_name: Optional[str] = None,
    limit: Optional[int] = 100,
    order_asc: bool = False,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve submissions with optional filters and sorting."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                s.id,
                s.assignment_id,
                a.title as assignment_title,
                s.student_name,
                s.language,
                s.score,
                s.max_score,
                s.status,
                s.execution_time_ms,
                s.submitted_at
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            WHERE 1=1
        """
        params: List[Any] = []
        if assignment_id is not None:
            query += " AND s.assignment_id = ?"
            params.append(assignment_id)
        if student_name:
            query += " AND LOWER(s.student_name) = LOWER(?)"
            params.append(student_name.strip())

        order_by = "ORDER BY s.submitted_at ASC, s.id ASC" if order_asc else "ORDER BY s.submitted_at DESC, s.id DESC"
        query += f" {order_by}"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_submission_details(
    submission_id: int,
    is_instructor: bool = False,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get full submission details including per-test case results.
    If is_instructor is False:
      Hides input_data, expected_output, and actual_output for all hidden test cases.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                s.id,
                s.assignment_id,
                a.title as assignment_title,
                s.student_name,
                s.language,
                s.code,
                s.score,
                s.max_score,
                s.status,
                s.execution_time_ms,
                s.submitted_at
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            WHERE s.id = ?
            """,
            (submission_id,),
        )
        sub_row = cursor.fetchone()
        if not sub_row:
            return None

        submission = dict(sub_row)

        cursor.execute(
            """
            SELECT 
                sr.id,
                sr.test_case_id,
                sr.passed,
                sr.status,
                sr.actual_output,
                sr.error_message,
                sr.execution_time_ms,
                sr.points_awarded,
                tc.is_hidden,
                tc.points as points_possible,
                tc.input_data,
                tc.expected_output
            FROM submission_results sr
            JOIN test_cases tc ON sr.test_case_id = tc.id
            WHERE sr.submission_id = ?
            ORDER BY sr.test_case_id ASC
            """,
            (submission_id,),
        )
        res_rows = cursor.fetchall()
        results = []
        for row in res_rows:
            r = dict(row)
            # Mask hidden inputs/outputs for students
            if not is_instructor and r["is_hidden"]:
                r["input_data"] = "[Hidden Test Input]"
                r["expected_output"] = "[Hidden Expected Output]"
                r["actual_output"] = "[Output Suppressed For Hidden Test]"
            results.append(r)

        submission["results"] = results
        return submission
    finally:
        conn.close()


def get_leaderboard(
    assignment_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate leaderboard rankings.
    For each student, find their best submission score.
    Break ties by lowest execution time, then earliest submission.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        query = """
            WITH RankedSubmissions AS (
                SELECT 
                    s.id,
                    s.assignment_id,
                    a.title as assignment_title,
                    s.student_name,
                    s.language,
                    s.score,
                    s.max_score,
                    s.status,
                    s.execution_time_ms,
                    s.submitted_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY s.student_name, s.assignment_id 
                        ORDER BY s.score DESC, s.execution_time_ms ASC, s.submitted_at ASC
                    ) as rn
                FROM submissions s
                JOIN assignments a ON s.assignment_id = a.id
                WHERE (? IS NULL OR s.assignment_id = ?)
            )
            SELECT 
                id,
                assignment_id,
                assignment_title,
                student_name,
                language,
                score,
                max_score,
                status,
                execution_time_ms,
                submitted_at,
                ROUND((CAST(score AS REAL) / CASE WHEN max_score = 0 THEN 1 ELSE max_score END) * 100.0, 1) as percentage
            FROM RankedSubmissions
            WHERE rn = 1
            ORDER BY score DESC, execution_time_ms ASC, submitted_at ASC
        """
        cursor.execute(query, (assignment_id, assignment_id))
        rows = cursor.fetchall()

        results = []
        for rank, row in enumerate(rows, 1):
            item = dict(row)
            item["rank"] = rank
            results.append(item)
        return results
    finally:
        conn.close()


def get_all_submissions_raw(
    assignment_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve raw submission data for analytics in chronological order (preserved wrapper)."""
    return get_submissions(assignment_id=assignment_id, limit=None, order_asc=True, db_path=db_path)
