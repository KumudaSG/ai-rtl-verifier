from pipeline import run_pipeline, MODEL_NAME


def main():
    results = []

    print(f"Running repeated sampling for model: {MODEL_NAME}\n")

    for trial in range(1, 6):
        print(f"========== Trial {trial} ==========")

        try:
            solution, verification_result = run_pipeline()
            passed = verification_result["pass"]

            results.append({
                "trial": trial,
                "pass": passed,
                "reason": verification_result["reason"]
            })

            print("Pass" if passed else "Fail")
            print("Reason:", verification_result["reason"])
            print()

        except Exception as error:
            results.append({
                "trial": trial,
                "pass": False,
                "reason": f"Pipeline crashed: {error}"
            })

            print("Fail")
            print("Reason:", f"Pipeline crashed: {error}")
            print()

    print("===== Final Summary =====")
    for item in results:
        verdict = "Pass" if item["pass"] else "Fail"
        print(f"Trial {item['trial']}: {verdict}")

    print("\nDetailed Results:")
    for item in results:
        print(f"Trial {item['trial']}: {item['reason']}")


if __name__ == "__main__":
    main()