import os
import sys
from pathlib import Path

if not __package__:
    # Make CLI runnable from source tree with
    #    python src/package
    package_source_path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, package_source_path)
    
if __name__ == "__main__":
    
    # By default, we trigger the CLI logic
    if "--streamlit" in sys.argv:
        from streamlit.web.cli import main as streamlit_main

        from jira_analyzer import ui as web_ui_app

        streamlit_args = [arg for arg in sys.argv[1:] if arg != "--streamlit"]
        sys.argv = [
            "streamlit",
            "run",
            str(Path(__file__).parent / f"{web_ui_app.__file__}"),
        ] + streamlit_args

        sys.exit(streamlit_main())
    else:
        from jira_analyzer.cli import main as cli_app

        sys.exit(cli_app())
    