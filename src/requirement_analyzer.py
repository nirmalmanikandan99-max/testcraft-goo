from pathlib import Path

from src import llm
from src.config import ANALYSIS_NUM_PREDICT, ANALYSIS_TEMPERATURE

PROMPT_FILE = Path("prompts") / "requirement_analysis_prompt.txt"


def analyze_requirements(context, llm_config=None):

    print("Step 1 - Reading Prompt")

    with open(PROMPT_FILE, "r", encoding="utf-8") as file:
        prompt = file.read()

    print("Step 2 - Prompt Read Successfully")

    full_prompt = f"""
{prompt}

==============================

PROJECT CONTEXT

==============================

{context}
"""

    print("Step 3 - Calling LLM")

    response = llm.chat(
        llm_config or llm.LLMConfig(),
        full_prompt,
        temperature=ANALYSIS_TEMPERATURE,
        num_predict=ANALYSIS_NUM_PREDICT,
    )

    print("Step 4 - Response Received")

    return response
