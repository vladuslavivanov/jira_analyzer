from pathlib import Path
import sys

from streamlit.web.cli import main as streamlit_main

def main():
    sys.argv = [
        "streamlit",
        "run",
        str(Path(__file__).parent.parent / "main.py"),
    ] + sys.argv

    return streamlit_main()

