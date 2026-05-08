import os
import sys

if not __package__:
    # Make CLI runnable from source tree with
    #    python src/mock_jira
    package_source_path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, package_source_path)

from mock_jira.server import main


if __name__ == "__main__":
    main()

