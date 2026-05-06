# memory_pipeline.py

from typing import Dict, Any, List

from problems import get_prompt
from memory import MemoryStore, MemoryEntry, create_memory_entry
from extraction import extract_lesson


from tool_pipeline import generate_solution, convert_to_verifier_solution, generate_solution_from_prompt

from verifier import verify


PROBLEM_FEATURES = {
    "P1": "family A, combinational logic, signed arithmetic, overflow detection",
    "P2": "family A, FSM, accumulator, valid gating, signed running sum, control datapath split",
    "P3": "family A, FSM, sequential multiplication, signed arithmetic, overflow detection, control datapath split",
    "P4": "family A, FSM, pulse counting, valid gating, target count, done signaling",
    "P5": "family A, FIFO, pointer wraparound, full empty flags, read write control",

    "P6": "family B, stack, LIFO memory, push pop control, pointer module, full empty flags",
    "P7": "family B, FIFO queue, pointer module, read write pointers, memory module, simultaneous read write",
    "P8": "family B, circular buffer, sliding window sum, accumulator, pointer wraparound, valid sample count",
    "P9": "family B, register file, decoder, synchronous write, combinational read, one hot write enable",
    "P10": "family B, priority buffer, selector, valid bits, highest value selection, insert remove control",
}


def get_problem_features(problem_id: str) -> str:
    problem_id = problem_id.strip().upper()

    if problem_id not in PROBLEM_FEATURES:
        raise ValueError(f"Invalid problem id: {problem_id}")

    return PROBLEM_FEATURES[problem_id]


def format_lessons_for_prompt(lessons: List[MemoryEntry]) -> str:
    if len(lessons) == 0:
        return "No relevant prior lessons."

    text = ""

    for index, entry in enumerate(lessons, start=1):
        text += f"Lesson {index} from {entry.source_problem_id}:\n"
        text += f"When: {entry.lesson.condition}\n"
        text += f"Do: {entry.lesson.action}\n"
        text += f"Why: {entry.lesson.rationale}\n"
        text += f"Generality: {entry.lesson.generality}\n\n"

    return text


def run_memory_pipeline(
    problem_id: str,
    k: int = 3,
    memory_path: str = "memory_dump.json",
    verbose: bool = True,
    timeout_seconds: int = 60
) -> Dict[str, Any]:

    problem_id = problem_id.strip().upper()

    print(f"\nRunning memory pipeline for {problem_id}\n")

    store = MemoryStore(memory_path)

    problem_prompt = get_prompt(problem_id)
    problem_features = get_problem_features(problem_id)

    retrieved_lessons = store.retrieve(
        current_problem_id=problem_id,
        current_features=problem_features,
        k=k
    )

    lesson_text = format_lessons_for_prompt(retrieved_lessons)

    if verbose:
        print("Retrieved lessons:")
        print(lesson_text)

    augmented_prompt = f"""
Relevant prior lessons:
{lesson_text}

Current problem:
{problem_prompt}
"""

    # For now, your generate_solution uses problem_id and gets prompt internally.
    # Later, update generate_solution to accept augmented_prompt if needed.
    generated_solution = generate_solution_from_prompt(problem_id, augmented_prompt)

    rtl_solution = convert_to_verifier_solution(generated_solution)

    verification_result = verify(
        problem_id,
        rtl_solution,
        verbose=verbose,
        timeout_seconds=timeout_seconds
    )

    print("\nVerification result:")
    print(verification_result)

    outcome = "pass" if verification_result["pass"] else "fail"
    verifier_reason = verification_result.get("reason")

    failure_type = None
    if outcome == "fail":
        failure_type = "verifier_failure"

    lesson = extract_lesson(
        problem_id=problem_id,
        problem_prompt=problem_prompt,
        attempted_solution=str(generated_solution),
        outcome=outcome,
        failure_type=failure_type,
        verifier_reason=verifier_reason
    )

    print("\nExtracted Lesson:")
    print(lesson)

    entry = create_memory_entry(
        source_problem_id=problem_id,
        problem_features=problem_features,
        outcome=outcome,
        failure_type=failure_type,
        lesson=lesson
    )

    store.write(entry)

    print("\nMemory updated successfully.")

    return {
        "problem_id": problem_id,
        "retrieved_lessons": retrieved_lessons,
        "verification_result": verification_result,
        "lesson": lesson,
        "memory_entry": entry
    }


if __name__ == "__main__":
    run_memory_pipeline("P7", k=3)
