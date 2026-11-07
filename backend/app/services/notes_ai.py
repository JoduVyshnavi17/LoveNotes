
import json

from langdetect import detect, DetectorFactory
from google import genai
from google.genai import types

from ..config import settings


DetectorFactory.seed = 0


# ==================================================
# GEMINI CLIENT
# ==================================================

def client():
    if not settings.gemini_api_key:
        raise RuntimeError(
            "AI features require GEMINI_API_KEY in backend/.env"
        )

    return genai.Client(
        api_key=settings.gemini_api_key
    )


# ==================================================
# SOURCE LANGUAGE DETECTION
# ==================================================

def detect_source_language(text: str) -> str:
    try:
        if not text or not text.strip():
            return "unknown"

        return detect(text)

    except Exception:
        return "unknown"


# ==================================================
# GEMINI GENERATION
# ==================================================

def generate(
    prompt: str,
    system_instruction: str,
    json_mode: bool = False
) -> str:

    config = types.GenerateContentConfig(
        temperature=0,
        system_instruction=system_instruction,
        response_mime_type=(
            "application/json" if json_mode else "text/plain"
        )
    )

    gemini_client = client()

    try:
        result = gemini_client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=config
        )

        if not result.text:
            raise RuntimeError(
                "Gemini returned an empty response"
            )

        return result.text

    finally:
        gemini_client.close()


# ==================================================
# 1. FAITHFUL RECONSTRUCTION SUPPORT
# ==================================================

def enhance(
    text: str,
    language: str = "auto-detect from source"
) -> str:

    source_language = detect_source_language(text)

    system_instruction = (
        f"The source language code is {source_language}. "
        "You are an educational notes formatting assistant. "
        "Write in exactly the same language and original script. "
        "Never translate the source. "
        "Preserve all original information and meaning. "
        "Improve readability, grammar and formatting. "
        "Organize existing content with suitable headings "
        "and paragraphs. "
        "Do not add new concepts, examples or facts. "
        "Do not remove any identifiable information. "
        "Keep [unclear] markers. "
        "Return well-formatted Markdown. "
        "Language hint: " + language
    )

    prompt = f"""
Improve the readability and organization of these notes.

IMPORTANT:
- Preserve the original meaning.
- Preserve every identifiable point.
- Correct obvious transcription formatting problems.
- Use appropriate headings and paragraphs.
- Do not add new educational content.
- Do not translate.
- Keep uncertain text marked as [unclear].

SOURCE NOTES:

{text}
"""

    return generate(
        prompt=prompt,
        system_instruction=system_instruction
    )


# ==================================================
# 2. COMPLETE MY NOTES
# ==================================================

def complete_notes(text: str) -> str:

    source_language = detect_source_language(text)

    system_instruction = (
        f"The source language code is {source_language}. "
        "You are an expert educational notes-completion assistant. "
        "Write entirely in the original language and script. "
        "Preserve all original concepts and their meaning. "
        "Organize the notes using clear headings and subheadings. "
        "Improve grammar, readability and structure. "
        "Add relevant missing definitions, explanations, "
        "examples and important subtopics. "
        "Clearly label newly added material as "
        "'Additional Learning Material' in the source language. "
        "Never present added information as original source text. "
        "Do not invent citations or references. "
        "Keep original information intact. "
        "Return well-formatted Markdown."
    )

    prompt = f"""
Complete and organize the following student notes.

REQUIREMENTS:

1. Preserve every important point from the original notes.
2. Correct obvious grammar and formatting problems.
3. Organize concepts into meaningful sections.
4. Explain incomplete concepts where appropriate.
5. Add relevant definitions and examples.
6. Add important missing subtopics.
7. Clearly separate original material from additional material.
8. Do not remove important information.
9. Do not translate the notes.
10. Do not invent citations or references.

ORIGINAL NOTES:

{text}

Return the completed notes in Markdown.
"""

    return generate(
        prompt=prompt,
        system_instruction=system_instruction
    )


# ==================================================
# 3. COMPLETE MY NOTES - MISSING POINT SUGGESTIONS
# ==================================================

def suggestions(
    text: str,
    depth: str = "detailed",
    purpose: str = "personal learning"
) -> list[dict]:

    if depth not in {
        "basic",
        "detailed",
        "comprehensive"
    }:
        depth = "detailed"

    source_language = detect_source_language(text)

    prompt = f"""
Review these notes for possible missing points.

SOURCE LANGUAGE CODE: {source_language}

IMPORTANT LANGUAGE RULE:
Write every generated text field in the same language
and script as the source notes.

Depth: {depth}
Purpose: {purpose}

For students, consider missing:
- Definitions
- Subtopics
- Steps
- Examples
- Formulas
- Revision concepts

Clearly distinguish possible gaps from optional enrichment.

Return a JSON object with key "suggestions" containing an array.

Each item must contain:
- category
- title
- content
- rationale
- evidence
- confidence (0 to 1)

Allowed categories:
- explicit_omission
- potential_gap
- optional_enrichment

Use explicit_omission only if the notes signal an omission.

Potential gaps must be qualified.
Optional enrichment is not required content.

Do not duplicate existing content.
Never invent citations, facts or references.

Return an empty array if there are no defensible suggestions.

NOTES:
{text}
"""

    system_instruction = (
        f"The source language code is {source_language}. "
        "You are a cautious notes-review assistant. "
        "The source notes are authoritative. "
        "Write every generated field in the source language "
        "and original script. "
        "Never switch languages. "
        "Do not invent facts or citations. "
        "Return valid JSON only."
    )

    raw = generate(
        prompt=prompt,
        system_instruction=system_instruction,
        json_mode=True
    )

    try:
        data = json.loads(raw)

        if not isinstance(data, dict):
            raise ValueError(
                "Suggestions response must be a JSON object"
            )

        items = data.get("suggestions", [])

        if not isinstance(items, list):
            raise ValueError(
                "Suggestions must be a JSON array"
            )

        allowed = {
            "explicit_omission",
            "potential_gap",
            "optional_enrichment"
        }

        clean = []

        for item in items:

            if not isinstance(item, dict):
                continue

            if item.get("category") not in allowed:
                continue

            try:
                confidence = float(
                    item.get("confidence", 0)
                )
            except (TypeError, ValueError):
                confidence = 0.0

            clean.append({
                "category": item["category"],
                "title": str(
                    item.get("title", "Suggestion")
                )[:255],
                "content": str(
                    item.get("content", "")
                ),
                "rationale": str(
                    item.get("rationale", "")
                ),
                "evidence": str(
                    item.get("evidence", "")
                ),
                "confidence": max(
                    0.0,
                    min(1.0, confidence)
                )
            })

        return clean

    except Exception as exc:
        raise RuntimeError(
            f"Could not parse AI suggestions: {exc}"
        ) from exc


# ==================================================
# 4. STUDY SUMMARY AND QUIZ
# ==================================================

def study_aids(
    text: str,
    kind: str
) -> dict | list:

    if kind not in {"summary", "quiz"}:
        raise ValueError(
            "Kind must be summary or quiz"
        )

    source_language = detect_source_language(text)

    if kind == "summary":

        task = """
Create a detailed structured study summary.

Return a JSON object containing:
- title
- introduction
- concepts (array of name and definition)
- definitions (array of term and definition)
- applications (array)
- steps (array)
- formulas (array)
- key_points (array)
"""

        expected_format = "JSON object"

    else:

        task = """
Create exactly 8 multiple-choice questions.

Return a JSON array.

Each question must contain:
- question
- options (exactly four options)
- answer_index (0, 1, 2 or 3)
- explanation

Questions must be based only on the source notes.

Avoid duplicate questions.
Ensure the correct answer matches answer_index.
"""

        expected_format = "JSON array"

    prompt = f"""
{task}

SOURCE LANGUAGE CODE: {source_language}

Write every field in the same language and script
as the original notes.

Do not translate.

Do not invent facts or information absent from the notes.

Return a valid {expected_format}.

SOURCE NOTES:

{text}
"""

    raw = generate(
        prompt=prompt,
        system_instruction=(
            f"The source language code is {source_language}. "
            "You are an accurate educational study assistant. "
            "Use the same language and script as the source notes. "
            "Never translate into another language. "
            "Do not invent facts. "
            "Return valid JSON only."
        ),
        json_mode=True
    )

    try:
        result = json.loads(raw)

        if kind == "summary":

            if not isinstance(result, dict):
                raise ValueError(
                    "Summary response must be a JSON object"
                )

        else:

            if not isinstance(result, list):
                raise ValueError(
                    "Quiz response must be a JSON array"
                )

            for question in result:

                if not isinstance(question, dict):
                    raise ValueError(
                        "Each quiz question must be an object"
                    )

                options = question.get("options")
                answer_index = question.get("answer_index")

                if not isinstance(options, list) or len(options) != 4:
                    raise ValueError(
                        "Every quiz question must have four options"
                    )

                if (
                    not isinstance(answer_index, int)
                    or isinstance(answer_index, bool)
                    or answer_index not in range(4)
                ):
                    raise ValueError(
                        "Invalid quiz answer_index"
                    )

                for field in (
                    "question",
                    "explanation"
                ):
                    if not isinstance(question.get(field), str):
                        raise ValueError(
                            f"Missing or invalid quiz field: {field}"
                        )

        return result

    except Exception as exc:
        raise RuntimeError(
            f"Could not parse study aids: {exc}"
        ) from exc
