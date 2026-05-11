from jira import JIRA


def main() -> None:
    jira = JIRA(server="http://127.0.0.1:8081", options={"verify": False})
    issue = jira.issue("YA-1")

    print(issue.key)
    print(issue.fields.summary)
    print(issue.fields.status.name)


if __name__ == "__main__":
    main()

