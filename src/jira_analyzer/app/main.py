import sys
from jira_analyzer.cli import main

if __name__ == "__main__":
    # This maintains backward compatibility for running the script directly
    sys.exit(main())