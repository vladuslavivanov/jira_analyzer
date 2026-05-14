# Reamining Improvements TODO-List

- [x] Web application must save intermediate results in sqlite database. Clarification: service fetches task id's and first of all saves them in results repository as incomplete, results in the repository are filled while the analysis process till full completion
- [x] Update report structure according to FR-4 description in [requirements_spec](./requirements_spec.md)
    - [x] update LLM request to support recommendations
        - [ ] enumerate recommendations
    - [x] place statistics of criteria score in separate table
- [x] Update report section in UI according to UI requirements in end of spec. Only folder with markdown-report and output JSON must remain. 
- [x] Use asyncronous requests to LLM processing, not multithreading (see streamlit warnings on start up)
