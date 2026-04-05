from dotenv import load_dotenv
import os
from openai import OpenAI
import instructor

from pipeline import RTLSolution, PROBLEM_PROMPT, MODEL_NAME
from verifier import verify


load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

client = instructor.patch(client)


def generate_with_history(messages):
    return client.chat.completions.create(
        model=MODEL_NAME,
        response_model=RTLSolution,
        temperature=0,
        messages=messages,
        max_retries=2
    )


def main():
    messages = [
        {
            "role": "system",
            "content": "You are an expert FPGA and SystemVerilog engineer. Always return a valid structured solution."
        },
        {
            "role": "user",
            "content": PROBLEM_PROMPT
        }
    ]

    turn_results = []

    for turn in range(1, 4):  # max 3 turns
        print(f"\n========== TURN {turn} ==========")

        solution = generate_with_history(messages)

        verification_result = verify(solution)

        passed = verification_result["pass"]
        reason = verification_result["reason"]

        turn_results.append({
            "turn": turn,
            "pass": passed,
            "reason": reason
        })

        print("Pass" if passed else "Fail")
        print("Reason:", reason)

        if passed:
            break

        # Append feedback to conversation
        messages.append({
            "role": "assistant",
            "content": "Previous solution failed verification."
        })

        messages.append({
            "role": "user",
            "content": f"""
The previous RTL solution failed verification.

Verifier feedback:
{reason}

Fix the design. Focus on:
- Correct multiplication logic
- Proper handling of signed values
- Correct overflow detection
- Ensuring done is asserted at the correct time

Return a corrected full structured solution.
"""
        })

    print("\n===== Final Summary =====")
    for item in turn_results:
        verdict = "Pass" if item["pass"] else "Fail"
        print(f"Turn {item['turn']}: {verdict}")

    final_pass = turn_results[-1]["pass"]
    print("\nFinal Pass/Fail:", "Pass" if final_pass else "Fail")


if __name__ == "__main__":
    main()