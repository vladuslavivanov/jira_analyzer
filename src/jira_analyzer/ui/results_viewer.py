"""Results Viewer for browsing SQLite analysis results."""

import json
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

    def render(self, force_reload: bool = False) -> None:
        """Render the master-detail results viewer interface.

        Args:
            force_reload: If True, force reload results from database.
                          Otherwise, use cached results if available.
        """
        # Load results: force reload when entering the page, otherwise use cache
        if force_reload or "all_results" not in st.session_state:
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
                    st.warning(self.t("skipping_malformed", error=validation_error))
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
            all_runs_label = self.t("all_runs")
            run_options = [(all_runs_label, None)] + [(r.get("run_name", f"Run {r['run_id']}"), r['run_id']) for r in analysis_runs]
            run_filter = st.selectbox(
                self.t("analysis_run_label"),
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
                options=["All", "Pending", "Processing", "Completed", "Failed"],
                format_func=lambda x: {
                    "All": self.t("filter_all"),
                    "Pending": self.t("filter_pending"),
                    "Processing": self.t("filter_processing"),
                    "Completed": self.t("filter_completed"),
                    "Failed": self.t("filter_failed"),
                }.get(x, x),
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
            title = result.get("title") or self.t("no_title")

            # Create clickable card for each result
            is_selected = task_id == st.session_state.selected_result_id
            card_color = "primary" if is_selected else "secondary"
            
            # Determine state indicator (all states except completed get an emoji)
            state = result.get("state", "PENDING")
            if state == "PENDING":
                state_prefix = "⏳ "
            elif state == "PROCESSING":
                state_prefix = "🔄 "
            elif state == "FAILED":
                state_prefix = "❌ "
            else:
                state_prefix = ""      # completed or unknown — no emoji

            # Use button to select the result (simple direct interaction)
            if st.button(
                f"{state_prefix}{self.t('issue_title', id=task_id, title=title)}",
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
        if status_filter == "Pending":
            filtered = [r for r in filtered if r.get("state") == "PENDING"]
        elif status_filter == "Processing":
            filtered = [r for r in filtered if r.get("state") == "PROCESSING"]
        elif status_filter == "Completed":
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
        st.header(f"📋 {self.t('brief_analysis_details')}")

        # Manual table implementation for cleaner formatting
        col1, col2 = st.columns(2)
        with col1:
            st.metric(self.t("task_id"), result.get("task_id", "N/A"), label_visibility="visible")
            st.metric(self.t("status"), result.get("state", "N/A"), label_visibility="visible")
            st.metric(self.t("analyzed_at"), self._format_date(result.get("analyzed_at")), label_visibility="visible")
        with col2:
            st.metric(self.t("assignee"), result.get("assignee", "N/A"), label_visibility="visible")
            st.metric(self.t("created_at"), self._format_date(result.get("created_at")), label_visibility="visible")

        # Task Description
        st.subheader(f"📝 {self.t('task_description')}")
        description = result.get("description", "")
        if description:
            st.text_area("Description", value=description, disabled=True, height=200, label_visibility="collapsed")
        else:
            st.info(self.t("no_description"))

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
                with st.expander(f"⚙️ {self.t('analysis_configuration')}", expanded=False):
                    # Run metadata
                    metadata_col1, metadata_col2 = st.columns(2)
                    with metadata_col1:
                        st.write(f"**{self.t('run_name_label')}:** {analysis_run.get('run_name', f'Run {run_id}')}")
                        st.write(f"**{self.t('label_created')}:** {self._format_date(analysis_run.get('created_at'))}")
                    with metadata_col2:
                        include_overall = analysis_run.get("include_overall_conclusion", True)
                        st.write(f"**{self.t('label_include_overall')}:** {self.t('yes') if include_overall else self.t('no')}")
                        split_by_criterion = analysis_run.get("split_by_criterion", False)
                        st.write(f"**{self.t('label_split_by_criterion')}:** {self.t('yes') if split_by_criterion else self.t('no')}")
                        reasoning_enabled = analysis_run.get("reasoning_enabled", False)
                        st.write(f"**{self.t('label_reasoning_mode')}:** {self.t('label_enabled') if reasoning_enabled else self.t('label_disabled')}")
                        if reasoning_enabled:
                            reasoning_effort = analysis_run.get("reasoning_effort", 'high')
                            st.write(f"**{self.t('label_reasoning_effort')}:** {reasoning_effort.capitalize()}" )
                    
                    st.divider()
                    
                    # Display run configuration details
                    if analysis_run.get("system_prompt"):
                        st.subheader(f"🤖 {self.t('system_prompt')}")
                        st.text_area(self.t("system_prompt"), value=analysis_run.get("system_prompt", ""), height=80, disabled=True, label_visibility="collapsed")
                    
                    if analysis_run.get("general_prompt"):
                        st.subheader(f"📋 {self.t('general_prompt')}")
                        st.text_area(self.t("general_prompt"), value=analysis_run.get("general_prompt", ""), height=80, disabled=True, label_visibility="collapsed")
                    
                    # Display criteria definitions summary
                    criteria = self.repository.get_criteria(run_id)
                    if criteria:
                        st.subheader(f"📏 {self.t('criteria_definitions_count', count=len(criteria))}")
                        with st.expander(f"📋 {self.t('view_all_criteria_definitions')}", expanded=False):
                            for i, criterion in enumerate(criteria, 1):
                                st.markdown(f"**{i}. {criterion.get('title', self.t('unknown_criterion'))}**")
                                if criterion.get('description'):
                                    st.markdown(f"*{criterion.get('description')}*")
                                st.write(f"**{self.t('scoring_system')}:** {criterion.get('scoring_system', 'percent')}")
                                if criterion.get('include_review'):
                                    st.write(f"*{self.t('includes_review_label')}*")
                                st.divider()

                    # Export button
                    export_data = {
                        "version": 1,
                        "run_name": analysis_run.get("run_name", f"Run {run_id}"),
                        "created_at": analysis_run.get("created_at", ""),
                        "system_prompt": analysis_run.get("system_prompt", ""),
                        "general_prompt": analysis_run.get("general_prompt", ""),
                        "include_overall_conclusion": analysis_run.get("include_overall_conclusion", True),
                        "split_by_criterion": analysis_run.get("split_by_criterion", False),
                        "reasoning_enabled": analysis_run.get("reasoning_enabled", False),
                        "reasoning_effort": analysis_run.get("reasoning_effort", "high"),
                        "criteria": [
                            {
                                "title": c.get("title", ""),
                                "description": c.get("description", ""),
                                "scoring_system": c.get("scoring_system", "percent"),
                                "include_review": bool(c.get("include_review", False)),
                            }
                            for c in (criteria or [])
                        ],
                    }
                    export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
                    st.download_button(
                        label=self.t("export_config"),
                        data=export_json,
                        file_name=f"analysis_config_run_{run_id}.json",
                        mime="application/json",
                        use_container_width=True,
                    )
        except Exception as e:
            st.warning(self.t("loaded_config_error", error=e))

    def _display_analysis_result(self, result: Dict[str, Any]) -> None:
        """Display detailed analysis results.

        Args:
            result: Result dictionary with analysis data.
        """
        st.divider()
        st.header(f"📊 {self.t('analysis_results')}")

        analysis = result.get("analysis", {})
        if not analysis:
            st.warning(self.t("no_analysis_data"))
            return

        # Overall conclusion
        overall_conclusion = analysis.get("overall_conclusion")
        if overall_conclusion:
            st.subheader(f"🎯 {self.t('overall_conclusion')}")
            st.markdown(overall_conclusion)

        # Criteria scores - Table formatted display
        criteria_scores = analysis.get("criteria_scores", {})
        criteria_full = analysis.get("criteria", {})
        if criteria_scores:
            st.subheader(f"📈 {self.t('criteria_breakdown')}")
            self._display_criteria_scores_table(result, criteria_scores, criteria_full)
        else:
            # Legacy format: check for 'criteria' field
            criteria = analysis.get("criteria", {})
            if criteria:
                st.subheader(f"📈 {self.t('criteria_breakdown')}")
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
            expander_title = f"📊 {display_title} - {self.t('score')}: {score_display}"
            
            with st.expander(expander_title, expanded=False):
                # Display score system
                st.markdown(f"**📈 {self.t('score_system_label')}:** {scoring_system}")
                
                # Display fix recommendations
                if recommendations and isinstance(recommendations, list):
                    st.markdown(f"**🔧 {self.t('fix_recommendations_label')}:**")
                    for i, rec in enumerate(recommendations, 1):
                        st.markdown(f"  {i}. {rec}")
                
                # Display review
                if review:
                    st.markdown(f"**📝 {self.t('review')}:**")
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
                    self.t("criterion_name"): criterion_name,
                    self.t("score"): score_display,
                    self.t("scoring_system"): "N/A",
                    self.t("review"): review[:100] + "..." if len(str(review)) > 100 else review,
                    self.t("diagnosis"): diagnosis[:100] + "..." if len(str(diagnosis)) > 100 else diagnosis,
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
                        with st.expander(f"📝 {self.t('details_for_criterion', criterion_name=criterion_name)}", expanded=False):
                            if diagnosis:
                                st.markdown(f"**{self.t('diagnosis')}:** {diagnosis}")
                            if review:
                                st.markdown(f"**{self.t('review')}:** {review}")
