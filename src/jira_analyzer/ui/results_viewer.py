"""Results Viewer for browsing SQLite analysis results."""

from typing import Any, Dict, List, Callable

import pandas as pd
import streamlit as st

from jira_analyzer.storage import SqliteAnalysisResultRepository


class ResultsViewer:
    """Master-detail results viewer for SQLite analysis results."""

    def __init__(
        self,
        repository: SqliteAnalysisResultRepository,
        translate_func: Callable[[str, Any], str],
    ) -> None:
        """Initialize the results viewer.

        Args:
            repository: SQLite repository for accessing analysis results.
            translate_func: Translation function for UI text.
        """
        self.repository = repository
        self.t = translate_func

    def render(self) -> None:
        """Render the master-detail results viewer interface."""
        # Initialize session state properly
        if "all_results" not in st.session_state:
            st.session_state.all_results = self._load_results()

        # Initialize selected result ID if not set
        if "selected_result_id" not in st.session_state:
            st.session_state.selected_result_id = None

        results = st.session_state.all_results

        if not results:
            st.info(self.t("no_analysis_results"))
            return

        # Default to first result if no result is selected
        if st.session_state.selected_result_id is None:
            st.session_state.selected_result_id = results[0].get("task_id")

        # Create two-column layout (master-detail)
        col1, col2 = st.columns([1, 2])

        with col1:
            self._render_results_list(results)

        with col2:
            if st.session_state.selected_result_id:
                self._render_result_details(st.session_state.selected_result_id)

    def _load_results(self) -> List[Dict[str, Any]]:
        """Load all completed analysis results from repository.

        Returns:
            List of result dictionaries.
        """
        try:
            results = self.repository.get_all_results()
            
            # Load analysis runs and criteria for run-based filtering
            analysis_runs = self.repository.get_analysis_runs()
            st.session_state.analysis_runs = analysis_runs
            
            # Validate results structure to prevent downstream errors
            validated_results = []
            for result in results:
                try:
                    # Ensure required fields exist with defensive defaults
                    validated_result = {
                        "task_id": result.get("task_id", "Unknown"),
                        "title": result.get("title") or "No title",
                        "state": result.get("state", "UNKNOWN"),
                        "description": result.get("description", ""),
                        "assignee": result.get("assignee"),
                        "created_at": result.get("created_at"),
                        "analyzed_at": result.get("analyzed_at"),
                        "analysis": result.get("analysis", {}),
                        "run_id": result.get("run_id"),
                    }
                    validated_results.append(validated_result)
                except Exception as validation_error:
                    # Skip malformed results but continue processing others
                    st.warning(f"Skipping malformed result: {validation_error}")
                    continue
            
            return validated_results
            
        except KeyError as key_error:
            st.error(self.t("results_loading_error", 
                          error=f"Missing required field: {key_error}"))
            return []
        except ValueError as value_error:
            st.error(self.t("results_loading_error", 
                          error=f"Invalid data format: {value_error}"))
            return []
        except Exception as error:
            st.error(self.t("results_loading_error", error=str(error)))
            return []

    def _render_results_list(self, results: List[Dict[str, Any]]) -> None:
        """Render the left panel with list of results.

        Args:
            results: List of analysis results to display.
        """
        st.subheader(self.t("results_list"))

        # Analysis run filter
        analysis_runs = st.session_state.get("analysis_runs", [])
        if analysis_runs:
            run_options = [("All Runs", None)] + [(r.get("run_name", f"Run {r['run_id']}"), r['run_id']) for r in analysis_runs]
            run_filter = st.selectbox(
                "Analysis Run",
                options=[name for name, _ in run_options],
                index=0,
                key="run_filter",
            )
            selected_run_id = [run_id for name, run_id in run_options if name == run_filter][0]
        else:
            selected_run_id = None

        # Search and filter controls
        search_text = st.text_input(
            self.t("search_results"),
            key="results_search",
        )

        # Filtering options
        filter_container = st.container()
        with filter_container:
            status_filter = st.selectbox(
                self.t("filter_by_status"),
                options=["All", "Completed", "Failed"],
                key="status_filter",
            )

        st.divider()

        # Apply filters
        filtered_results = self._filter_results(results, search_text, status_filter, selected_run_id)

        if not filtered_results:
            st.warning(self.t("no_matching_results"))
            return

        # Display results as selectable items (not spoilers/expanders)
        for result in filtered_results:
            task_id = result.get("task_id", "Unknown")
            title = result.get("title", "No title")

            # Create clickable card for each result
            is_selected = task_id == st.session_state.selected_result_id
            card_color = "primary" if is_selected else "secondary"
            
            # Use button to select the result (simple direct interaction)
            if st.button(
                f"{self.t('issue_title', id=task_id, title=title)}",
                key=f"select_{task_id}",
                type=card_color,
            ):
                st.session_state.selected_result_id = task_id
                st.rerun()

    def _filter_results(
        self,
        results: List[Dict[str, Any]],
        search_text: str,
        status_filter: str,
        selected_run_id: int | None = None,
    ) -> List[Dict[str, Any]]:
        """Filter results based on search text and filters.

        Args:
            results: List of all results.
            search_text: Text to search for.
            status_filter: Status filter to apply.
            selected_run_id: Analysis run ID to filter by.

        Returns:
            Filtered list of results.
        """
        filtered = results

        # Analysis run filter
        if selected_run_id is not None:
            filtered = [r for r in filtered if r.get("run_id") == selected_run_id]

        # Status filter - map UI-friendly values to database state values
        # Defensive filtering: handle None states and use exact matching
        if status_filter == "Completed":
            filtered = [r for r in filtered if r.get("state") == "COMPLETED"]
        elif status_filter == "Failed":
            filtered = [r for r in filtered if r.get("state") == "FAILED"]
        # "All" means no status filter applied

        # Score filtering is disabled as criteria may have different scoring systems

        # Text search
        if search_text:
            search_lower = search_text.lower()
            filtered = [
                r for r in filtered
                if search_lower in r.get("task_id", "").lower()
                or search_lower in r.get("title", "").lower()
                or search_lower in r.get("description", "").lower()
            ]

        return filtered

    def _render_result_details(self, task_id: str) -> None:
        """Render the right panel with detailed result information.

        Args:
            task_id: ID of the result to display details for.
        """
        st.subheader(self.t("result_details"))

        # Get result from repository
        result = self.repository.get_result(task_id)

        if not result:
            st.error(self.t("result_not_found", id=task_id))
            return

        # Display result information
        self._display_result_summary(result)

        if result.get("state") == "COMPLETED":
            self._display_analysis_result(result)

    def _display_result_summary(self, result: Dict[str, Any]) -> None:
        """Display summary information about the result.

        Args:
            result: Result dictionary.
        """
        st.header("📋 Brief Analysis Details")

        # Manual table implementation for cleaner formatting
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Task ID", result.get("task_id", "N/A"), label_visibility="visible")
            st.metric("Status", result.get("state", "N/A"), label_visibility="visible")
            st.metric("Analysis Date", self._format_date(result.get("analyzed_at")), label_visibility="visible")
        with col2:
            st.metric("Assignee", result.get("assignee", "N/A"), label_visibility="visible")
            st.metric("Creation Date", self._format_date(result.get("created_at")), label_visibility="visible")

        # Task Description
        st.subheader("📝 Task Description")
        description = result.get("description", "")
        if description:
            st.text_area("Description", value=description, disabled=True, height=200, label_visibility="collapsed")
        else:
            st.info("No description available")

    def _format_date(self, date_str: str | None) -> str:
        """Format date string for display.
        
        Args:
            date_str: Date string to format.
            
        Returns:
            Formatted date string or N/A
        """
        if not date_str:
            return "N/A"
        try:
            # Try to parse ISO format and format nicely
            from datetime import datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00') if 'Z' in date_str else date_str)
            return dt.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            return str(date_str)

    def _display_analysis_run_configuration_collapsed(self, run_id: int) -> None:
        """Display analysis run configuration information in a collapsed section.

        Args:
            run_id: Analysis run ID.
        """
        try:
            analysis_run = self.repository.get_analysis_run(run_id)
            if analysis_run:
                with st.expander("⚙️ Analysis Configuration (Click to expand)", expanded=False):
                    # Run metadata
                    metadata_col1, metadata_col2 = st.columns(2)
                    with metadata_col1:
                        st.write(f"**Run Name:** {analysis_run.get('run_name', f'Run {run_id}')}")
                        st.write(f"**Created:** {self._format_date(analysis_run.get('created_at'))}")
                    with metadata_col2:
                        include_overall = analysis_run.get("include_overall_conclusion", True)
                        st.write(f"**Include Overall Conclusion:** {'Yes' if include_overall else 'No'}")
                        split_by_criterion = analysis_run.get("split_by_criterion", False)
                        st.write(f"**Split By Criterion:** {'Yes' if split_by_criterion else 'No'}")
                    
                    st.divider()
                    
                    # Display run configuration details
                    if analysis_run.get("system_prompt"):
                        st.subheader("🤖 System Prompt")
                        st.text_area("System Prompt", value=analysis_run.get("system_prompt", ""), height=80, disabled=True, label_visibility="collapsed")
                    
                    if analysis_run.get("general_prompt"):
                        st.subheader("📋 General Prompt")
                        st.text_area("General Prompt", value=analysis_run.get("general_prompt", ""), height=80, disabled=True, label_visibility="collapsed")
                    
                    # Display criteria definitions summary
                    criteria = self.repository.get_criteria(run_id)
                    if criteria:
                        st.subheader(f"📏 Criteria Definitions ({len(criteria)} criteria)")
                        with st.expander("📋 View All Criteria Definitions", expanded=False):
                            for i, criterion in enumerate(criteria, 1):
                                st.markdown(f"**{i}. {criterion.get('title', 'Unknown Criterion')}**")
                                if criterion.get('description'):
                                    st.markdown(f"*{criterion.get('description')}*")
                                st.write(f"**Scoring System:** {criterion.get('scoring_system', 'percent')}")
                                if criterion.get('include_review'):
                                    st.write("*Includes review*")
                                st.divider()
                            
        except Exception as e:
            st.warning(f"Could not load analysis configuration: {e}")

    def _display_analysis_result(self, result: Dict[str, Any]) -> None:
        """Display detailed analysis results.

        Args:
            result: Result dictionary with analysis data.
        """
        st.divider()
        st.header("📊 Analysis Results")

        analysis = result.get("analysis", {})
        if not analysis:
            st.warning(self.t("no_analysis_data"))
            return

        # Overall conclusion
        overall_conclusion = analysis.get("overall_conclusion")
        if overall_conclusion:
            st.subheader("🎯 Overall Conclusion")
            st.markdown(overall_conclusion)

        # Criteria scores - Table formatted display
        criteria_scores = analysis.get("criteria_scores", {})
        criteria_full = analysis.get("criteria", {})
        if criteria_scores:
            st.subheader("📈 Criteria Breakdown")
            self._display_criteria_scores_table(result, criteria_scores, criteria_full)
        else:
            # Legacy format: check for 'criteria' field
            criteria = analysis.get("criteria", {})
            if criteria:
                st.subheader("📈 Criteria Breakdown")
                self._display_legacy_criteria_table(criteria)
                
        # Analysis Run Configuration (under cut)
        run_id = result.get("run_id")
        if run_id:
            self._display_analysis_run_configuration_collapsed(run_id)

    def _get_criteria_definitions(self, run_id: int | None) -> Dict[str, Dict[str, Any]]:
        """Get criteria definitions for an analysis run.

        Args:
            run_id: Analysis run ID.

        Returns:
            Dictionary of criteria definitions keyed by criterion_key.
        """
        if not run_id:
            return {}
        
        try:
            criteria = self.repository.get_criteria(run_id)
            return {c.get("criterion_key", c.get("title")): c for c in criteria}
        except Exception:
            return {}

    def _display_criteria_scores_table(self, result: Dict[str, Any], criteria_scores: Dict[str, Any], criteria: Dict[str, Any] = None) -> None:
        """Display criteria scores in individual expandable sections.

        Each criterion is shown in its own expandable section with the criterion name
        and score in the title. Inside each section, the score system, fix recommendations,
        and review text are displayed.

        Args:
            result: Result dictionary containing run_id.
            criteria_scores: Dictionary of criteria with scores.
            criteria: Dictionary of full criteria with recommendations and details.
        """
        if criteria is None:
            criteria = {}
        
        run_id = result.get("run_id")
        criteria_definitions = self._get_criteria_definitions(run_id) if run_id else {}
        
        # Display each criterion in its own expandable section
        for criterion_name, criterion_score in criteria_scores.items():
            # Get criteria definition for display title
            criterion_def = criteria_definitions.get(criterion_name)
            # Get full criteria data
            criterion_data = criteria.get(criterion_name, {})
            if not isinstance(criterion_data, dict):
                criterion_data = {}
                    
            display_title = criterion_def.get("title") if criterion_def else criterion_data.get("title", criterion_name)
            
            # Get scoring system - prioritize from full criteria data, then from definitions
            if criterion_data.get("scoring_system"):
                scoring_system = criterion_data.get("scoring_system")
            elif criterion_def and criterion_def.get("scoring_system"):
                scoring_system = criterion_def.get("scoring_system")
            else:
                scoring_system = "N/A"
            
            # Get score
            if isinstance(criterion_score, dict):
                score = criterion_score.get("score")
                review = criterion_score.get("review", criterion_data.get("review", ""))
            else:
                score = criterion_score if isinstance(criterion_score, (int, float)) else None
                review = criterion_data.get("review", "")
            
            # Format score display based on scoring system
            if score is not None:
                if scoring_system == "percent":
                    score_display = f"{score:.0f}%" if float(score).is_integer() else f"{score:.1f}%"
                elif scoring_system == "five":
                    score_display = f"{score:.0f}/5" if float(score).is_integer() else f"{score:.1f}/5"
                elif scoring_system == "binary":
                    score_display = f"{score:.0f}" if float(score).is_integer() else f"{score:.1f}"
                else:
                    # Default fallback
                    score_display = f"{score:.0f}/10" if float(score).is_integer() else f"{score:.1f}/10"
            else:
                score_display = "N/A"
            
            # Get fix recommendations
            recommendations = criterion_data.get("recommendations", [])
            
            # Create expandable section with criterion name and score in title
            expander_title = f"📊 {display_title} - Score: {score_display}"
            
            with st.expander(expander_title, expanded=False):
                # Display score system
                st.markdown(f"**📈 Score System:** {scoring_system}")
                
                # Display fix recommendations
                if recommendations and isinstance(recommendations, list):
                    st.markdown("**🔧 Fix Recommendations:**")
                    for i, rec in enumerate(recommendations, 1):
                        st.markdown(f"  {i}. {rec}")
                
                # Display review
                if review:
                    st.markdown("**📝 Review:**")
                    st.markdown(review)
    
    def _display_legacy_criteria_table(self, criteria: Dict[str, Any]) -> None:
        """Display criteria in legacy format using table.

        Args:
            criteria: Dictionary of criteria with detailed information.
        """
        table_data = []
        for criterion_name, criterion_data in criteria.items():
            if isinstance(criterion_data, dict):
                score = criterion_data.get("score")
                review = criterion_data.get("review", "")
                diagnosis = criterion_data.get("diagnosis", "")
                
                score_display = f"{score:.1f}/10" if score is not None else "N/A"
                
                table_data.append({
                    "Criterion Name": criterion_name,
                    "Score": score_display,
                    "Score System": "N/A",
                    "Review": review[:100] + "..." if len(str(review)) > 100 else review,
                    "Diagnosis": diagnosis[:100] + "..." if len(str(diagnosis)) > 100 else diagnosis,
                })
        
        if table_data:
            df = pd.DataFrame(table_data)
            st.dataframe(df, width="stretch", hide_index=True)
            
            # Show detailed reviews in expandable sections
            for criterion_name, criterion_data in criteria.items():
                if isinstance(criterion_data, dict):
                    review = criterion_data.get("review", "")
                    diagnosis = criterion_data.get("diagnosis", "")
                    if review or diagnosis:
                        with st.expander(f"📝 Details for: {criterion_name}", expanded=False):
                            if diagnosis:
                                st.markdown(f"**Diagnosis:** {diagnosis}")
                            if review:
                                st.markdown(f"**Review:** {review}")
