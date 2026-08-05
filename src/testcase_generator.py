from pathlib import Path
import json

from src import llm
from src.config import (
    GENERATION_NUM_PREDICT,
    GENERATION_TEMPERATURE,
    MIN_CASES_PER_TECHNIQUE,
    SYSTEM_JSON_RULE,
)
from src.json_validator import validate_json

# Stage 3 must return an ARRAY of rows; stage 1/2 need single objects.
# Forcing the array in the system role stops models from collapsing the
# skeleton into one object.
SYSTEM_ARRAY_RULE = (
    "You are an expert QA assistant. You always respond with ONE valid JSON "
    "ARRAY of test-case objects and nothing else. No markdown code fences, "
    "no explanations, no extra text outside the JSON array."
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
        system=SYSTEM_ARRAY_RULE,
        json_mode=True,
    )

    return response


def _case_keys(test_case_format):
    if test_case_format == "GWT":
        return [
            "S.No", "Title", "Given", "When", "Then",
            "Test Data", "Testing Technique",
        ]
    return [
        "S.No", "Title of Test Case", "Pre Requisites",
        "Actions to be done", "Expected Results",
        "Test Data", "Testing Technique",
    ]


def _skeleton_cases(test_case_format):
    """Pre-filled array skeleton with exactly MIN_CASES_PER_TECHNIQUE rows.

    Models reliably fill a numbered skeleton instead of returning a short
    array when told "at least N" — this guarantees the per-technique count.
    """

    keys = _case_keys(test_case_format)
    rows = [
        {key: (index if key == "S.No" else "") for key in keys}
        for index in range(1, MIN_CASES_PER_TECHNIQUE + 1)
    ]

    return json.dumps(rows, indent=2)


def generate_testcases_for_technique(
    requirement_json,
    technique,
    test_case_format="Conventional Test Case",
    llm_config=None,
    retry_hint=None,
):
    """
    One focused generation call for a SINGLE testing technique.

    Stage 3 runs this once per selected technique and merges the results,
    which is what produces the technique-combination matrix instead of a
    single batch of cases.
    """

    prompt = _load_prompt(test_case_format)
    skeleton = _skeleton_cases(test_case_format)

    full_prompt = f"""
{prompt}

====================================

Requirement Analysis

{requirement_json}

====================================

FOCUSED TECHNIQUE

Apply ONLY this testing technique:

{technique}

====================================

OUTPUT CONTRACT

1. Return EXACTLY {MIN_CASES_PER_TECHNIQUE} test cases — no more, no fewer.
2. Fill every row of the skeleton below; never omit, merge or shorten rows.
3. Every row's "Testing Technique" field must be exactly: {technique}
4. Every test case must genuinely apply "{technique}" to the requirements.
5. Cover every acceptance criterion and business rule with this technique.
6. No duplicate scenarios.

SKELETON TO FILL (replace the empty values, keep S.No):

{skeleton}
"""

    if retry_hint:
        full_prompt += f"\n\n{retry_hint}\n"

    response = llm.chat(
        llm_config or llm.LLMConfig(),
        full_prompt,
        temperature=GENERATION_TEMPERATURE,
        num_predict=GENERATION_NUM_PREDICT,
        system=SYSTEM_ARRAY_RULE,
        json_mode=True,
    )

    rows = _extract_rows(response)

    # Some free-tier models (heavy reasoning models in particular) return a
    # single row despite the skeleton. Make one top-up attempt demanding the
    # missing rows, then merge unique cases — guarantees as many rows as the
    # model is able to produce.
    if len(rows) < MIN_CASES_PER_TECHNIQUE:
        existing = "\n".join(
            f"- {r.get('Title of Test Case', '').strip()}" for r in rows if r.get("Title of Test Case")
        )
        top_up_hint = (
            f"Your previous answer returned only {len(rows)} of the required "
            f"{MIN_CASES_PER_TECHNIQUE} test cases.\n"
            f"Already given titles (do NOT repeat them):\n{existing}\n"
            f"Return EXACTLY {MIN_CASES_PER_TECHNIQUE} DISTINCT test cases "
            f'applying "{technique}", filling the skeleton completely.'
        )
        second = llm.chat(
            llm_config or llm.LLMConfig(),
            full_prompt + "\n\n" + top_up_hint + "\n",
            temperature=GENERATION_TEMPERATURE,
            num_predict=GENERATION_NUM_PREDICT,
            system=SYSTEM_ARRAY_RULE,
            json_mode=True,
        )
        second_rows = _extract_rows(second)

        seen = set()
        seen_empty = False
        combined = []
        for case in rows + second_rows:
            title = (case.get("Title of Test Case") or "").strip().lower()
            if title:
                if title in seen:
                    continue
                seen.add(title)
            elif seen_empty:
                continue
            else:
                seen_empty = True
            combined.append(case)

        return json.dumps(combined)

    return response


def _extract_rows(raw):
    """Parse a stage-3 reply into a list of row dicts (dict replies become a 1-row list)."""
    if not raw:
        return []
    parsed = validate_json(raw)
    if parsed is None:
        return []
    if isinstance(parsed, dict):
        return [parsed]
    return [case for case in parsed if isinstance(case, dict)]


def generate_testcases_for_techniques(
    requirement_json,
    techniques,
    test_case_format="Conventional Test Case",
    llm_config=None,
    retry_hint=None,
):
    """
    Generate cases for SEVERAL techniques in one call (a batch).

    Batching keeps the run fast on free-tier providers: one larger call is
    dramatically cheaper in wall time than one call per technique (which runs
    well past 3 minutes when 5-8 techniques are selected). The skeleton
    pre-tags every row with its technique, and a top-up attempt covers models
    that under-fill the array.
    """

    keys = _case_keys(test_case_format)
    expected = len(techniques) * MIN_CASES_PER_TECHNIQUE

    skeleton_rows = []
    s_no = 1
    for technique in techniques:
        for _ in range(MIN_CASES_PER_TECHNIQUE):
            skeleton_rows.append(
                {
                    key: (
                        s_no
                        if key == "S.No"
                        else (technique if key == "Testing Technique" else "")
                    )
                    for key in keys
                }
            )
            s_no += 1
    skeleton = json.dumps(skeleton_rows, indent=2)

    prompt = _load_prompt(test_case_format)
    techniques_line = "; ".join(techniques)

    full_prompt = f"""
{prompt}

====================================

Requirement Analysis

{requirement_json}

====================================

FOCUSED TECHNIQUES

Apply ONLY these testing techniques (each row is tagged with exactly ONE of them):

{techniques_line}

====================================

OUTPUT CONTRACT

1. Return EXACTLY {expected} test cases — no more, no fewer
   ({len(techniques)} techniques x {MIN_CASES_PER_TECHNIQUE} cases each).
2. Fill every row of the skeleton below; never omit, merge or shorten rows.
3. Every row's "Testing Technique" field must remain exactly the value that is
   pre-filled in that row of the skeleton.
4. Every test case must genuinely apply its tagged technique to the requirements.
5. Cover every acceptance criterion and business rule across the rows.
6. No duplicate scenarios.

SKELETON TO FILL (replace the empty values, keep S.No and Testing Technique):

{skeleton}
"""

    if retry_hint:
        full_prompt += f"\n\n{retry_hint}\n"

    response = llm.chat(
        llm_config or llm.LLMConfig(),
        full_prompt,
        temperature=GENERATION_TEMPERATURE,
        num_predict=GENERATION_NUM_PREDICT,
        system=SYSTEM_ARRAY_RULE,
        json_mode=True,
    )

    rows = _extract_rows(response)

    if len(rows) < expected:
        existing = "\n".join(
            f"- {r.get('Title of Test Case', '').strip()}"
            for r in rows
            if r.get("Title of Test Case")
        )
        top_up_hint = (
            f"Your previous answer returned only {len(rows)} of the required "
            f"{expected} test cases.\n"
            f"Already given titles (do NOT repeat them):\n{existing}\n"
            f"Return EXACTLY {expected} DISTINCT test cases, using the "
            f"techniques {techniques_line}, filling the skeleton completely."
        )
        second = llm.chat(
            llm_config or llm.LLMConfig(),
            full_prompt + "\n\n" + top_up_hint + "\n",
            temperature=GENERATION_TEMPERATURE,
            num_predict=GENERATION_NUM_PREDICT,
            system=SYSTEM_ARRAY_RULE,
            json_mode=True,
        )
        second_rows = _extract_rows(second)

        seen = set()
        seen_empty = False
        combined = []
        for case in rows + second_rows:
            title = (case.get("Title of Test Case") or "").strip().lower()
            if title:
                if title in seen:
                    continue
                seen.add(title)
            elif seen_empty:
                continue
            else:
                seen_empty = True
            combined.append(case)

        return json.dumps(combined)

    return response


def group_rows_by_technique(rows, techniques):
    """
    Bucket parsed batch rows by their "Testing Technique" tag.

    Rows whose tag doesn't match a batch technique (model drift) are assigned
    to the least-populated technique so every technique still gets its cases.
    Returns [(technique, [rows]), ...] preserving the input technique order.
    """

    counts = {technique: 0 for technique in techniques}
    buckets = {technique: [] for technique in techniques}

    for row in rows:
        tag = str(row.get("Testing Technique") or "").strip().lower()
        match = next((t for t in techniques if t.lower() == tag), None)
        if not match:
            match = min(counts, key=counts.get)
        row["Testing Technique"] = match
        buckets[match].append(row)
        counts[match] += 1

    return [(technique, buckets[technique]) for technique in techniques]


def merge_technique_testcases(per_technique_cases):
    """
    Combine [(technique, [cases]), ...] into one flat list.

    Stamps each row's "Testing Technique" column with the technique it was
    generated for and renumbers S.No sequentially across the whole set.
    """

    merged = []

    for technique, cases in per_technique_cases:
        if isinstance(cases, dict):
            cases = [cases]
        for case in cases:
            if not isinstance(case, dict):
                continue
            case["Testing Technique"] = technique
            merged.append(case)

    for index, case in enumerate(merged, start=1):
        case["S.No"] = index

    return merged
