from pathlib import Path

from src import llm
from src.config import ANALYSIS_NUM_PREDICT, ANALYSIS_TEMPERATURE

PROMPT_FILE = Path("prompts") / "technique_selector_prompt.txt"


def select_techniques(requirement_json, llm_config=None):

    with open(PROMPT_FILE, "r", encoding="utf-8") as file:
        prompt = file.read()

    full_prompt = f"""
{prompt}

REQUIREMENT ANALYSIS

{requirement_json}
"""

    response = llm.chat(
        llm_config or llm.LLMConfig(),
        full_prompt,
        temperature=ANALYSIS_TEMPERATURE,
        num_predict=ANALYSIS_NUM_PREDICT,
    )

    return response
