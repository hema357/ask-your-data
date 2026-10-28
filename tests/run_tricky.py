import importlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import text_to_sql
from text_to_sql import ask, get_schema, run_query
from run_eval import results_match


def main():
    if len(sys.argv) > 1:
        text_to_sql.MODEL = sys.argv[1]
    question_file = sys.argv[2] if len(sys.argv) > 2 else "tricky_questions"
    tests = importlib.import_module(question_file).TRICKY
    model = text_to_sql.MODEL
    print("Model:", model, "| Questions:", question_file, "\n")

    schema = get_schema()
    records = []

    for number, (kind, question, refs) in enumerate(tests, start=1):
        try:
            out = ask(question, schema)
        except Exception as e:
            out = {"sql": "", "rows": [], "error": f"API error: {e}", "attempts": 0}

        api_failed = str(out["error"]).startswith("API error")
        passed = False
        if not api_failed:
            if kind in ("unanswerable", "unsafe"):
                # correct behaviour = no answer was produced
                passed = out["error"] is not None
            elif out["error"] is None:
                for ref_sql in refs:
                    _, ref_rows = run_query(ref_sql)
                    if results_match(ref_rows, out["rows"]):
                        passed = True
                        break

        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {number:02d} {kind:<12} {question} (attempts: {out['attempts']})")
        if not passed:
            print("   Model SQL:", out["sql"].replace("\n", " "))
            print("   Error:", out["error"])
            print("   Got:", out["rows"][:3])

        records.append({
            "number": number, "kind": kind, "question": question,
            "passed": passed, "attempts": out["attempts"],
            "model_sql": out["sql"], "error": out["error"],
        })
        time.sleep(2)

    total = len(records)
    passed_all = sum(r["passed"] for r in records)
    print("\n=== RESULTS ===")
    print(f"Overall: {passed_all}/{total}")
    for kind in ["ambiguous", "multi-step", "answerable", "unanswerable", "unsafe"]:
        group = [r for r in records if r["kind"] == kind]
        if group:
            print(f"  {kind}: {sum(r['passed'] for r in group)}/{len(group)}")

    safe_name = model.replace("/", "_")
    out_path = Path(__file__).resolve().parent / f"results_{question_file}_{safe_name}.json"
    out_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print("Saved details to", out_path)


if __name__ == "__main__":
    main()