# Fake Provider Setup Guide

## Problem: Missing Analysis Results in Reports

If you're seeing reports like:
```
Issue Details
1. Issue 1
    Type: Risk    
Original Description
Your issue text...

(No analysis results shown)
```

This means the fake provider isn't returning structured JSON format that contains analysis fields.

## Solution: Configure Fake Provider with Structured Response

### Option 1: Use Environment Variables (Simplest)

Add to your `.env` file:

```bash
# .env file
LLM_PROVIDER_TYPE=fake
LLM_FAKE_RESPONSE='{"overall_conclusion": "Analysis complete", "criteria": {"completeness": {"title": "Completeness", "description": "Issue description completeness", "scoring_system": "percent", "score": 90}}, "criteria_scores": {"completeness": 90}}'
```

### Option 2: Set Programmatically (More Control)

```python
from jira_analyzer.analyzer.core.llm.adapter import SyncToAsyncLLMAdapter
from jira_analyzer.analyzer.service import AnalysisService
from jira_analyzer.providers import ProviderFactory

# Create fake provider with structured response
import json
structured_response = {
    "overall_conclusion": "Analysis complete",
    "criteria": {
        "completeness": {
            "title": "Completeness", 
            "description": "Issue description completeness",
            "scoring_system": "percent", 
            "score": 90
        }
    },
    "criteria_scores": {"completeness": 90},
    "recommendations": [
        "Issue structure is good",
        "Consider adding acceptance criteria"
    ],
    "analysis_description": "Analysis completed successfully using fake provider."
}

fake_provider = ProviderFactory.create_provider({
    "provider_type": "fake",
    "default_response": json.dumps(structured_response)
})

async_provider = SyncToAsyncLLMAdapter(fake_provider)

service = AnalysisService(
    prompt_template="{element_type}: {description}",
    llm_provider=async_provider
)
```

### Option 3: Use Updated Default (Easiest)

The system now has a built-in structured response as default. Just set:

```bash
# .env file (or ensure no LLM_FAKE_RESPONSE set)
LLM_PROVIDER_TYPE=fake
```

The default response now includes:
- `overall_conclusion`: Analysis status
- `criteria`: Individual criteria with scores
- `criteria_scores`: Summary of all scores  
- `recommendations`: List of improvement suggestions
- `analysis_description`: Detailed analysis text

## Expected Report Format

With proper fake provider setup, you should see:

```
Jira Task Analysis Report

Analyzed issues: 2
Summary
#       Issue         Type           Overall Conclusion
1       YA-1            Risk           Analysis complete
2       YA-2            Risk           Analysis complete

Issue Details

1. YA-1 - Risk

    Overall Conclusion: Analysis complete
    
    Criteria Analysis:
    - Completeness: 90/100
    
    Recommendations:
    * Issue structure is good
    * Consider adding acceptance criteria
    
    Analysis Description:
    Analysis completed successfully using fake provider.

    Original Description:
    Your issue text...

2. YA-2 - Risk
    [Similar detailed analysis...]
```

## Testing Different Scenarios

### Success Scenario
```python
fake_provider = ProviderFactory.create_provider({
    "provider_type": "fake",
    "default_response": json.dumps({
        "overall_conclusion": "pass",
        "criteria": {
            "completeness": {"score": 100},
            "clarity": {"score": 95}
        },
        "criteria_scores": {"completeness": 100, "clarity": 95},
        "recommendations": ["Excellent issue"],
        "analysis_description": "Issue meets all quality standards."
    })
})
```

### Partial Success Scenario
```python
fake_provider = ProviderFactory.create_provider({
    "provider_type": "fake",
    "default_response": json.dumps({
        "overall_conclusion": "partial",
        "criteria": {
            "completeness": {"score": 75}
        },
        "criteria_scores": {"completeness": 75},
        "recommendations": ["Add more details"],
        "analysis_description": "Issue needs improvements in completeness."
    })
})
```

### Failure Scenario  
```python
fake_provider = ProviderFactory.create_provider({
    "provider_type": "fake",
    "default_response": json.dumps({
        "overall_conclusion": "fail",
        "criteria": {
            "completeness": {"score": 30}
        },
        "criteria_scores": {"completeness": 30},
        "recommendations": ["Rewrite completely"],
        "analysis_description": "Issue lacks essential information."
    })
})
```

## Quick Start Examples

### For Development (No API Calls)
```python
# Just use default fake provider - no configuration needed!
from jira_analyzer.analyzer.service import AnalysisService

service = AnalysisService(prompt_template="{element_type}: {description}")
service.analyze_issues(issues_list)
```

### For Testing Specific Cases
```python
# Create custom responses for test scenarios
test_responses = {
    "good_issue": json.dumps({...}),
    "bad_issue": json.dumps({...})
}

# Use different fake providers for different test cases
```

### For CI/CD
```bash
# Run tests without real LLM API
LLM_PROVIDER_TYPE=fake pytest tests/
```

## Troubleshooting

**Report still shows no analysis results?**
- Restart your application to pick up new configuration
- Check `.env` file is loaded correctly
- Verify JSON response is valid (using `json.loads()`)

**Getting "object dict can't be used in 'await' expression"?**
- This should be fixed by the latest async adapter update
- Clear Python cache: `find . -type d -name __pycache__ -exec rm -rf {} +`

**JSON parsing errors?**
- Ensure your fake response is valid JSON
- Use `json.dumps()` to format response in Python code
- Avoid single quotes in JSON (use double quotes)

## Benefits

Fake provider setup allows you to:
- ✅ Develop and test without API costs
- ✅ Test specific scenarios reliably
- ✅ Run CI/CD without external dependencies
- ✅ Debug application logic without LLM variability
- ✅ Test error handling and edge cases

The fake provider maintains full compatibility with the analysis pipeline while giving you complete control over responses.
