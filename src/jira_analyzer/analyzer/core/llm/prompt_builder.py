from typing import TextIO


def build_prompt(element_type: str, description: str, prompt_file: TextIO) -> str:
    """
    Forms a prompt for the LLM based on the element type and description.

    Note: We use .replace() instead of .format() to avoid conflicts with
    the literal curly braces used in the JSON structure within the template.
    """
    template = prompt_file.read()

    # Replace placeholders manually
    prompt = template.replace("{element_type}", str(element_type))
    prompt = prompt.replace("{description}", str(description))

    return prompt