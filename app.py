"""Code & Chaos — Automated Code Testing & Grading Engine.

Main application entry point orchestrating the Student Portal, Instructor Dashboard,
and Leaderboard & Analytics modules.
"""

from __future__ import annotations

import streamlit as st
from database import db_handler
from ui.student_view import render_student_view
from ui.instructor_view import render_instructor_view
from ui.leaderboard_view import render_leaderboard_view


def apply_custom_theme() -> None:
    """Apply high-contrast, polished styling suitable for hackathon presentations."""
    st.markdown(
        """
        <style>
        /* Main branding header */
        .brand-header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155;
            padding: 1.25rem 1.75rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        }
        .brand-title {
            color: #38bdf8;
            font-size: 1.85rem;
            font-weight: 800;
            margin: 0;
            letter-spacing: -0.025em;
        }
        .brand-subtitle {
            color: #94a3b8;
            font-size: 0.95rem;
            margin-top: 0.25rem;
            margin-bottom: 0;
        }
        .telemetry-pill {
            display: inline-block;
            background-color: #1e293b;
            color: #38bdf8;
            font-size: 0.78rem;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            border: 1px solid #334155;
            margin-right: 0.4rem;
            margin-top: 0.4rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Code & Chaos Grader",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize SQLite database (creates tables & seeds starter problems if first run)
    db_handler.init_db(seed_samples=True)

    apply_custom_theme()

    # App Header Banner
    st.markdown(
        """
        <div class="brand-header">
            <h1 class="brand-title">⚡ CODE & CHAOS GRADER</h1>
            <p class="brand-subtitle">High-Performance Automated Testing & Grading Engine for Python & C++</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar Navigation & System Telemetry
    with st.sidebar:
        st.image("https://api.iconify.design/lucide:cpu.svg?color=%2338bdf8", width=48)
        st.markdown("### 🧭 Navigation")
        selected_view = st.radio(
            "Select Portal",
            [
                "📝 Student Portal",
                "🛠️ Instructor Dashboard",
                "🏆 Leaderboard & Analytics",
            ],
            index=0,
        )

        st.divider()
        st.markdown("### ⚙️ Engine Telemetry")
        st.markdown(
            """
            <span class="telemetry-pill">🐍 Python 3.14.3</span>
            <span class="telemetry-pill">⚡ g++ 16.1.0 (MSYS2)</span>
            <span class="telemetry-pill">🗄️ SQLite WAL Mode</span>
            <span class="telemetry-pill">⏱️ Subprocess Engine</span>
            """,
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown("### 🎯 Presentation Utilities")
        st.caption("Use during live presentations to quickly restore clean demo assignments.")
        if st.button("🔄 Reload Sample Assignments", use_container_width=True):
            db_handler.init_db(seed_samples=True)
            st.toast("Starter assignments refreshed!", icon="✅")
            st.rerun()

    # Route to selected view
    if selected_view == "📝 Student Portal":
        render_student_view()
    elif selected_view == "🛠️ Instructor Dashboard":
        render_instructor_view()
    elif selected_view == "🏆 Leaderboard & Analytics":
        render_leaderboard_view()


if __name__ == "__main__":
    main()
