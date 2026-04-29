import streamlit as st
import json
import pandas as pd
from pathlib import Path

from jira_analyzer.analyzer.engine import run_analysis
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
    Upload your Jira issues export (JSON) to analyze the quality of descriptions and requirements using AI.
    """)

    # Sidebar for configuration
    st.sidebar.header("Settings")
    
    # File uploader
    uploaded_file = st.sidebar.file_uploader("Upload Jira JSON", type=["json"])
    
    # Option to use sample data if no file is uploaded
    use_sample = st.sidebar.checkbox("Use sample data (data/input.json)", value=not uploaded_file)

    if st.button("🚀 Run Analysis"):
        issues = None
        
        try:
            if uploaded_file is not None:
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
                display_cols = ["input_element_type", "overall_score", "verdict", "diagnosis", "recommendations"]
                available_cols = [c for c in display_cols if c in df.columns]
                
                if not df.empty:
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
                                st.markdown(res.get("recommendations", "No recommendations available"))
                        
                        st.divider()
                else:
                    st.warning("No issues were processed.")

        except Exception as e:
            st.error(f"An error occurred during analysis: {e}")
            logger.exception("UI Analysis Error")

if __name__ == "__main__":
    main()