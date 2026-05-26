Issue type:
{element_type}

Issue description:
{description}

General analysis prompt:
{general_prompt}

Criteria:
{criteria_block}

Output requirements:
- Return only valid JSON. Do not include markdown or explanatory text outside JSON.
- Follow the JSON schema below exactly and keep the exact criterion ids.
- Put every criterion result into the top-level "criteria" object.
- Each criterion result must include title, description, scoring_system, and score.
- Include a criterion review field only when that criterion explicitly asks for it.
- For each criterion, include recommendations as an array of 1-3 specific suggestions based on the score for that criterion.
- Put a compact score map into "criteria_scores" for downstream parsing.
- criteria_scores values must mirror the matching criteria.*.score values.
- Compute total_score as the average of all criteria_scores.
- Aggregate all unique criterion recommendations into the top-level recommendations list.
- Provide a list of recommendations for improving the issue description based on the analysis.
- Do not add criteria that are not listed in the schema.
- For binary criteria, score must be 0 or 1.
- For percent criteria, score must be an integer from 0 to 100.
- For five-point criteria, score must be an integer from 0 to 5.
- {overall_instruction}

JSON schema to follow:
{json_schema}