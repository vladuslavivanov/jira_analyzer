import sys
from jira_analyzer.cli import main

if __name__ == "__main__":
    # This entry point allows running the package as:
    # python -m jira_analyzer [args]
    #
    # To run the Streamlit UI, use:
    # streamlit run src/jira_analyzer/ui.py
    
    # By default, we trigger the CLI logic
    sys.exit(main())