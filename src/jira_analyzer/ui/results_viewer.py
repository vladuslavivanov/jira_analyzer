"""Streamlit results viewer component.

This component provides a master-detail layout for viewing stored
analysis results from a SQLite database.
"""

import json
import streamlit as st
from sqlite3 import Connection
from typing import List, Dict, Any


class ResultsViewer:
    """Display stored analysis results in master-detail layout.

    Student implementation: Simple Streamlit UI components with state management.
    """

    def __init__(self, db_connection: Connection):
        """Initialize with database connection.

        Args:
            db_connection: SQLite connection to results database
        """
        self._db = db_connection

    def render(self):
        """Render the results viewer page.

        This method creates a master-detail layout with:
        - Master list: selectbox for task selection
        - Detail panel: columns for task metadata and analysis results
        """
        st.title("Analysis Results")

        # Fetch results from database
        results = self._fetch_all_results()

        if not results:
            st.info("No analysis results found. Run analysis first.")
            return

        # Master list: task selection
        self._render_master_list(results)

        # Detail panel: task details and analysis
        self._render_detail_panel(results)

    def _fetch_all_results(self) -> List[Dict[str, Any]]:
        """Fetch all results from database.

        Returns:
            List of result dictionaries with all columns

        Note:
            Simple SELECT query - no complex filtering or pagination.
        """
        cursor = self._db.cursor()
        cursor.execute("""
            SELECT
                task_id, title, status, assignee,
                total_score, summary, analyzed_at
            FROM analysis_results
            WHERE state = 'COMPLETED'
            ORDER BY analyzed_at DESC
        """)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _render_master_list(self, results: List[Dict[str, Any]]) -> None:
        """Render master list of tasks.

        Uses st.selectbox for task selection with session state.

        Args:
            results: List of result dictionaries
        """
        # Prepare display options: "PROJ-001 - Fix bug - Score: 8"
        options = [
            f"{r['task_id']} - {r['title']} - Score: {r['total_score']}"
            for r in results
        ]

        # Selectbox for task selection
        selected = st.selectbox(
            "Select Task",
            range(len(results)),
            format_func=lambda i: options[i],
            key="results_viewer_selected"
        )

        # Store in session state
        if "selected_result_index" not in st.session_state or st.session_state.selected_result_index != selected:
            st.session_state.selected_result_index = selected
            st.session_state.selected_result = results[selected]
        elif "selected_result" not in st.session_state:
            st.session_state.selected_result = results[0]

    def _render_detail_panel(self, results: List[Dict[str, Any]]) -> None:
        """Render detail panel for selected task.

        Uses columns for layout: task metadata left, analysis results right.

        Args:
            results: List of result dictionaries
        """
        result = st.session_state.get("selected_result")

        if not result:
            return

        # Create columns for layout (2 equal columns)
        col1, col2 = st.columns([1, 1])

        # Left column: Task metadata
        with col1:
            st.subheader("Task Information")
            st.write(f"**ID:** {result['task_id']}")
            st.write(f"**Title:** {result['title']}")
            st.write(f"**Status:** {result['status']}")
            st.write(f"**Assignee:** {result['assignee']}")
            st.write(f"**Analyzed At:** {result['analyzed_at']}")

        # Right column: Analysis results
        with col2:
            st.subheader("Quality Analysis")
            score = result['total_score']
            
            # Simple color coding based on score
            if 1 <= score <= 4:
                color = "red"
            elif 5 <= score <= 7:
                color = "orange"
            elif 8 <= score <= 10:
                color = "green"
            else:
                color = "gray"

            st.markdown(
                f"### Quality Score: <span style='color:{color}'>{score}/10</span>",
                unsafe_allow_html=True
            )

            st.write("**Summary:**")
            st.write(result['summary'])

        # Download option
        st.download_button(
            label="Download Result (JSON)",
            data=json.dumps(result, indent=2),
            file_name=f"{result['task_id']}_analysis.json",
            mime="application/json"
        )
