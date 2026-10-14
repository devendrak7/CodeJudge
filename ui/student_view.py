"""Student portal UI for viewing assignments, submitting code, and reviewing test results."""

from __future__ import annotations

import streamlit as st
from database import db_handler
from engine import runner

PYTHON_TEMPLATE = """# Write your solution here
import sys

def solve():
    # Read all input from standard input
    input_text = sys.stdin.read().split()
    if not input_text:
        return
    
    # Example parsing:
    # n = int(input_text[0])
    # ...
    # print(answer)

if __name__ == '__main__':
    solve()
"""

CPP_TEMPLATE = """// Write your C++ solution here
#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read input from standard input
    // Example:
    // int n;
    // if (cin >> n) {
    //     cout << n << "\\n";
    // }

    return 0;
}
"""


def render_student_view() -> None:
    st.header("📝 Student Portal — Code & Submission")
    st.caption("Select an assignment, write or upload your solution, and receive instant automated grading.")

    # 1. Fetch available assignments
    assignments = db_handler.get_assignments()
    if not assignments:
        st.warning("⚠️ No assignments are currently available. Please ask your instructor to publish one.")
        return

    assignment_options = {f"#{a['id']}: {a['title']} ({a['max_points']} pts, {a['time_limit']}s limit)": a["id"] for a in assignments}
    selected_label = st.selectbox("📌 Select Assignment", list(assignment_options.keys()))
    assignment_id = assignment_options[selected_label]
    assignment = db_handler.get_assignment(assignment_id)

    # 2. Display Assignment Details
    with st.container(border=True):
        col_title, col_meta = st.columns([3, 1])
        with col_title:
            st.subheader(assignment["title"])
        with col_meta:
            st.metric("Max Score", f"{assignment['max_points']} pts")
            st.metric("Time Limit", f"{assignment['time_limit']}s / test")

        st.markdown(assignment["description"])

    # 3. Visible Sample Test Cases
    visible_tests = db_handler.get_test_cases(assignment_id, include_hidden=False)
    with st.expander(f"📋 Sample Test Cases ({len(visible_tests)} visible)", expanded=True):
        st.info("🔒 Hidden test cases are also evaluated to assess edge cases. Inputs and expected outputs for hidden tests remain strictly confidential.")
        if visible_tests:
            cols = st.columns(len(visible_tests)) if len(visible_tests) <= 3 else [st]
            for idx, tc in enumerate(visible_tests, 1):
                st.markdown(f"**Sample Case {idx}** ({tc['points']} points)")
                st.text(f"Input:\n{tc['input_data'] if tc['input_data'] else '(No input)'}")
                st.text(f"Expected Output:\n{tc['expected_output']}")
                st.divider()

    # 4. Student Information & Code Submission Form
    st.subheader("💻 Submit Solution")
    col_name, col_lang = st.columns([2, 1])

    with col_name:
        default_name = st.session_state.get("student_name", "Student_Alpha")
        student_name = st.text_input("Your Full Name / Student ID", value=default_name)
        st.session_state["student_name"] = student_name

    with col_lang:
        language = st.selectbox("Programming Language", ["Python", "C++"], index=0)

    # File upload or code editor
    input_method = st.radio("Submission Method", ["Interactive Code Editor", "Upload Source File (.py / .cpp)"], horizontal=True)

    code_content = ""
    default_code = PYTHON_TEMPLATE if language == "Python" else CPP_TEMPLATE

    if input_method == "Interactive Code Editor":
        # Keep track in session state
        code_key = f"code_editor_{assignment_id}_{language}"
        if code_key not in st.session_state:
            st.session_state[code_key] = default_code
        code_content = st.text_area(
            "Source Code",
            value=st.session_state[code_key],
            height=320,
            help="Write your solution reading from standard input and printing to standard output.",
        )
        st.session_state[code_key] = code_content
    else:
        file_ext = [".py"] if language == "Python" else [".cpp", ".cc", ".cxx"]
        uploaded_file = st.file_uploader(f"Choose a {language} file", type=[e.lstrip(".") for e in file_ext])
        if uploaded_file is not None:
            code_content = uploaded_file.getvalue().decode("utf-8", errors="replace")
            st.code(code_content, language="python" if language == "Python" else "cpp")

    # 5. Grading Trigger
    if st.button("🚀 Run & Submit Code", type="primary", use_container_width=True):
        if not student_name.strip():
            st.error("Please enter your name before submitting.")
            return

        if not code_content.strip():
            st.error("Please provide non-empty code to submit.")
            return

        with st.spinner("⚡ Compiling, executing, and evaluating against all test cases..."):
            # Fetch ALL test cases (visible + hidden) for the execution engine
            all_tests = db_handler.get_test_cases(assignment_id, include_hidden=True)
            eval_result = runner.evaluate_submission(
                language=language.lower(),
                code=code_content,
                test_cases=all_tests,
                time_limit_sec=assignment["time_limit"],
            )

            # Save submission into SQLite database
            sub_id = db_handler.save_submission(
                assignment_id=assignment_id,
                student_name=student_name,
                language=language.lower(),
                code=code_content,
                score=eval_result["score"],
                max_score=eval_result["max_score"],
                status=eval_result["status"],
                execution_time_ms=eval_result["execution_time_ms"],
                test_results=eval_result["results"],
            )

        # 6. Display Results Card
        st.success(f"Submission #{sub_id} evaluated successfully!")
        _render_submission_result_card(eval_result)

    # 7. Student Previous Submissions
    if student_name.strip():
        st.divider()
        st.subheader("📜 Your Recent Submissions for this Assignment")
        student_subs = db_handler.get_submissions(assignment_id=assignment_id, student_name=student_name)
        if student_subs:
            history_rows = []
            for s in student_subs[:10]:
                history_rows.append({
                    "Sub ID": f"#{s['id']}",
                    "Language": s["language"].upper(),
                    "Score": f"{s['score']} / {s['max_score']}",
                    "Status": s["status"],
                    "Time (ms)": f"{s['execution_time_ms']:.1f} ms",
                    "Submitted At": s["submitted_at"],
                })
            st.dataframe(history_rows, use_container_width=True)
        else:
            st.caption("No previous submissions recorded for this student name.")


def _render_submission_result_card(eval_result: dict) -> None:
    """Render the evaluation breakdown, strictly masking hidden test cases."""
    status = eval_result["status"]
    score = eval_result["score"]
    max_score = eval_result["max_score"]

    status_color = {
        "Accepted": "🟢",
        "Wrong Answer": "🔴",
        "Time Limit Exceeded": "⏱️",
        "Runtime Error": "💥",
        "Compilation Error": "⚠️",
    }.get(status, "⚪")

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Verdict", f"{status_color} {status}")
        with col2:
            st.metric("Total Score", f"{score} / {max_score}")
        with col3:
            st.metric("Total Execution Time", f"{eval_result['execution_time_ms']} ms")

        # If compilation error, show compiler diagnostics
        if eval_result.get("compilation_error"):
            st.error("Compilation Diagnostics:")
            st.code(eval_result["compilation_error"], language="text")

        st.markdown("#### Test Case Breakdown")
        table_rows = []
        for idx, res in enumerate(eval_result["results"], 1):
            is_hidden = bool(res.get("is_hidden"))
            res_status = res.get("status", "FAILED")
            status_icon = "✅" if res.get("passed") else "❌"

            # CRITICAL SECURITY REQUIREMENT:
            # Never reveal hidden test inputs or expected outputs to students
            if is_hidden:
                inp_display = "🔒 [Hidden for Security]"
                exp_display = "🔒 [Hidden for Security]"
                act_display = "🔒 [Output Suppressed]"
            else:
                inp_display = (res.get("input_data", "") or "").strip()
                if len(inp_display) > 60:
                    inp_display = inp_display[:57] + "..."
                exp_display = (res.get("expected_output", "") or "").strip()
                if len(exp_display) > 60:
                    exp_display = exp_display[:57] + "..."
                act_display = (res.get("actual_output", "") or "").strip()
                if len(act_display) > 60:
                    act_display = act_display[:57] + "..."

            table_rows.append({
                "Test": f"Case {idx}" + (" (🔒 Hidden)" if is_hidden else " (Visible)"),
                "Input": inp_display,
                "Expected": exp_display,
                "Actual": act_display,
                "Verdict": f"{status_icon} {res_status}",
                "Time (ms)": f"{res.get('execution_time_ms', 0):.1f}",
                "Points": f"{res.get('points_awarded', 0)} / {res.get('points_possible', 0)}",
            })

        st.dataframe(table_rows, use_container_width=True)
