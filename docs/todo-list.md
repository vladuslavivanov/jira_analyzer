# Reamining Improvements TODO-List

- [x] Web application must save intermediate results in sqlite database. Clarification: service fetches task id's and first of all saves them in results repository as incomplete, results in the repository are filled while the analysis process till full completion
- [x] Update report structure according to FR-4 description in [requirements_spec](./requirements_spec.md)
    - [x] update LLM request to support recommendations
        - [x] enumerate recommendations
    - [x] place statistics of criteria score in separate table
- [x] Update report section in UI according to UI requirements in end of spec. Only folder with markdown-report and output JSON must remain. 
- [x] Use asyncronous requests to LLM processing, not multithreading (see streamlit warnings on start up)

- [x] fix mock jira to return all data on any request
- [ ] change default dataset in jira mock
- [x] page for ready analysis viewing: master-detail view where list of tasks and details for one
  - fix issue with fixed score limit. - add "analysis session storage" to store original analysis criteria.
  - 
- [x] load final prompt template from resource file for easier updating
- [x] add dubug logging of sent requests and recieved responses
- [x] docker compose config
- [ ] add hints to prompt configuration UI: like "must describe scoring system: what is bad, what is good", general recommendations of prompt engeneering, etc.
- [x] ensure independence from Deepseek LLM provider. Should be able easily add new LLM Provider
- [x] LLM reasoning setting
- [ ] extract localization configuratino to resource file
- [ ] Title/Summary mismatch which leads to "No title" in results page in list.
- [ ] Show processing status for tasks in list on results page.
- [ ] Asignee is not provided on results page even if asignee for task is set.
- [ ] Add ability to export analysis config from results page which was used for task
- [ ] Wrong N/A value of Creation Date for real task in results page.

- [ ] experiments:
  - analyse AI model value:
    - multiple runs for:
      - models: deepseek & GLM
      - single prompt
      - split-criteria prompt
      - reasoning-mode
    - to collect data:
      - criteria score (variance)
      - total tokens consumption
