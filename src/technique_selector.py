from pathlib import Path

from src import llm
from src.config import ANALYSIS_NUM_PREDICT, ANALYSIS_TEMPERATURE, SYSTEM_JSON_RULE

PROMPT_FILE = Path("prompts") / "technique_selector_prompt.txt"


def select_techniques(requirement_json, llm_config=None, retry_hint=None):

    with open(PROMPT_FILE, "r", encoding="utf-8") as file:
        prompt = file.read()

    full_prompt = f"""
{prompt}

REQUIREMENT ANALYSIS

{requirement_json}
"""

    if retry_hint:
        full_prompt += f"\n\n{retry_hint}\n"

    response = llm.chat(
        llm_config or llm.LLMConfig(),
        full_prompt,
        temperature=ANALYSIS_TEMPERATURE,
        num_predict=ANALYSIS_NUM_PREDICT,
        system=SYSTEM_JSON_RULE,
        json_mode=True,
    )

    return response
