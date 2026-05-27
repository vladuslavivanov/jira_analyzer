"""Results Viewer for browsing SQLite analysis results."""

from typing import Any, Dict, List, Callable

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
        st.title(self.t("results_viewer_title"))
        st.caption(self.t("results_viewer_caption"))

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
                        "total_score": result.get("total_score"),
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
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                status_filter = st.selectbox(
                    self.t("filter_by_status"),
                    options=["All", "Completed", "Failed"],
                    key="status_filter",
                )
            with filter_col2:
                min_score = st.number_input(
                    self.t("minimum_score"),
                    min_value=0.0,
                    max_value=10.0,
                    value=0.0,
                    step=0.5,
                    key="min_score_filter",
                )

        st.divider()

        # Apply filters
        filtered_results = self._filter_results(results, search_text, status_filter, min_score, selected_run_id)

        if not filtered_results:
            st.warning(self.t("no_matching_results"))
            return

        # Display results as selectable items (not spoilers/expanders)
        for result in filtered_results:
            task_id = result.get("task_id", "Unknown")
            title = result.get("title", "No title")
            score = result.get("total_score")
            score_display = f"{score:.1f}/10" if score is not None else "N/A"  

            # Create clickable card for each result
            is_selected = task_id == st.session_state.selected_result_id
            card_color = "primary" if is_selected else "secondary"
            
            # Use button to select the result (simple direct interaction)
            if st.button(
                f"{self.t('issue_title', id=task_id, title=title)} | {score_display}",
                key=f"select_{task_id}",
                use_container_width=True,
                type=card_color,
            ):
                st.session_state.selected_result_id = task_id
                st.rerun()

    def _filter_results(
        self,
        results: List[Dict[str, Any]],
        search_text: str,
        status_filter: str,
        min_score: float,
        selected_run_id: int | None = None,
    ) -> List[Dict[str, Any]]:
        """Filter results based on search text and filters.

        Args:
            results: List of all results.
            search_text: Text to search for.
            status_filter: Status filter to apply.
            min_score: Minimum score threshold.
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

        # Score filter
        if min_score > 0.0:
            filtered = [
                r for r in filtered
                if r.get("total_score") is not None
                and r.get("total_score") >= min_score
            ]

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
        st.info(self.t("issue_summary_heading"))

        # Basic information
        col1, col2 = st.columns(2)
        with col1:
            st.text(self.t("task_id"))
            st.text(result.get("task_id", "N/A"))

            st.text(self.t("title"))
            st.text(result.get("title", "N/A"))
        with col2:
            st.text(self.t("status"))
            status = result.get("state", "N/A")
            st.text(status)

            score = result.get("total_score")
            score_display = f"{score:.1f}/10" if score is not None else "N/A"
            st.text(self.t("quality_score"))
            st.text(score_display)

        # Additional metadata
        st.divider()
        metadata_col1, metadata_col2 = st.columns(2)
        with metadata_col1:
            st.text(self.t("assignee"))
            st.text(result.get("assignee", "N/A"))

            st.text(self.t("created_at"))
            st.text(result.get("created_at", "N/A"))
        with metadata_col2:
            st.text(self.t("analyzed_at"))
            st.text(result.get("analyzed_at", "N/A"))

        # Description
        st.text(self.t("original_description"))
        description = result.get("description", "")
        if description:
            st.text_area(self.t("original_description"), value=description, disabled=False, height=150)
        else:
            st.info(self.t("no_description"))

        # Display analysis run configuration if available
        run_id = result.get("run_id")
        if run_id:
            self._display_analysis_run_configuration(run_id)

    def _display_analysis_run_configuration(self, run_id: int) -> None:
        """Display analysis run configuration information.

        Args:
            run_id: Analysis run ID.
        """
        try:
            analysis_run = self.repository.get_analysis_run(run_id)
            if analysis_run:
                st.subheader("⚙️ Analysis Configuration")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.text("Run Name:")
                    st.text(analysis_run.get("run_name", f"Run {run_id}"))
                with col2:
                    st.text("Created:")
                    st.text(analysis_run.get("created_at", "N/A"))
                
                st.divider()
                
                # Display run configuration details
                if analysis_run.get("system_prompt"):
                    st.write("**System Prompt:**")
                    st.text_area("System Prompt", value=analysis_run.get("system_prompt", ""), height=100, disabled=True)
                
                if analysis_run.get("general_prompt"):
                    st.write("**General Prompt:**")
                    st.text_area("General Prompt", value=analysis_run.get("general_prompt", ""), height=100, disabled=True)
                
                # Display run settings
                config_col1, config_col2 = st.columns(2)
                with config_col1:
                    include_overall = analysis_run.get("include_overall_conclusion", True)
                    st.write(f"**Include Overall Conclusion:** {'Yes' if include_overall else 'No'}")
                with config_col2:
                    split_by_criterion = analysis_run.get("split_by_criterion", False)
                    st.write(f"**Split By Criterion:** {'Yes' if split_by_criterion else 'No'}")
                
                # Display criteria definitions summary
                criteria = self.repository.get_criteria(run_id)
                if criteria:
                    st.divider()
                    st.write(f"**Total Criteria:** {len(criteria)}")
                    with st.expander("📋 View All Criteria Definitions", expanded=False):
                        for i, criterion in enumerate(criteria, 1):
                            st.write(f"**{i}. {criterion.get('title', 'Unknown Criterion')}**")
                            if criterion.get('description'):
                                st.write(f"*{criterion.get('description')}*")
                            st.write(f"Scoring: {criterion.get('scoring_system', 'percent')}")
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
        st.subheader(self.t("analysis_results"))

        analysis = result.get("analysis", {})
        if not analysis:
            st.warning(self.t("no_analysis_data"))
            return

        # Get criteria definitions for this analysis run
        run_id = result.get("run_id")
        criteria_definitions = self._get_criteria_definitions(run_id)

        # Overall conclusion
        overall_conclusion = analysis.get("overall_conclusion")
        if overall_conclusion:
            st.subheader(self.t("overall_conclusion"))
            st.markdown(overall_conclusion)

        # Criteria scores
        criteria_scores = analysis.get("criteria_scores", {})
        if criteria_scores:
            st.subheader(self.t("criteria_breakdown"))
            self._display_criteria_scores(criteria_scores, criteria_definitions)
        else:
            # Legacy format: check for 'criteria' field
            criteria = analysis.get("criteria", {})
            if criteria:
                st.subheader(self.t("criteria_breakdown"))
                self._display_legacy_criteria(criteria)

        # Recommendations
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            st.subheader(self.t("recommendations"))
            for i, recommendation in enumerate(recommendations, 1):
                st.markdown(f"{i}. {recommendation}")

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

    def _display_criteria_scores(self, criteria_scores: Dict[str, Any], criteria_definitions: Dict[str, Dict[str, Any]] = None) -> None:
        """Display criteria scores in a formatted way.

        Args:
            criteria_scores: Dictionary of criteria with scores and reviews.
            criteria_definitions: Dictionary of criteria definitions keyed by criterion_key.
        """
        if criteria_definitions is None:
            criteria_definitions = {}
        
        for criterion_name, criterion_data in criteria_scores.items():
            # Get the criteria definition for this criterion
            criterion_def = criteria_definitions.get(criterion_name)
            
            # Create a more descriptive title if we have the definition
            if criterion_def and criterion_def.get("title"):
                display_title = criterion_def.get("title")
            else:
                display_title = criterion_name
            
            with st.expander(display_title, expanded=False):
                # Show criteria definition if available
                if criterion_def:
                    st.write("📋 **Criteria Definition:**")
                    if criterion_def.get("description"):
                        st.write(f"*{criterion_def.get('description')}*")
                    
                    scoring_system = criterion_def.get("scoring_system", "percent")
                    st.write(f"**Scoring System:** {scoring_system}")
                    
                    if criterion_def.get("include_review"):
                        st.write("**Includes:** Review")
                    
                    st.divider()
                
                if isinstance(criterion_data, dict):
                    score = criterion_data.get("score")
                    review = criterion_data.get("review")

                    col_score, col_name1 = st.columns([1, 3])
                    with col_score:
                        if score is not None:
                            st.metric(self.t("score"), f"{score}/10")
                        else:
                            st.metric(self.t("score"), "N/A")

                    if review:
                        with st.container():
                            st.text(self.t("review"))
                            st.markdown(review)
                else:
                    # Simple score value
                    if isinstance(criterion_data, (int, float)):
                        col_score, col_name1 = st.columns([1, 3])
                        with col_score:
                            st.metric(self.t("score"), f"{criterion_data}/10")

    def _display_legacy_criteria(self, criteria: Dict[str, Any]) -> None:
        """Display criteria in legacy format.

        Args:
            criteria: Dictionary of criteria with detailed information.
        """
        for criterion_name, criterion_data in criteria.items():
            with st.expander(criterion_name, expanded=False):
                if isinstance(criterion_data, dict):
                    score = criterion_data.get("score")
                    review = criterion_data.get("review")
                    diagnosis = criterion_data.get("diagnosis")

                    col_score1, col_name1 = st.columns([1, 3])
                    with col_score1:
                        if score is not None:
                            st.metric(self.t("score"), f"{score}/10")
                        else:
                            st.metric(self.t("score"), "N/A")

                    if diagnosis:
                        with st.container():
                            st.text(self.t("diagnosis"))
                            st.markdown(diagnosis)

                    if review:
                        with st.container():
                            st.text(self.t("review"))
                            st.markdown(review)
