"""Leaderboard and analytics view with Pandas metrics and Matplotlib visualizations."""

from __future__ import annotations

import io
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from database import db_handler


def render_leaderboard_view() -> None:
    st.header("🏆 Leaderboard & Grading Analytics")
    st.caption("Real-time student rankings, score distributions, and performance analytics.")

    # 1. Assignment Selector
    assignments = db_handler.get_assignments()
    ass_options = {"All Assignments (Global Leaderboard)": None}
    for a in assignments:
        ass_options[f"#{a['id']}: {a['title']}"] = a["id"]

    selected_label = st.selectbox("📌 Select Assignment Scope", list(ass_options.keys()))
    selected_ass_id = ass_options[selected_label]

    # 2. Fetch Leaderboard Data
    leaderboard = db_handler.get_leaderboard(assignment_id=selected_ass_id)
    raw_submissions = db_handler.get_all_submissions_raw(assignment_id=selected_ass_id)

    # 3. KPI Metrics
    total_subs = len(raw_submissions)
    unique_students = len(set(s["student_name"] for s in raw_submissions)) if raw_submissions else 0
    accepted_subs = sum(1 for s in raw_submissions if s["status"] == "Accepted")
    acc_rate = round((accepted_subs / total_subs * 100.0), 1) if total_subs > 0 else 0.0
    avg_score = round(sum(s["score"] for s in raw_submissions) / total_subs, 1) if total_subs > 0 else 0.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Submissions", total_subs)
    with col2:
        st.metric("Unique Students", unique_students)
    with col3:
        st.metric("Acceptance Rate", f"{acc_rate}%")
    with col4:
        st.metric("Average Score", f"{avg_score} pts")

    st.divider()

    # 4. Leaderboard Table
    st.subheader("🥇 Live Rankings")
    if not leaderboard:
        st.info("No submissions recorded yet for this view.")
    else:
        lb_display = []
        for row in leaderboard:
            rank = row["rank"]
            if rank == 1:
                rank_str = "🥇 1st"
            elif rank == 2:
                rank_str = "🥈 2nd"
            elif rank == 3:
                rank_str = "🥉 3rd"
            else:
                rank_str = f"#{rank}"

            lang_icon = "🐍 Python" if row["language"].lower() == "python" else "⚡ C++"

            lb_display.append({
                "Rank": rank_str,
                "Student": row["student_name"],
                "Assignment": row["assignment_title"],
                "Language": lang_icon,
                "Best Score": f"{row['score']} / {row['max_score']}",
                "Percentage": f"{row['percentage']}%",
                "Best Time (ms)": f"{row['execution_time_ms']:.1f} ms",
                "Verdict": row["status"],
                "Submitted At": row["submitted_at"],
            })
        st.dataframe(lb_display, use_container_width=True)

    # 5. Visual Analytics with Matplotlib & Pandas
    if raw_submissions:
        st.divider()
        st.subheader("📊 Visual Analytics & Performance Insights")

        df = pd.DataFrame(raw_submissions)

        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.markdown("##### 📈 Score Distribution")
            fig, ax = plt.subplots(figsize=(5.5, 3.2))
            _apply_dark_theme(fig, ax)
            ax.hist(df["score"], bins=10, color="#38bdf8", edgecolor="#0f172a", alpha=0.85)
            ax.set_title("Submission Score Distribution", color="#e2e8f0", fontsize=11, fontweight="bold")
            ax.set_xlabel("Score Earned", color="#94a3b8")
            ax.set_ylabel("Count", color="#94a3b8")
            ax.grid(True, linestyle="--", alpha=0.2, color="#94a3b8")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

        with col_c2:
            st.markdown("##### 🎯 Verdict Breakdown")
            status_counts = df["status"].value_counts()
            fig, ax = plt.subplots(figsize=(5.5, 3.2))
            fig.patch.set_facecolor("#0E1117")
            ax.set_facecolor("#161B22")

            status_colors = {
                "Accepted": "#22c55e",
                "Wrong Answer": "#ef4444",
                "Time Limit Exceeded": "#f59e0b",
                "Runtime Error": "#ec4899",
                "Compilation Error": "#a855f7",
            }
            colors = [status_colors.get(s, "#64748b") for s in status_counts.index]

            wedges, texts, autotexts = ax.pie(
                status_counts.values,
                labels=status_counts.index,
                autopct="%1.1f%%",
                startangle=140,
                colors=colors,
                textprops=dict(color="#e2e8f0"),
                wedgeprops=dict(width=0.45, edgecolor="#0E1117"),
            )
            for at in autotexts:
                at.set_color("#000000")
                at.set_fontweight("bold")
            ax.set_title("Submission Verdict Distribution", color="#e2e8f0", fontsize=11, fontweight="bold")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

        # 6. CSV Export
        st.divider()
        st.subheader("📥 Export Submission Records")
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📄 Download Submissions as CSV",
            data=csv_buffer.getvalue(),
            file_name="submissions_report.csv",
            mime="text/csv",
            use_container_width=True,
        )


def _apply_dark_theme(fig, ax):
    """Apply consistent dark styling to Matplotlib charts."""
    fig.patch.set_facecolor("#0E1117")
    ax.set_facecolor("#161B22")
    ax.tick_params(colors="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#334155")
