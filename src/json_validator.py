import json


def validate_json(ai_response):
    """
    Extract and parse JSON from an LLM response.

    Local models often wrap JSON in markdown fences or add
    explanatory text before/after. This strips fences and then
    falls back to extracting the outermost JSON object/array.
    """

    if not ai_response:
        print("Empty AI response")
        return None

    # Remove markdown code fences if present
    cleaned = ai_response.replace("```json", "").replace("```", "").strip()

    # First attempt: parse as-is
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Fallback: extract the outermost JSON structure.
    # Test cases come as an array [...], analysis/techniques as {...}.
    candidates = []

    for open_char, close_char in (("[", "]"), ("{", "}")):
        start = cleaned.find(open_char)
        end = cleaned.rfind(close_char)
        if start != -1 and end != -1 and end > start:
            candidates.append((start, cleaned[start:end + 1]))

    # Prefer whichever structure appears first in the text
    candidates.sort(key=lambda c: c[0])

    for _, snippet in candidates:
        try:
            return json.loads(snippet)
        except Exception:
            continue

    print("Invalid JSON - could not parse AI response")
    print(cleaned[:500])
    return None
