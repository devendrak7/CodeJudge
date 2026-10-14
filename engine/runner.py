"""Execution engine for Code & Chaos Grader.

Runs Python and C++ code against test cases with timeout limits, output capture,
and stdout normalization.

SECURITY DISCLAIMER:
This engine relies on subprocess execution with strict timeouts. While timeouts
prevent infinite loops and excessive CPU usage, this does NOT constitute a fully
isolated OS sandbox (e.g., Docker, Linux namespaces/seccomp, or Windows AppContainers).
Do not run untrusted code in an uncontained production environment without containerization.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

# Suppress Windows error reporting dialogs for crashed child processes
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
if sys.platform == "win32":
    try:
        import ctypes
        SEM_NOGPFAULTERRORBOX = 0x0002
        SEM_FAILCRITICALERRORS = 0x0001
        ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX | SEM_FAILCRITICALERRORS)
    except Exception:
        pass

MAX_OUTPUT_CHARS = 10000  # Prevent memory exhaustion on infinite prints
COMPILATION_TIMEOUT_SEC = 15.0


def normalize_output(text: Optional[str]) -> str:
    """Normalize string output by standardizing line endings and stripping trailing whitespace."""
    if text is None:
        return ""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # Strip trailing whitespace on each line
    stripped_lines = [line.rstrip() for line in lines]
    # Remove empty trailing lines
    while stripped_lines and stripped_lines[-1] == "":
        stripped_lines.pop()
    return "\n".join(stripped_lines)


def outputs_match(actual: str, expected: str) -> bool:
    """Compare normalized actual output with normalized expected output."""
    return normalize_output(actual) == normalize_output(expected)


def truncate_output(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """Truncate output if it exceeds max_chars."""
    if len(text) > max_chars:
        return text[:max_chars] + f"\n... [Output truncated after {max_chars} characters]"
    return text


def run_python_test(
    code_path: str,
    input_data: str,
    time_limit_sec: float,
) -> Dict[str, Any]:
    """Execute a Python file with stdin input and enforce a time limit."""
    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-u", code_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=time_limit_sec,
            creationflags=CREATE_NO_WINDOW,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        if proc.returncode != 0:
            return {
                "status": "RUNTIME_ERROR",
                "actual_output": truncate_output(proc.stdout),
                "error_message": truncate_output(proc.stderr or f"Process exited with code {proc.returncode}"),
                "execution_time_ms": round(duration_ms, 2),
            }

        return {
            "status": "COMPLETED",
            "actual_output": truncate_output(proc.stdout),
            "error_message": truncate_output(proc.stderr),
            "execution_time_ms": round(duration_ms, 2),
        }
    except subprocess.TimeoutExpired as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        stdout_txt = e.stdout if isinstance(e.stdout, str) else (e.stdout.decode("utf-8", errors="replace") if e.stdout else "")
        return {
            "status": "TIMEOUT",
            "actual_output": truncate_output(stdout_txt),
            "error_message": f"Time Limit Exceeded (Limit: {time_limit_sec:.2f}s)",
            "execution_time_ms": round(duration_ms, 2),
        }
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "RUNTIME_ERROR",
            "actual_output": "",
            "error_message": str(e),
            "execution_time_ms": round(duration_ms, 2),
        }


def compile_cpp(
    source_path: str,
    binary_path: str,
) -> Tuple[bool, str]:
    """Compile C++ code using g++."""
    try:
        proc = subprocess.run(
            ["g++", "-O2", "-std=c++17", "-Wall", source_path, "-o", binary_path],
            capture_output=True,
            text=True,
            timeout=COMPILATION_TIMEOUT_SEC,
            creationflags=CREATE_NO_WINDOW,
        )
        if proc.returncode != 0:
            return False, truncate_output(proc.stderr or proc.stdout or "Compilation failed.")
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"Compilation timed out after {COMPILATION_TIMEOUT_SEC}s."
    except FileNotFoundError:
        return False, "C++ compiler 'g++' was not found on system PATH."
    except Exception as e:
        return False, f"Unexpected compilation error: {str(e)}"


def run_cpp_test(
    binary_path: str,
    input_data: str,
    time_limit_sec: float,
) -> Dict[str, Any]:
    """Execute a compiled C++ binary with stdin input and enforce a time limit."""
    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            [binary_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=time_limit_sec,
            creationflags=CREATE_NO_WINDOW,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        if proc.returncode != 0:
            return {
                "status": "RUNTIME_ERROR",
                "actual_output": truncate_output(proc.stdout),
                "error_message": truncate_output(proc.stderr or f"Process exited with non-zero exit code: {proc.returncode}"),
                "execution_time_ms": round(duration_ms, 2),
            }

        return {
            "status": "COMPLETED",
            "actual_output": truncate_output(proc.stdout),
            "error_message": truncate_output(proc.stderr),
            "execution_time_ms": round(duration_ms, 2),
        }
    except subprocess.TimeoutExpired as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        stdout_txt = e.stdout if isinstance(e.stdout, str) else (e.stdout.decode("utf-8", errors="replace") if e.stdout else "")
        return {
            "status": "TIMEOUT",
            "actual_output": truncate_output(stdout_txt),
            "error_message": f"Time Limit Exceeded (Limit: {time_limit_sec:.2f}s)",
            "execution_time_ms": round(duration_ms, 2),
        }
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "RUNTIME_ERROR",
            "actual_output": "",
            "error_message": str(e),
            "execution_time_ms": round(duration_ms, 2),
        }


def evaluate_submission(
    language: str,
    code: str,
    test_cases: List[Dict[str, Any]],
    time_limit_sec: float = 2.0,
) -> Dict[str, Any]:
    """
    Main evaluation pipeline for Python and C++ submissions.
    Executes all provided test cases, calculates scores, and returns detailed results.
    """
    language_norm = language.strip().lower()
    if language_norm in ("python", "py"):
        lang_type = "python"
    elif language_norm in ("cpp", "c++"):
        lang_type = "cpp"
    else:
        raise ValueError(f"Unsupported language '{language}'. Supported: python, cpp")

    # Create isolated temp workspace
    temp_dir = tempfile.mkdtemp(prefix="chaos_grader_")
    try:
        if lang_type == "python":
            source_file = os.path.join(temp_dir, "solution.py")
            with open(source_file, "w", encoding="utf-8") as f:
                f.write(code)

            return _run_test_suite_python(source_file, test_cases, time_limit_sec)

        else:  # C++
            source_file = os.path.join(temp_dir, "solution.cpp")
            binary_file = os.path.join(temp_dir, "solution.exe")
            with open(source_file, "w", encoding="utf-8") as f:
                f.write(code)

            compiled, compile_err = compile_cpp(source_file, binary_file)
            if not compiled:
                # Compilation failed: mark all test cases as COMPILATION_ERROR
                total_possible = sum(int(tc.get("points", 10)) for tc in test_cases)
                res_list = []
                for tc in test_cases:
                    res_list.append({
                        "test_case_id": tc.get("id"),
                        "is_hidden": tc.get("is_hidden", 0),
                        "passed": False,
                        "status": "COMPILATION_ERROR",
                        "points_awarded": 0,
                        "points_possible": int(tc.get("points", 10)),
                        "execution_time_ms": 0.0,
                        "actual_output": "",
                        "expected_output": tc.get("expected_output", ""),
                        "input_data": tc.get("input_data", ""),
                        "error_message": compile_err,
                    })
                return {
                    "score": 0,
                    "max_score": total_possible,
                    "status": "Compilation Error",
                    "execution_time_ms": 0.0,
                    "compilation_error": compile_err,
                    "results": res_list,
                }

            return _run_test_suite_cpp(binary_file, test_cases, time_limit_sec)

    finally:
        # Guarantee cleanup of all temporary artifacts
        shutil.rmtree(temp_dir, ignore_errors=True)


def _run_test_suite_python(
    source_file: str,
    test_cases: List[Dict[str, Any]],
    time_limit_sec: float,
) -> Dict[str, Any]:
    """Run all test cases against a Python source file."""
    total_score = 0
    total_possible = 0
    total_time_ms = 0.0
    all_passed = True
    any_timeout = False
    any_runtime_err = False
    results = []

    for tc in test_cases:
        points = int(tc.get("points", 10))
        total_possible += points
        input_data = tc.get("input_data", "")
        expected_output = tc.get("expected_output", "")

        run_res = run_python_test(source_file, input_data, time_limit_sec)
        total_time_ms += run_res["execution_time_ms"]

        if run_res["status"] == "COMPLETED":
            if outputs_match(run_res["actual_output"], expected_output):
                test_passed = True
                status_str = "PASSED"
                points_earned = points
                total_score += points
            else:
                test_passed = False
                status_str = "FAILED"
                points_earned = 0
                all_passed = False
        elif run_res["status"] == "TIMEOUT":
            test_passed = False
            status_str = "TIMEOUT"
            points_earned = 0
            all_passed = False
            any_timeout = True
        else:  # RUNTIME_ERROR
            test_passed = False
            status_str = "RUNTIME_ERROR"
            points_earned = 0
            all_passed = False
            any_runtime_err = True

        results.append({
            "test_case_id": tc.get("id"),
            "is_hidden": tc.get("is_hidden", 0),
            "passed": test_passed,
            "status": status_str,
            "points_awarded": points_earned,
            "points_possible": points,
            "execution_time_ms": run_res["execution_time_ms"],
            "actual_output": run_res["actual_output"],
            "expected_output": expected_output,
            "input_data": input_data,
            "error_message": run_res["error_message"],
        })

    overall_status = _determine_overall_status(all_passed, any_timeout, any_runtime_err)
    return {
        "score": total_score,
        "max_score": total_possible,
        "status": overall_status,
        "execution_time_ms": round(total_time_ms, 2),
        "compilation_error": None,
        "results": results,
    }


def _run_test_suite_cpp(
    binary_file: str,
    test_cases: List[Dict[str, Any]],
    time_limit_sec: float,
) -> Dict[str, Any]:
    """Run all test cases against a compiled C++ binary."""
    total_score = 0
    total_possible = 0
    total_time_ms = 0.0
    all_passed = True
    any_timeout = False
    any_runtime_err = False
    results = []

    for tc in test_cases:
        points = int(tc.get("points", 10))
        total_possible += points
        input_data = tc.get("input_data", "")
        expected_output = tc.get("expected_output", "")

        run_res = run_cpp_test(binary_file, input_data, time_limit_sec)
        total_time_ms += run_res["execution_time_ms"]

        if run_res["status"] == "COMPLETED":
            if outputs_match(run_res["actual_output"], expected_output):
                test_passed = True
                status_str = "PASSED"
                points_earned = points
                total_score += points
            else:
                test_passed = False
                status_str = "FAILED"
                points_earned = 0
                all_passed = False
        elif run_res["status"] == "TIMEOUT":
            test_passed = False
            status_str = "TIMEOUT"
            points_earned = 0
            all_passed = False
            any_timeout = True
        else:  # RUNTIME_ERROR
            test_passed = False
            status_str = "RUNTIME_ERROR"
            points_earned = 0
            all_passed = False
            any_runtime_err = True

        results.append({
            "test_case_id": tc.get("id"),
            "is_hidden": tc.get("is_hidden", 0),
            "passed": test_passed,
            "status": status_str,
            "points_awarded": points_earned,
            "points_possible": points,
            "execution_time_ms": run_res["execution_time_ms"],
            "actual_output": run_res["actual_output"],
            "expected_output": expected_output,
            "input_data": input_data,
            "error_message": run_res["error_message"],
        })

    overall_status = _determine_overall_status(all_passed, any_timeout, any_runtime_err)
    return {
        "score": total_score,
        "max_score": total_possible,
        "status": overall_status,
        "execution_time_ms": round(total_time_ms, 2),
        "compilation_error": None,
        "results": results,
    }


def _determine_overall_status(all_passed: bool, any_timeout: bool, any_runtime_err: bool) -> str:
    """Determine submission headline status."""
    if all_passed:
        return "Accepted"
    if any_timeout:
        return "Time Limit Exceeded"
    if any_runtime_err:
        return "Runtime Error"
    return "Wrong Answer"
