"""LLM Response Schema Definition.

This module defines the exact JSON schema format expected from LLM providers
based on the prompt_builder.py implementation and AnalysisPromptConfig dataclass.
"""

from typing import Literal

# From prompt_builder.py
ScoringSystem = Literal["binary", "percent", "five"]


def get_default_fake_response() -> str:
    """Generate default fake provider response matching exact LLM schema.
    
    This response structure is derived from the exact schema defined in
    prompt_builder.py's _build_json_schema_text() function.
    
    Returns:
        JSON string matching expected LLM response format
    """
    import json
    
    return json.dumps({
        "criteria": {
            "criterion_1": {
                "title": "Completeness and specificity",
                "description": (
                    "Check whether the issue contains concrete names, links, versions, "
                    "API signatures, expected behavior, and enough context to act on it."
                ),
                "scoring_system": "percent",
                "score": 85,
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "criteria_scores": {
            "criterion_1": 85
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Aggregated list of unique recommendations from all criteria"
        },
        "overall_conclusion": "Overall conclusion for the issue."
    }, ensure_ascii=False, indent=2)


def get_reseted_high_response() -> str:
    """Generate fake response for well-scoring criteria for reset evaluation"""
    import json
    
    return json.dumps({
        "criteria": {
            "criterion_1": {
                "title": "Reachability",
                "description": (
                    "Check whether the issue can be verified and resolved in the current context, "
                    "with clear acceptance criteria (DoD) or verifiable mitigation measures."
                ),
                "scoring_system": "percent",
                "score": 90,
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "criterion_2": {
                "title": "Clarity",
                "description": (
                    "Check whether the issue description is clear and unambiguous."
                ),
                "scoring_system": "percent",
                "score": 85,
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "criteria_scores": {
            "criterion_1": 90,
            "criterion_2": 85
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Aggregated list of unique recommendations from all criteria"
        },
        "overall_conclusion": "The issue is well-structured and can be resolved in the current context with clear acceptance criteria."
    }, ensure_ascii=False, indent=2)


def get_risk_assessment_response() -> str:
    """Generate fake response for risk assessment as shown in Russian examples."""
    import json
    
    return json.dumps({
        "criteria": {
            "criterion_1": {
                "title": "Risk Clarity",
                "description": (
                    "Check whether the risk description is clear, specific, and actionable. "
                    "Does it identify specific potential issues rather than vague concerns?"
                ),
                "scoring_system": "percent",
                "score": 85,
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "criterion_2": {
                "title": "Impact Assessment",
                "description": (
                    "Check whether the potential impact of the risk is properly assessed "
                    "and quantified if possible."
                ),
                "scoring_system": "percent",
                "score": 80,
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "criteria_scores": {
            "criterion_1": 85,
            "criterion_2": 80
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Aggregated list of unique recommendations from all criteria"
        },
        "overall_conclusion": "Risk assessment is comprehensive; it is recommended to further improve impact analysis and mitigation measures."
    }, ensure_ascii=False, indent=2)


def get_task_definition_response() -> str:
    """Generate fake response for task definition."""
    import json
    
    return json.dumps({
        "criteria": {
            "criterion_1": {
                "title": "Task Completeness",
                "description": (
                    "Check whether the task description includes all necessary details like "
                    "acceptance criteria, expected behavior, and deliverables."
                ),
                "scoring_system": "percent",
                "score": 90,
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "criterion_2": {
                "title": "Measurability",
                "description": (
                    "Check whether the task has clear success conditions that can be verified."
                ),
                "scoring_system": "binary",
                "score": 1,
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "criteria_scores": {
            "criterion_1": 90,
            "criterion_2": 1
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Aggregated list of unique recommendations from all criteria"
        },
        "overall_conclusion": "Task definition is clear and quantitatively verifiable."
    }, ensure_ascii=False, indent=2)


# Predefined responses for different scenario types
RESPONSE_TEMPLATES = {
    "default": get_default_fake_response(),
    "reset": get_reseted_high_response(),
    "risk": get_risk_assessment_response(),
    "task": get_task_definition_response(),
}


def get_response_for_scenario(scenario_type: str = "default") -> str:
    """Get fake response for a specific scenario type.
    
    Args:
        scenario_type: Type of scenario (default, reset, risk, task)
        
    Returns:
        JSON string matching LLM schema
    """
    return RESPONSE_TEMPLATES.get(scenario_type, RESPONSE_TEMPLATES["default"])


# Schema documentation for developers
EXPECTED_SCHEMA = {
    "criteria": {
        "type": "object",
        "description": (
            "Object where each key is a criterion identifier (criterion_1, criterion_2, etc.) "
            "and each value contains criterion details."
        ),
        "example": {
            "criterion_1": {
                "title": "Completeness and specificity",
                "description": "Check whether the issue contains concrete details...",
                "scoring_system": "binary|percent|five",
                "score": "0-100/or-0-5/etc.",
                "review": "Criterion-specific review (only when include_review=True)",
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "1-3 specific recommendations for this criterion"
                }
            }
        }
    },
    "criteria_scores": {
        "type": "object",
        "description": "Object mapping criterion keys to their scores",
        "example": {
            "criterion_1": 85,
            "criterion_2": 75
        }
    },
    "recommendations": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Aggregated list of unique recommendations from all criteria"
    },
    "overall_conclusion": {
        "type": "string",
        "description": "Overall conclusion for the issue"
    }
}
