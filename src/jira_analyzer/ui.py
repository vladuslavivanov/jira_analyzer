import streamlit as st
import json
import pandas as pd
from pathlib import Path

from jira_analyzer.analyzer.engine import run_analysis
from jira_analyzer.tasktracker.jira import JiraConnectionConfig, fetch_issue
from jira_analyzer.tasktracker.jira import jira_issue_to_analysis_input
from jira_analyzer.tasktracker.jira.jira_parser import load_issues
from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    st.set_page_config(
        page_title="Jira AI Linter",
        page_icon="🤖",
        layout="wide"
    )

    st.title("🤖 Jira AI Task Linter")
    st.markdown("""
    Upload your Jira issues export (JSON) or fetch a Jira issue by key to analyze
    the quality of descriptions and requirements using AI.
    """)

    # Sidebar for configuration
    st.sidebar.header("Settings")

    source = st.sidebar.radio("Issue source", ["Jira", "JSON"], horizontal=True)
    uploaded_file = None
    use_sample = False
    jira_server = ""
    jira_issue = ""
    jira_username = ""
    jira_token = ""
    jira_verify_ssl = True

    if source == "Jira":
        jira_server = st.sidebar.text_input(
            "Jira server URL",
            value="http://127.0.0.1:8081",
        )
        jira_issue = st.sidebar.text_input("Jira issue key", value="YA-1")
        jira_username = st.sidebar.text_input("Jira username")
        jira_token = st.sidebar.text_input("Jira API token/password", type="password")
        jira_verify_ssl = st.sidebar.checkbox("Verify SSL", value=False)
    else:
        uploaded_file = st.sidebar.file_uploader("Upload Jira JSON", type=["json"])
        use_sample = st.sidebar.checkbox(
            "Use sample data (data/input.json)",
            value=not uploaded_file,
        )

    if st.button("🚀 Run Analysis"):
        issues = None
        
        try:
            if source == "Jira":
                if not jira_server or not jira_issue:
                    st.error("Jira server URL and issue key are required.")
                    return

                config = JiraConnectionConfig(
                    server=jira_server,
                    username=jira_username or None,
                    token=jira_token or None,
                    verify_ssl=jira_verify_ssl,
                )
                with st.spinner(f"Fetching {jira_issue} from Jira..."):
                    jira_issue_data = fetch_issue(jira_issue, config)
                    issues = [jira_issue_to_analysis_input(jira_issue_data)]
            elif uploaded_file is not None:
                # Process uploaded file
                data = json.load(uploaded_file)
                if not isinstance(data, list):
                    st.error("Invalid format: JSON must be a list of issues.")
                else:
                    issues = data
            elif use_sample:
                # Fallback to local sample
                # Resolving path relative to this file
                project_root = Path(__file__).parent.parent.parent.parent
                sample_path = project_root / "jira_analyzer" / "data" / "input.json"
                if sample_path.exists():
                    issues = load_issues(str(sample_path))
                else:
                    st.error(f"Sample file not found at {sample_path}")
            
            if issues:
                with st.spinner(f"Analyzing {len(issues)} issues via LLM..."):
                    results = run_analysis(issues)
                
                st.success("Analysis Complete!")
                
                # Display results in a table
                df = pd.DataFrame(results)
                
                # Aligning with keys from system_prompt.template
                # overall_score, verdict, diagnosis, recommendations
                display_cols = [
                    "input_element_type",
                    "overall_score",
                    "verdict",
                    "diagnosis",
                    "recommendations",
                ]
                available_cols = [c for c in display_cols if c in df.columns]
                
                if not df.empty:
                    st.subheader("JSON Result")
                    st.json(results)
                    st.download_button(
                        "Download JSON",
                        data=json.dumps(results, ensure_ascii=False, indent=2),
                        file_name="analysis_result.json",
                        mime="application/json",
                    )

                    st.subheader("Summary Table")
                    # Using width='stretch' as per Streamlit deprecation warning
                    st.dataframe(df[available_cols] if available_cols else df, width="stretch")
                    
                    st.subheader("Detailed Breakdown")
                    for i, res in enumerate(results):
                        header_name = res.get('input_element_type', 'Unknown')
                        st.write(f"### Issue {i+1}: {header_name}")
                        
                        # Handle potential error results where LLM failed
                        if "error" in res:
                            st.error(f"Failed to analyze this issue: {res['error']}")
                            st.write("**Original Description:**")
                            st.info(res.get("input_description", "No description provided"))
                        else:
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.metric("Overall Score", res.get("overall_score", "N/A"))
                                verdict = res.get('verdict', 'N/A')
                                if "Принять" in verdict:
                                    st.success(f"**Verdict:** {verdict}")
                                elif "Отклонить" in verdict:
                                    st.error(f"**Verdict:** {verdict}")
                                else:
                                    st.warning(f"**Verdict:** {verdict}")
                                
                                # Show sub-scores if available
                                scores = res.get("criteria_scores", {})
                                if isinstance(scores, dict) and scores:
                                    st.write("**Criteria Breakdown:**")
                                    for k, v in scores.items():
                                        st.write(f"- {k.replace('_', ' ').title()}: {v}")
                            
                            with col2:
                                st.write("**Original Description:**")
                                st.info(res.get("input_description", "No description provided"))
                                
                                st.write("**Diagnosis:**")
                                st.write(res.get("diagnosis", "No diagnosis available"))
                                
                                st.write("**Recommendations:**")
                                st.markdown(
                                    res.get(
                                        "recommendations",
                                        "No recommendations available",
                                    )
                                )
                        
                        st.divider()
                else:
                    st.warning("No issues were processed.")

        except Exception as e:
            st.error(f"An error occurred during analysis: {e}")
            logger.exception("UI Analysis Error")

if __name__ == "__main__":
    main()
