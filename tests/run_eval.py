import itertools
import json
import sys
import time
from pathlib import Path

# let this script import the files in the app folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import text_to_sql
from text_to_sql import ask, get_schema, run_query
from eval_questions import TESTS


def norm_value(v):
    if isinstance(v, (int, float)):
        return round(float(v), 1)
    return v


def norm_rows(rows):
    return sorted((tuple(norm_value(v) for v in r) for r in rows), key=str)


def results_match(ref_rows, got_rows):
    """Same rows, any order; the model may return extra columns."""
    if len(ref_rows) != len(got_rows):
        return False
    if not ref_rows:
        return True
    ref_width = len(ref_rows[0])
    got_width = len(got_rows[0])
    if got_width < ref_width:
        return False
    expected = norm_rows(ref_rows)
    for cols in itertools.permutations(range(got_width), ref_width):
        projected = [tuple(row[i] for i in cols) for row in got_rows]
        if norm_rows(projected) == expected:
            return True
    return False


def main():
    if len(sys.argv) > 1:
        text_to_sql.MODEL = sys.argv[1]
    model = text_to_sql.MODEL
    print("Model:", model, "\n")

    schema = get_schema()
    records = []

    for number, (level, question, ref_sql) in enumerate(TESTS, start=1):
        _, ref_rows = run_query(ref_sql)
        try:
            out = ask(question, schema)
        except Exception as e:
            out = {"sql": "", "rows": [], "error": f"API error: {e}", "attempts": 0}

        passed = out["error"] is None and results_match(ref_rows, out["rows"])
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {number:02d} {level:<6} {question} (attempts: {out['attempts']})")
        if not passed:
            print("   Model SQL:", out["sql"].replace("\n", " "))
            print("   Error:", out["error"])
            print("   Expected:", ref_rows[:3])
            print("   Got:     ", out["rows"][:3])

        records.append({
            "number": number, "level": level, "question": question,
            "passed": passed, "attempts": out["attempts"],
            "model_sql": out["sql"], "error": out["error"],
        })
        time.sleep(2)  # stay under the free-tier rate limit

    total = len(records)
    passed_all = sum(r["passed"] for r in records)
    first_try = sum(r["passed"] and r["attempts"] == 1 for r in records)

    print("\n=== RESULTS ===")
    print(f"Overall accuracy: {passed_all}/{total} = {100 * passed_all / total:.0f}%")
    print(f"Correct on first attempt: {first_try}/{total}")
    for level in ["easy", "medium", "hard"]:
        group = [r for r in records if r["level"] == level]
        got = sum(r["passed"] for r in group)
        print(f"  {level}: {got}/{len(group)}")

    safe_name = model.replace("/", "_")
    out_path = Path(__file__).resolve().parent / f"results_{safe_name}.json"
    out_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print("Saved details to", out_path)


if __name__ == "__main__":
    main()