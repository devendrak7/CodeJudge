-- Database schema for Code & Chaos Grader

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    time_limit REAL NOT NULL DEFAULT 2.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL,
    input_data TEXT NOT NULL DEFAULT '',
    expected_output TEXT NOT NULL,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    points INTEGER NOT NULL DEFAULT 10,
    FOREIGN KEY (assignment_id) REFERENCES assignments (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL,
    student_name TEXT NOT NULL,
    language TEXT NOT NULL,
    code TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    max_score INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    execution_time_ms REAL NOT NULL DEFAULT 0.0,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assignment_id) REFERENCES assignments (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS submission_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL,
    test_case_id INTEGER NOT NULL,
    passed INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    actual_output TEXT,
    error_message TEXT,
    execution_time_ms REAL NOT NULL DEFAULT 0.0,
    points_awarded INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE,
    FOREIGN KEY (test_case_id) REFERENCES test_cases (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_test_cases_assignment ON test_cases(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_student ON submissions(student_name);
CREATE INDEX IF NOT EXISTS idx_submission_results_sub ON submission_results(submission_id);
