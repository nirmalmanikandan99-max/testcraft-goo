from pathlib import Path

from src import llm
from src.config import (
    GENERATION_NUM_PREDICT,
    GENERATION_TEMPERATURE,
    SYSTEM_JSON_RULE,
)

PROMPT_FOLDER = Path("prompts")

# Conventional flow uses the dedicated generator prompt (7-column format).
# GWT flow reuses the GWT prompt (Given/When/Then columns).
CONVENTIONAL_PROMPT = PROMPT_FOLDER / "testcase_generator_prompt.txt"
GWT_PROMPT = PROMPT_FOLDER / "gwt_prompt.txt"


def _load_prompt(test_case_format):
    if test_case_format == "GWT":
        path = GWT_PROMPT
    else:
        path = CONVENTIONAL_PROMPT

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def generate_testcases(
    requirement_json,
    technique_json,
    test_case_format="Conventional Test Case",
    llm_config=None,
    retry_hint=None,
):

    prompt = _load_prompt(test_case_format)

    full_prompt = f"""
{prompt}

====================================

Requirement Analysis

{requirement_json}

====================================

Selected Testing Techniques

{technique_json}

====================================
"""

    if retry_hint:
        full_prompt += f"\n\n{retry_hint}\n"

    response = llm.chat(
        llm_config or llm.LLMConfig(),
        full_prompt,
        temperature=GENERATION_TEMPERATURE,
        # Test cases can be many rows; a low limit truncates the JSON
        # mid-array and breaks parsing. Give generous headroom.
        num_predict=GENERATION_NUM_PREDICT,
        system=SYSTEM_JSON_RULE,
    )

    return response
