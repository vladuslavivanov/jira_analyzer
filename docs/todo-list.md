# Reamining Improvements TODO-List

- [ ] Web application must save intermediate results in sqlite database
- [x] Update report structure according to FR-4 description in [requirements_spec](./requirements_spec.md)
    - [ ] update LLM request to support recommendations
    - [ ] place statistics of criteria score in separate table
- [ ] Update report section in UI according to UI requirements in end of spec. Only folder with markdown-report and output JSON must remain. 
- [ ] Use asyncronous requests to LLM processing, not multithreading (see streamlit warnings on start up)
