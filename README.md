# ⚡ Code & Chaos — Automated Code Testing & Grading Engine

> **A high-performance, polyglot automated code execution, testing, and grading platform built with Python 3.14, C++ (g++ 16.1.0), Streamlit, SQLite (WAL mode), Pandas, and Matplotlib.**

Developed for a college hackathon with a presentation tomorrow morning, **Code & Chaos Grader** delivers an end-to-end, locally runnable online judge system featuring instructor assignment authoring, confidential hidden test cases, strict execution timeouts, live leaderboards, and rich visual analytics.

---

## 🏛️ System Architecture

```
                      +-----------------------------------+
                      |      Streamlit Web Interface      |
                      |  (Student, Instructor, Analytics) |
                      +-----------------+-----------------+
                                        |
                 +----------------------+----------------------+
                 |                                             |
                 v                                             v
     +-----------------------+                     +-----------------------+
     |   Database Handler    |                     |   Execution Engine    |
     | (Parameterized SQL)   |                     |  (Subprocess Runner)  |
     +-----------+-----------+                     +-----------+-----------+
                 |                                             |
                 v                                             v
     +-----------------------+                     +-----------------------+
     |   SQLite Database     |                     | Python 3.14 / g++ 16  |
     | (WAL Mode, Cascades)  |                     |  Isolated Temp Dir    |
     +-----------------------+                     +-----------------------+
```

---

## ✨ Key Features

### 1. 🎓 Student Portal
- **Problem Explorer**: View active assignments with rich Markdown problem statements, input/output formats, time limits, and point values.
- **Sample Test Cases**: Inspect visible sample test cases to understand expected problem contracts.
- **Confidential Grading**: Hidden test cases test edge cases and boundary conditions. **Inputs and outputs for hidden test cases are strictly masked** from student results.
- **Polyglot Submissions**: Submit code in **Python 3.14** or **C++ (g++ 16.1.0)** via an interactive in-browser editor or direct file upload (`.py` / `.cpp`).
- **Instant Detailed Feedback**: Real-time evaluation breakdown with pass/fail badges, execution times in milliseconds, and points awarded.
- **Submission History**: Track past submissions and personal score progression.

### 2. 🛠️ Instructor Studio
- **Dynamic Assignment Authoring**: Create new programming challenges with custom time limits (0.2s - 15.0s) and dynamic point distributions.
- **Interactive Test Case Builder**: Add, edit, or remove test cases dynamically. Configure test cases as visible sample tests or confidential hidden tests.
- **Reference Solution Dry-Run**: Verify your assignment and test cases by executing a reference Python or C++ solution directly in the dashboard before publishing.
- **Submissions Audit**: Search and filter all student submissions by assignment, language, and verdict. Full inspectability of student code and unmasked execution logs.

### 3. 🏆 Leaderboard & Visual Analytics
- **Live Rankings**: Automatic student ranking by highest score, lowest execution time (tie-breaker), and earliest submission timestamp.
- **Top Podium Medals**: 🥇 1st, 🥈 2nd, and 🥉 3rd place badges.
- **KPI Metrics**: Total Submissions, Unique Students, Acceptance Rate (%), and Average Score.
- **Visual Analytics (Pandas + Matplotlib)**:
  - **Score Distribution**: Histogram of scores across all submissions.
  - **Verdict Breakdown**: Donut chart displaying Accepted, Wrong Answer, Time Limit Exceeded, Runtime Error, and Compilation Error ratios.
  - **Language Breakdown**: Bar chart comparing Python vs C++ adoption.
  - **Runtime Distribution**: Boxplot of execution times comparing Python and C++.
- **One-Click Export**: Download complete submission logs as a CSV file for grading sheets.

### 4. ⚡ Execution Engine
- **Accurate Timing**: High-precision execution benchmarking using `time.perf_counter()`.
- **Output Normalization**: White-space tolerant line-by-line comparison ignoring trailing line whitespace and platform carriage returns (`\r\n` vs `\n`).
- **Output Truncation**: Stdout and Stderr are capped at 10,000 characters to prevent memory exhaustion from runaway print statements.
- **Automated Cleanup**: Ephemeral temporary compilation folders (`tempfile.mkdtemp`) are guaranteed to be cleaned up upon completion.
- **Windows Dialog Suppression**: Windows Error Reporting dialogs and CRT abort prompts are suppressed via `SetErrorMode` and `CREATE_NO_WINDOW` flags to ensure continuous, unattended grading.

---

## 🛡️ Security Architecture & Honest Sandbox Notice

> [!WARNING]
> ### Subprocess Isolation vs. Production Sandboxes
> In this local MVP implementation, Python and C++ processes are spawned using Python's standard `subprocess.run` module with strict wall-clock timeouts.
> 
> **What this engine guarantees:**
> 1. **Time Limits**: Infinite loops (`while(true)`, infinite recursion) are forcibly terminated when the wall-clock limit expires (`subprocess.TimeoutExpired`).
> 2. **Memory/Output Safeguard**: Output streams are truncated at 10,000 characters to avoid memory exhaustion.
> 3. **File Isolation**: Each run executes in an isolated temporary directory with immediate cleanup in `finally` blocks.
> 
> **What this engine does NOT provide:**
> Subprocess timeouts alone **do not** constitute a secure OS-level sandbox against malicious actors. Subprocesses have access to system calls, filesystem reads/writes, and network sockets unless constrained by the operating system.
> 
> **Enterprise Production Sandbox Roadmap:**
> For a public web deployment, the runner should be migrated to:
> - **Containerization**: Docker/Podman with unprivileged user namespaces and `--network none`.
> - **Kernel Isolation**: Linux `seccomp-bpf` syscall filters, Google `gVisor`, or `nsjail`.
> - **Windows Environments**: Windows Job Objects with strict CPU/memory limits (`SetInformationJobObject`) and restricted token AppContainers.

---

## 🚀 Setup & Installation

### Prerequisites
- **Python**: 3.14.3 (recommended) or 3.13
- **C++ Compiler**: MinGW-w64 `g++` (16.1.0 or similar) added to system `PATH`

### 1. Clone & Enter Project Directory
```powershell
cd "d:\My Projects\CodeAndChaosGrader"
```

### 2. Activate Virtual Environment
```powershell
# Using the existing virtual environment:
.\.venv\Scripts\Activate.ps1
```

*(Or create a new one if necessary: `py -3.14 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt`)*

### 3. Run Automated Tests
Verify all 14 unit and integration tests across database operations and execution engine:
```powershell
pytest tests/ -v
```

### 4. Launch Application
```powershell
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🎤 Presentation & Demo Guide (Tomorrow Morning)

Use this **3-minute presentation script** to impress judges and instructors:

### 1. The Hook (30 seconds)
> *"Grading programming assignments manually is slow, error-prone, and frustrating for both students and instructors. Traditional competitive programming judges are complex, heavyweight, and difficult to deploy locally. We built **Code & Chaos Grader** — a lightweight, modular, automated testing engine that compiles, executes, and grades Python and C++ code with millisecond precision, instant feedback, and built-in cheating resistance."*

### 2. Student Experience Demo (60 seconds)
1. Navigate to **📝 Student Portal**.
2. Select the assignment: `Sum of Multiples (3 & 5)`.
3. Highlight that the student can see visible sample test cases, but **hidden test cases remain confidential**.
4. Enter Student Name: `Alex Rivera`.
5. Select **Python** and submit the starter template or complete solution.
6. Click **🚀 Run & Submit Code**.
7. Show the real-time verdict:
   - Point out that visible test cases show expected vs actual output.
   - Point out that hidden test cases show `🔒 [Hidden for Security]` and only display pass/fail status and points awarded.
8. Switch language to **C++**, submit a solution, and show that C++ compiles with `g++` and executes with ultra-low latency (~20ms).

### 3. Chaos & Edge Case Testing Demo (45 seconds)
1. Write an intentional infinite loop in Python:
   ```python
   while True: pass
   ```
2. Click **Run & Submit Code** -> Show the engine catches **Time Limit Exceeded** within the exact configured time limit.
3. Switch to C++ and introduce a syntax error (`invalid_code;`) -> Show the engine captures **Compilation Error** and displays compiler diagnostics cleanly.

### 4. Leaderboard & Analytics (30 seconds)
1. Navigate to **🏆 Leaderboard & Analytics**.
2. Show the live podium medals (🥇, 🥈, 🥉) and explain the tie-breaking logic (Score -> Lowest Execution Time -> Earliest Submission).
3. Walk through the Matplotlib charts:
   - **Score Distribution** histogram.
   - **Verdict Breakdown** donut chart.
   - **Language Adoption & Speed Comparison** (C++ vs Python).
4. Click **📄 Download Submissions as CSV** to show export capabilities.

### 5. Technical Questions & Sandboxing (15 seconds)
- When asked about security: Transparently explain the difference between our subprocess timeouts and a containerized production sandbox (refer to the **🛡️ Engine & Sandbox Architecture** tab in the Instructor Dashboard).

---

## 📁 Repository Structure

```
CodeAndChaosGrader/
├── .gitignore               # Git ignore rules for venv, DB, and binaries
├── app.py                   # Main Streamlit application and navigation
├── requirements.txt         # Project dependencies
├── README.md                # Documentation and presentation guide
├── database/
│   ├── __init__.py
│   ├── schema.sql           # SQLite relational schema
│   └── db_handler.py        # Parameterized queries, CRUD, and data masking
├── engine/
│   ├── __init__.py
│   └── runner.py            # Subprocess runner, g++ compiler, timeouts, normalization
├── ui/
│   ├── __init__.py
│   ├── instructor_view.py   # Assignment creator, dry-run, submission inspector
│   ├── student_view.py      # Code editor, submission runner, masked test display
│   └── leaderboard_view.py  # Rankings, KPI metrics, Pandas & Matplotlib charts
├── tests/
│   ├── test_database.py     # Database unit tests & privacy checks
│   └── test_runner.py       # Python & C++ execution, TLE, RTE, CE tests
└── workspace/
    └── .gitkeep             # Preserved workspace folder for sandbox artifacts
```

---

## 👥 Authors
Built for the Hackathon Coding Challenge.
Developed with Python 3.14, g++ 16.1.0, and Streamlit.
