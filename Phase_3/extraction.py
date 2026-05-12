# extraction.py

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
import instructor

from memory import Lesson

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if OPENROUTER_API_KEY is None:
    raise ValueError("OPENROUTER_API_KEY not found in environment")


MODEL_NAME = "openai/gpt-5.4"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://github.com/yourusername/ai-rtl-verifier",
        "X-Title": "ai-rtl-verifier",
    },
)

client = instructor.patch(client)


EXTRACTION_SYSTEM_PROMPT = """
You are extracting reusable engineering lessons from SystemVerilog RTL attempts.

Your job is to produce one structured Lesson object.

The lesson must help a future RTL-generating agent avoid similar mistakes or repeat useful design behavior.

Rules:
- Do not copy the specific solution.
- Do not include exact numeric test answers.
- Do not include problem-specific names unless they describe a general RTL concept.
- The lesson must be reusable.
- If the lesson only applies to this exact problem, mark it as problem_specific.
- If the lesson applies to similar problems in the same family, mark it as family_specific.
- If the lesson applies broadly across RTL design, mark it as domain_general.
- The rationale must explain the engineering principle behind the lesson.
"""


def extract_lesson(
    problem_id: str,
    problem_prompt: str,
    attempted_solution: str,
    outcome: str,
    failure_type: Optional[str],
    verifier_reason: Optional[str]
) -> Lesson:
    user_prompt = f"""
Problem ID:
{problem_id}

Problem Prompt:
{problem_prompt}

Attempted Solution:
{attempted_solution}

Outcome:
{outcome}

Failure Type:
{failure_type}

Verifier Reason:
{verifier_reason}

Extract one reusable lesson from this attempt.

Return:
- condition: when the lesson applies
- action: what the RTL agent should do
- rationale: why this action matters
- generality: problem_specific, family_specific, or domain_general
"""

    lesson = client.chat.completions.create(
        model=MODEL_NAME,
        response_model=Lesson,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": EXTRACTION_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        max_retries=2,
    )

    return lesson

