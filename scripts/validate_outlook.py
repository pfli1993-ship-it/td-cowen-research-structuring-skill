#!/usr/bin/env python3
"""Validate structured TD Cowen Outlook JSON before rendering."""

import argparse
import json
import re
import sys
from pathlib import Path

STAGES = {"Preclinical", "Phase I", "Phase II", "Phase III", "NDA/BLA", "Marketed"}
INACTIVE = ("discontinued", "halted", "failed", "withdrawn", "terminated", "de-prioritized", "deprioritized")

def has_chinese(value):
    return bool(re.search(r"[\u4e00-\u9fff]", str(value or "")))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file")
    parser.add_argument("--require-chinese", action="store_true")
    args = parser.parse_args()
    path = Path(args.json_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors, warnings = [], []
    report = data.get("report", {})
    if not report.get("is_td_cowen_outlook"):
        errors.append("Input is not detected as a TD Cowen Therapeutic Categories Outlook report.")
    if not report.get("report_date") or report.get("report_date") == "未明确":
        warnings.append("Report date is not explicit.")
    selected = data.get("selected_candidates", [])
    active_total = sum(bool(c.get("active")) for c in data.get("pipeline_candidates", []))
    if active_total >= 5 and not 5 <= len(selected) <= 6:
        errors.append(f"Expected 5-6 selected candidates; found {len(selected)}.")
    if not selected:
        warnings.append("No selected candidates.")
    for idx, candidate in enumerate(selected, 1):
        prefix = f"selected_candidates[{idx}]"
        for field in ("company", "product", "stage", "mechanism", "cowen_view", "catalyst", "catalyst_time", "source_pages"):
            if not candidate.get(field):
                errors.append(f"{prefix}.{field} is required.")
        if candidate.get("stage") not in STAGES:
            errors.append(f"{prefix}.stage is invalid: {candidate.get('stage')}")
        evidence = str(candidate.get("pipeline_comment", ""))
        if not candidate.get("active") or any(word in evidence.lower() for word in INACTIVE):
            errors.append(f"{prefix} appears inactive and cannot be selected.")
        if args.require_chinese:
            for field in ("cowen_view", "catalyst"):
                if candidate.get(field) and not has_chinese(candidate.get(field)):
                    errors.append(f"{prefix}.{field} must be written in Simplified Chinese.")
            if candidate.get("key_data") and not has_chinese(candidate.get("key_data")):
                errors.append(f"{prefix}.key_data must be written in Simplified Chinese.")
    if args.require_chinese:
        intro = data.get("disease_intro", {})
        if intro.get("text") and not has_chinese(intro.get("text")):
            errors.append("disease_intro.text must be written in Simplified Chinese.")
        for section in ("epidemiology", "treatment_landscape", "key_trends", "risks"):
            for idx, item in enumerate(data.get(section, []), 1):
                text = item.get("text", "") if isinstance(item, dict) else item
                if text and not has_chinese(text):
                    errors.append(f"{section}[{idx}].text must be written in Simplified Chinese.")
    result = {"valid": not errors, "errors": errors, "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
