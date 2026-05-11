from pathlib import Path
import sys


def main():
    from streamlit.web.cli import main as streamlit_main

    from jira_analyzer.app import streamlit as app

    sys.argv = [
        "streamlit",
        "run",
        str(Path(__file__).parent / f"{app.__file__}"),
    ] + sys.argv

    return streamlit_main()

