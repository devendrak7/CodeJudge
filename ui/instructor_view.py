"""Instructor dashboard for creating assignments, managing test cases, and auditing submissions."""

from __future__ import annotations

import streamlit as st
from database import db_handler
from engine import runner


def render_instructor_view() -> None:
    st.header("🛠️ Instructor Dashboard")
    st.caption("Create assignments, configure test cases, inspect student submissions, and verify grading integrity.")

    tabs = st.tabs([
        "➕ Create Assignment",
        "📂 Manage Assignments",
        "🔍 Inspect Submissions",
        "🛡️ Engine & Sandbox Architecture",
    ])

    with tabs[0]:
        _render_create_assignment_tab()

    with tabs[1]:
        _render_manage_assignments_tab()

    with tabs[2]:
        _render_inspect_submissions_tab()

    with tabs[3]:
        _render_security_architecture_tab()


def _render_create_assignment_tab() -> None:
    st.subheader("Create a New Coding Assignment")

    col_title, col_limit = st.columns([3, 1])
    with col_title:
        title = st.text_input("Assignment Title", placeholder="e.g. Invert Binary Tree / Two Sum")
    with col_limit:
        time_limit = st.number_input("Time Limit (sec / test)", min_value=0.2, max_value=15.0, value=2.0, step=0.1)

    description = st.text_area(
        "Assignment Description (Markdown supported)",
        value="### Problem Statement\nDescribe the task clearly.\n\n#### Input Format\n...\n\n#### Output Format\n...",
        height=180,
    )

    st.markdown("#### Test Cases Builder")
    st.caption("Add both visible (sample) test cases and hidden test cases for grading.")

    if "test_case_list" not in st.session_state:
        st.session_state["test_case_list"] = [
            {"input_data": "5\n", "expected_output": "10", "is_hidden": False, "points": 25},
            {"input_data": "100\n", "expected_output": "200", "is_hidden": True, "points": 75},
        ]

    # Test cases list display
    for idx, tc in enumerate(st.session_state["test_case_list"]):
        with st.container(border=True):
            col_header, col_hidden, col_pts = st.columns([2, 1, 1])
            with col_header:
                st.markdown(f"**Test Case #{idx + 1}**")
            with col_hidden:
                tc["is_hidden"] = st.checkbox("🔒 Hidden Test", value=tc.get("is_hidden", False), key=f"tc_hidden_{idx}")
            with col_pts:
                tc["points"] = st.number_input("Points", min_value=1, max_value=500, value=int(tc.get("points", 20)), key=f"tc_pts_{idx}")

            col_in, col_out = st.columns(2)
            with col_in:
                tc["input_data"] = st.text_area("Input (stdin)", value=tc.get("input_data", ""), height=80, key=f"tc_in_{idx}")
            with col_out:
                tc["expected_output"] = st.text_area("Expected Output (stdout)", value=tc.get("expected_output", ""), height=80, key=f"tc_out_{idx}")

    col_add, col_rem, _ = st.columns([1, 1, 2])
    with col_add:
        if st.button("➕ Add Test Case"):
            st.session_state["test_case_list"].append(
                {"input_data": "", "expected_output": "", "is_hidden": True, "points": 25}
            )
            st.rerun()
    with col_rem:
        if len(st.session_state["test_case_list"]) > 1:
            if st.button("➖ Remove Last"):
                st.session_state["test_case_list"].pop()
                st.rerun()

    # Dry-Run / Reference Solution Verifier
    with st.expander("🧪 Test Case Dry Run (Verify with Reference Solution)"):
        st.caption("Verify your test cases by running your reference solution before publishing.")
        dry_lang = st.selectbox("Dry-Run Language", ["Python", "C++"], key="dry_lang")
        dry_code = st.text_area("Reference Code", height=150, key="dry_code")
        if st.button("Run Reference Verification"):
            if dry_code.strip():
                dry_res = runner.evaluate_submission(
                    language=dry_lang.lower(),
                    code=dry_code,
                    test_cases=st.session_state["test_case_list"],
                    time_limit_sec=time_limit,
                )
                if dry_res["status"] == "Accepted":
                    st.success(f"All {len(st.session_state['test_case_list'])} test cases passed with reference code!")
                else:
                    st.error(f"Dry run result: {dry_res['status']} ({dry_res['score']}/{dry_res['max_score']} pts)")
                    if dry_res.get("compilation_error"):
                        st.code(dry_res["compilation_error"])

    st.divider()
    if st.button("💾 Publish Assignment", type="primary", use_container_width=True):
        if not title.strip():
            st.error("Please enter an assignment title.")
            return

        formatted_cases = []
        for tc in st.session_state["test_case_list"]:
            if not tc["expected_output"].strip():
                st.error("All test cases must have non-empty expected outputs.")
                return
            formatted_cases.append({
                "input_data": tc["input_data"],
                "expected_output": tc["expected_output"],
                "is_hidden": 1 if tc["is_hidden"] else 0,
                "points": tc["points"],
            })

        new_id = db_handler.create_assignment(
            title=title,
            description=description,
            time_limit=time_limit,
            test_cases=formatted_cases,
        )
        st.success(f"Assignment #{new_id} '{title}' created successfully!")
        st.rerun()


def _render_manage_assignments_tab() -> None:
    st.subheader("Existing Assignments")
    assignments = db_handler.get_assignments()

    if not assignments:
        st.info("No assignments created yet.")
        return

    for a in assignments:
        with st.expander(f"Assignment #{a['id']}: {a['title']} ({a['total_tests']} tests, {a['max_points']} pts, {a['time_limit']}s limit)"):
            st.markdown(a["description"])
            tcs = db_handler.get_test_cases(a["id"], include_hidden=True)
            tc_data = []
            for idx, tc in enumerate(tcs, 1):
                tc_data.append({
                    "Test #": idx,
                    "Type": "🔒 Hidden" if tc["is_hidden"] else "👁️ Visible",
                    "Points": tc["points"],
                    "Input (stdin)": repr(tc["input_data"])[1:-1],
                    "Expected (stdout)": repr(tc["expected_output"])[1:-1],
                })
            st.table(tc_data)

            col_del, _ = st.columns([1, 4])
            with col_del:
                if st.button(f"🗑️ Delete #{a['id']}", key=f"del_{a['id']}", type="secondary"):
                    db_handler.delete_assignment(a["id"])
                    st.warning(f"Deleted assignment #{a['id']}.")
                    st.rerun()


def _render_inspect_submissions_tab() -> None:
    st.subheader("Student Submissions Audit")

    assignments = db_handler.get_assignments()
    ass_options = {"All Assignments": None}
    for a in assignments:
        ass_options[f"#{a['id']}: {a['title']}"] = a["id"]

    col1, col2 = st.columns(2)
    with col1:
        sel_label = st.selectbox("Filter by Assignment", list(ass_options.keys()))
        selected_ass_id = ass_options[sel_label]
    with col2:
        student_filter = st.text_input("Filter by Student Name", placeholder="Leave blank for all")

    submissions = db_handler.get_submissions(
        assignment_id=selected_ass_id,
        student_name=student_filter if student_filter.strip() else None,
        limit=100,
    )

    if not submissions:
        st.info("No submissions matching the filters.")
        return

    st.write(f"Showing **{len(submissions)}** submission(s):")

    sub_display = []
    for s in submissions:
        sub_display.append({
            "Sub ID": s["id"],
            "Student": s["student_name"],
            "Assignment": s["assignment_title"],
            "Lang": s["language"].upper(),
            "Score": f"{s['score']} / {s['max_score']}",
            "Verdict": s["status"],
            "Time": f"{s['execution_time_ms']:.1f} ms",
            "Submitted": s["submitted_at"],
        })
    st.dataframe(sub_display, use_container_width=True)

    # Detailed Submission Inspector
    sub_ids = [s["id"] for s in submissions]
    inspect_id = st.selectbox("Select Submission ID to Inspect Code & Test Logs", sub_ids)

    if inspect_id:
        sub_details = db_handler.get_submission_details(inspect_id, is_instructor=True)
        if sub_details:
            with st.container(border=True):
                st.markdown(f"### Submission Details: #{sub_details['id']} — {sub_details['student_name']}")
                st.markdown(
                    f"**Assignment**: {sub_details['assignment_title']} | "
                    f"**Language**: `{sub_details['language'].upper()}` | "
                    f"**Verdict**: `{sub_details['status']}` | "
                    f"**Score**: `{sub_details['score']} / {sub_details['max_score']}` | "
                    f"**Time**: `{sub_details['execution_time_ms']:.1f} ms`"
                )

                st.markdown("#### Submitted Code")
                st.code(sub_details["code"], language=sub_details["language"])

                st.markdown("#### Detailed Test Results (Instructor View: Raw Hidden Data)")
                inst_test_rows = []
                for idx, r in enumerate(sub_details["results"], 1):
                    inst_test_rows.append({
                        "Test": f"#{idx} " + ("(Hidden)" if r["is_hidden"] else "(Visible)"),
                        "Input": repr(r["input_data"])[1:-1],
                        "Expected": repr(r["expected_output"])[1:-1],
                        "Actual": repr(r["actual_output"])[1:-1],
                        "Status": r["status"],
                        "Time (ms)": f"{r['execution_time_ms']:.1f}",
                        "Points": f"{r['points_awarded']} / {r['points_possible']}",
                        "Error": r["error_message"] if r["error_message"] else "-",
                    })
                st.dataframe(inst_test_rows, use_container_width=True)


def _render_security_architecture_tab() -> None:
    st.subheader("🛡️ Execution Engine & Security Architecture")

    st.markdown("""
    ### Honest Security Notice: Subprocess vs. Container Sandbox

    > [!WARNING]
    > **Local Subprocess Sandboxing Boundary**:
    > In this MVP engine, Python and C++ processes are spawned via Python's standard `subprocess.run` module with strict wall-clock timeouts and pipe buffering.
    > While execution timeouts safeguard against infinite loops, algorithmic time-limit failures, and runaway output streams, **subprocess timeouts alone DO NOT constitute a fully isolated operating system sandbox**.

    #### What Subprocess Guarantees Provide:
    - **Wall-Clock Timeouts**: Any program entering an infinite loop (`while(true)`, deep recursion) is forcibly terminated after the configured assignment limit (e.g. 2.0s).
    - **Output Truncation**: Stdout and Stderr are truncated at 10,000 characters to prevent memory exhaustion from infinite print loops.
    - **Resource Isolation by File**: Each submission compiles and runs in an ephemeral temporary directory (`tempfile.mkdtemp`) with guaranteed cleanup upon termination.
    - **Windows Dialog Suppression**: Windows Error Reporting and CRT abort dialogs are disabled via `SetErrorMode` and `CREATE_NO_WINDOW` flags to ensure automated grading runs unattended without modal blocking.

    #### Enterprise Production Roadmap:
    To safely run arbitrary untrusted user code in a public web deployment, the following sandboxing layers should be introduced:
    1. **Container Isolation**: Docker/Podman with unprivileged user namespaces and read-only root filesystems.
    2. **Kernel Sandboxing**: Linux `seccomp-bpf` syscall filtering or Google `gVisor` / `nsjail`.
    3. **Windows Sandbox / AppContainer**: Windows Job Objects with memory limits (`JOB_OBJECT_LIMIT_JOB_MEMORY`) and restricted tokens.
    4. **Network Namespace Disconnection**: Completely disabling network adapters (`--network none`) for execution workers.
    """)
