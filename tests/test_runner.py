"""Unit tests for the execution engine."""

import pytest
from engine import runner


def test_normalize_output():
    raw1 = "  42 \r\n"
    raw2 = "42\n\n"
    raw3 = "42"
    assert runner.normalize_output(raw1) == "  42"
    assert runner.normalize_output(raw2) == "42"
    assert runner.normalize_output(raw3) == "42"
    assert runner.outputs_match("Hello World\r\n", "Hello World")
    assert runner.outputs_match("1 2 3 \n", "1 2 3")


def test_python_success():
    code = """
import sys

def solve():
    data = sys.stdin.read().split()
    if not data:
        return
    a, b = int(data[0]), int(data[1])
    print(a + b)

if __name__ == '__main__':
    solve()
"""
    test_cases = [
        {"id": 1, "input_data": "10 20\n", "expected_output": "30", "is_hidden": 0, "points": 50},
        {"id": 2, "input_data": "-5 5\n", "expected_output": "0", "is_hidden": 1, "points": 50},
    ]

    res = runner.evaluate_submission("python", code, test_cases, time_limit_sec=2.0)
    assert res["status"] == "Accepted"
    assert res["score"] == 100
    assert res["max_score"] == 100
    assert len(res["results"]) == 2
    assert res["results"][0]["passed"] is True
    assert res["results"][1]["passed"] is True


def test_python_wrong_answer():
    code = "print(42)"
    test_cases = [
        {"id": 1, "input_data": "10\n", "expected_output": "100", "is_hidden": 0, "points": 50},
    ]
    res = runner.evaluate_submission("python", code, test_cases, time_limit_sec=1.5)
    assert res["status"] == "Wrong Answer"
    assert res["score"] == 0
    assert res["results"][0]["passed"] is False
    assert res["results"][0]["status"] == "FAILED"


def test_python_timeout():
    code = """
while True:
    pass
"""
    test_cases = [
        {"id": 1, "input_data": "", "expected_output": "ok", "is_hidden": 0, "points": 50},
    ]
    # Use short time limit (0.5s) to keep test fast
    res = runner.evaluate_submission("python", code, test_cases, time_limit_sec=0.5)
    assert res["status"] == "Time Limit Exceeded"
    assert res["score"] == 0
    assert res["results"][0]["status"] == "TIMEOUT"


def test_python_runtime_error():
    code = """
x = 1 / 0
"""
    test_cases = [
        {"id": 1, "input_data": "", "expected_output": "1", "is_hidden": 0, "points": 50},
    ]
    res = runner.evaluate_submission("python", code, test_cases, time_limit_sec=1.0)
    assert res["status"] == "Runtime Error"
    assert res["score"] == 0
    assert res["results"][0]["status"] == "RUNTIME_ERROR"
    assert "ZeroDivisionError" in res["results"][0]["error_message"]


def test_cpp_success():
    code = """
#include <iostream>
using namespace std;

int main() {
    long long a, b;
    if (cin >> a >> b) {
        cout << (a * b) << "\\n";
    }
    return 0;
}
"""
    test_cases = [
        {"id": 1, "input_data": "7 6\n", "expected_output": "42", "is_hidden": 0, "points": 40},
        {"id": 2, "input_data": "12 12\n", "expected_output": "144", "is_hidden": 1, "points": 60},
    ]
    res = runner.evaluate_submission("cpp", code, test_cases, time_limit_sec=2.0)
    assert res["status"] == "Accepted"
    assert res["score"] == 100
    assert res["max_score"] == 100
    assert res["results"][0]["passed"] is True
    assert res["results"][1]["passed"] is True


def test_cpp_compilation_error():
    code = """
#include <iostream>
int main() {
    this_is_invalid_syntax_error;;;
    return 0;
}
"""
    test_cases = [
        {"id": 1, "input_data": "1", "expected_output": "1", "is_hidden": 0, "points": 50},
    ]
    res = runner.evaluate_submission("cpp", code, test_cases, time_limit_sec=1.0)
    assert res["status"] == "Compilation Error"
    assert res["score"] == 0
    assert "error" in res["compilation_error"].lower()
    assert res["results"][0]["status"] == "COMPILATION_ERROR"


def test_cpp_timeout():
    code = """
#include <iostream>
int main() {
    volatile int x = 0;
    while(true) {
        x++;
    }
    return 0;
}
"""
    test_cases = [
        {"id": 1, "input_data": "", "expected_output": "0", "is_hidden": 0, "points": 50},
    ]
    res = runner.evaluate_submission("cpp", code, test_cases, time_limit_sec=0.5)
    assert res["status"] == "Time Limit Exceeded"
    assert res["score"] == 0
    assert res["results"][0]["status"] == "TIMEOUT"


def test_cpp_runtime_crash():
    code = """
#include <iostream>
#include <cstdlib>

int main() {
    exit(134);
}
"""
    test_cases = [
        {"id": 1, "input_data": "", "expected_output": "0", "is_hidden": 0, "points": 50},
    ]
    res = runner.evaluate_submission("cpp", code, test_cases, time_limit_sec=1.0)
    assert res["status"] == "Runtime Error"
    assert res["score"] == 0
    assert res["results"][0]["status"] == "RUNTIME_ERROR"
