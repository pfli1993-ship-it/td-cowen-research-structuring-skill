#!/usr/bin/env python3
"""Extract an auditable draft from a TD Cowen Therapeutic Categories Outlook PDF."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

STAGE_ORDER = ["Preclinical", "Phase I", "Phase II", "Phase III", "NDA/BLA", "Marketed"]
STOP_WORDS = {
    "total", "source", "company", "product", "therapeutic", "categories", "outlook",
}
INACTIVE_RE = re.compile(
    r"\b(discontinued|halted|failed|withdrawn|terminated|de-?prioritized|missed primary|seeking partner|out.?license)\b",
    re.I,
)
POSITIVE_RE = re.compile(
    r"\b(encourag|promising|positive|impressive|strong|potential|hopeful|favorable|successful|met (?:its |the )?primary)\w*",
    re.I,
)
TIME_RE = re.compile(
    r"\b(?:Q[1-4]\s*[:']?\s*\d{2,4}|H[12]\s*[:']?\s*\d{2,4}|"
    r"(?:early|mid|late|year[- ]end|YE)\s*[:']?\s*\d{2,4}|"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|"
    r"20\d{2})\b",
    re.I,
)
CATALYST_RE = re.compile(
    r"(?i)(?:topline|top-line|data|readout|results?|primary completion|trial completion|"
    r"filing|submission|submit|approval|PDUFA|initiat\w+|launch\w*|expected|anticipat\w+)"
)


def clean(text: str) -> str:
    text = text.replace("\x00", " ").replace("\u00ad", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s*\n\s*", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", flat) if len(s.strip()) > 25]


def detect_date(text: str) -> str:
    match = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2}\b",
        text,
    )
    return match.group(0) if match else "未明确"


def detect_topic(page_texts: list[str], path: Path) -> str:
    excluded = re.compile(r"DEFINITION/BACKDROP|MAJOR TRENDS|DETAILED DISCUSSION|R&D PIPELINE", re.I)
    for line in page_texts[1].splitlines()[:18] if len(page_texts) > 1 else []:
        line = line.strip()
        if line.isupper() and 4 < len(line) < 100 and "THERAPEUTIC" not in line and not excluded.search(line):
            return line.title()
    name = re.sub(r"^\d+\s*-\s*Cowen Research\s*-\s*\d+\w?\s*", "", path.stem, flags=re.I)
    name = re.sub(r"\s*-\s*\d+\s*pages?$", "", name, flags=re.I)
    return name.strip() or path.stem


def section_pages(page_texts: list[str]) -> dict[str, list[int]]:
    markers = {
        "definition_backdrop": r"DEFINITION/BACKDROP|Landscape",
        "major_trends": r"MAJOR TRENDS\s*&\s*ISSUES",
        "detailed_discussion": r"DETAILED DISCUSSION",
        "rd_pipeline": r"R&D PIPELINE",
    }
    found: dict[str, list[int]] = {}
    for name, pattern in markers.items():
        hits = [i for i, text in enumerate(page_texts, 1) if re.search(pattern, text, re.I)]
        if hits:
            found[name] = hits
    return found


def stage_from_text(text: str) -> str:
    lower = text.lower()
    if re.search(r"\b(approved|approval|marketed|market|commerciali[sz])", lower):
        return "Marketed"
    if re.search(r"\b(nda|bla|maa|regulatory (?:filing|submission|review)|under review)", lower):
        return "NDA/BLA"
    if re.search(r"\b(?:phase|ph\.?)\s*(?:iii|3)\b|pivotal", lower):
        return "Phase III"
    if re.search(r"\b(?:phase|ph\.?)\s*(?:ii|2)\b", lower):
        return "Phase II"
    if re.search(r"\b(?:phase|ph\.?)\s*(?:i|1)\b|first-in-human", lower):
        return "Phase I"
    return "Preclinical"


def likely_pipeline_pages(page_texts: list[str], sections: dict[str, list[int]]) -> list[int]:
    if "rd_pipeline" in sections:
        start = sections["rd_pipeline"][0]
        pages = []
        for number in range(start, min(len(page_texts), start + 5) + 1):
            text = page_texts[number - 1]
            if number == start or re.search(r"COMPANY\s+PRODUCT|Total Drugs in Development", text, re.I):
                pages.append(number)
                if "Total Drugs in Development" in text:
                    break
        return pages
    return []


def parse_pipeline_rows(text: str) -> list[dict]:
    rows = []
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    skip_re = re.compile(
        r"Therapeutic Categories Outlook|R&D PIPELINE|COMPANY PRODUCT|Total Drugs|Source:|TD Cowen|Global Research|TDSecurities|Please see pages",
        re.I,
    )
    current = None
    for raw_line in lines:
        line = clean(raw_line)
        if skip_re.search(line) or len(line) < 18:
            continue
        bullet = re.match(r"^(.*?)\s+(?:•|⚫)\s*(.*)$", raw_line)
        if not bullet:
            if current and not re.match(r"^(October|20\d{2}|[0-9a-f-]+\.pdf)", line, re.I):
                current["pipeline_comment"] += " " + line
            continue
        head, comment = [clean(x) for x in bullet.groups()]
        paren_product = re.search(r"(\S+\s*\([^)]*\).*)$", head)
        if paren_product:
            product = paren_product.group(1)
            company = head[: paren_product.start()].strip()
        else:
            tokens = head.split()
            product_size = 3 if len(tokens) >= 4 and tokens[-2] == "&" else 1
            company = " ".join(tokens[:-product_size])
            product = " ".join(tokens[-product_size:])
        if not company or product.startswith("(") or company.lower() in STOP_WORDS or product.lower() in STOP_WORDS:
            continue
        if len(comment) < 8:
            continue
        current = {"company": company, "product": product, "pipeline_comment": comment}
        rows.append(current)
    return rows


def unique_candidates(rows: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for row in rows:
        key = (row["company"].lower(), re.sub(r"\W+", "", row["product"].lower()))
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def product_tokens(product: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]{2,}", product)
    return [t for t in tokens if t.lower() not in {"phase", "oral", "therapy", "product"}][:4]


def body_evidence(candidate: dict, page_texts: list[str], pipeline_pages: set[int]) -> tuple[list[int], str]:
    tokens = product_tokens(candidate["product"])
    hits = []
    excerpts = []
    for number, text in enumerate(page_texts, 1):
        if number in pipeline_pages:
            continue
        if any(re.search(rf"\b{re.escape(token)}\b", text, re.I) for token in tokens):
            hits.append(number)
            excerpts.extend([s for s in sentences(text) if any(token.lower() in s.lower() for token in tokens)])
    ranked = sorted(
        excerpts,
        key=lambda s: (bool(POSITIVE_RE.search(s)), bool(CATALYST_RE.search(s)), bool(TIME_RE.search(s)), len(s)),
        reverse=True,
    )
    return hits[:10], " ".join(ranked[:3])[:1600]


def catalyst_from_text(text: str, report_date: str) -> tuple[str, str]:
    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    report_year_match = re.search(r"20\d{2}", report_date)
    report_year = int(report_year_match.group()) if report_year_match else None
    report_month = next((i for i, name in enumerate(month_names, 1) if name.lower() in report_date.lower()), 1)
    report_index = report_year * 12 + report_month if report_year else 0
    def time_index(value: str) -> int:
        full = re.search(r"20\d{2}", value)
        short = re.search(r"\b(?:Q[1-4]|H[12]|YE)\s*[:']?\s*(\d{2})\b", value, re.I)
        year = int(full.group()) if full else (2000 + int(short.group(1)) if short else 0)
        month = 12
        quarter = re.search(r"\bQ([1-4])", value, re.I)
        half = re.search(r"\bH([12])", value, re.I)
        named = next((i for i, name in enumerate(month_names, 1) if name.lower() in value.lower()), None)
        if named:
            month = named
        elif quarter:
            month = int(quarter.group(1)) * 3
        elif half:
            month = int(half.group(1)) * 6
        return year * 12 + month if year else 0
    candidates = [s for s in sentences(text) if CATALYST_RE.search(s) and TIME_RE.search(s)]
    future = []
    for sentence in candidates:
        indexes = [time_index(t) for t in TIME_RE.findall(sentence)]
        if report_index and indexes and max(indexes) < report_index:
            continue
        future.append(sentence)
    future.sort(
        key=lambda s: (
            bool(re.search(r"\b(expected|anticipat\w+|planned|plans? to|will|topline|top-line|primary completion|trial completion|filing|submission|submit)\b", s, re.I)),
            not bool(re.search(r"\b(approved|reported|presented|initiated|began|received|failed|missed)\b", s, re.I)),
            len(s),
        ),
        reverse=True,
    )
    chosen = future[0] if future else ""
    times = TIME_RE.findall(chosen)
    eligible_times = [t for t in times if not report_index or time_index(t) >= report_index]
    timing = max(eligible_times, key=time_index) if eligible_times else "未明确"
    return chosen[:420] if chosen else "研报未明确下一催化剂", timing


def extract_highlights(page_texts: list[str], start_pages: list[int]) -> dict:
    opening = " ".join(page_texts[i - 1] for i in start_pages if i <= len(page_texts))
    ss = sentences(opening)
    epi = [s for s in ss if re.search(r"\b(?:million|billion|MM|BB|%|per 100,?000|incidence|prevalence|patients?)\b", s, re.I)]
    landscape = [s for s in ss if re.search(r"\b(?:approved|treatment|therapy|standard|first-line|market|sales)\b", s, re.I)]
    trends = [s for s in ss if re.search(r"\b(?:expect|believe|project|anticipat|potential|remain|continue|develop)\w*", s, re.I)]
    risks = [s for s in ss if re.search(r"\b(?:risk|fail|limitation|barrier|safety|side effect|challenge|uncertain|concern)\w*", s, re.I)]
    intro = ss[0] if ss else ""
    return {
        "disease_intro": {"text": intro[:650], "source_pages": start_pages[:2]},
        "epidemiology": [{"text": s[:420], "source_pages": start_pages[:3]} for s in epi[:4]],
        "treatment_landscape": [{"text": s[:420], "source_pages": start_pages[:3]} for s in landscape[:4]],
        "key_trends": [{"text": s[:420], "source_pages": start_pages[:4]} for s in trends[:5]],
        "risks": [{"text": s[:420], "source_pages": start_pages[:4]} for s in risks[:4]],
    }


def infer_sub_indications(page_texts: list[str], topic: str) -> list[str]:
    if len(page_texts) < 140:
        return []
    excluded = re.compile(
        r"THERAPEUTIC|OUTLOOK|TD COWEN|GLOBAL RESEARCH|DEFINITION|BACKDROP|MAJOR TRENDS|"
        r"DETAILED DISCUSSION|R&D PIPELINE|SOURCE|DISCLOSURE|OCTOBER|COMPANY|PRODUCT|"
        r"TABLE OF CONTENTS|PDUFA|SSRS?|SSRIS?",
        re.I,
    )
    found = []
    for text in page_texts[:-3]:
        for raw in text.splitlines()[:30]:
            line = clean(raw)
            if not (line.isupper() and 5 <= len(line) <= 65) or excluded.search(line):
                continue
            if line.title().lower() == topic.lower() or re.search(r"\d|[$%]", line):
                continue
            title = line.title()
            if title not in found:
                found.append(title)
    return found[:8]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()
    path = Path(args.pdf).expanduser().resolve()
    reader = PdfReader(str(path))
    page_texts = [clean(page.extract_text() or "") for page in reader.pages]
    joined_first = "\n".join(page_texts[:4])
    sections = section_pages(page_texts)
    pipe_pages = likely_pipeline_pages(page_texts, sections)
    rows = []
    for number in pipe_pages:
        rows.extend(parse_pipeline_rows(page_texts[number - 1]))
    rows = unique_candidates(rows)
    report_date = detect_date(joined_first)
    report_year_match = re.search(r"20\d{2}", report_date)
    report_year = int(report_year_match.group()) if report_year_match else None
    candidates = []
    for row in rows:
        body_pages, excerpt = body_evidence(row, page_texts, set(pipe_pages))
        combined = f"{row['pipeline_comment']} {excerpt}"
        catalyst, catalyst_time = catalyst_from_text(combined, report_date)
        active = not bool(INACTIVE_RE.search(row["pipeline_comment"]))
        stage = stage_from_text(row["pipeline_comment"])
        score = (4 if POSITIVE_RE.search(combined) else 0) + (3 if catalyst_time != "未明确" else 0)
        score += STAGE_ORDER.index(stage) + min(len(body_pages), 5)
        if stage == "Marketed":
            score -= 5
        candidates.append({
            **row,
            "stage": stage,
            "mechanism": row["pipeline_comment"][:240],
            "cowen_view": excerpt[:500] or row["pipeline_comment"][:500],
            "key_data": "",
            "catalyst": catalyst,
            "catalyst_time": catalyst_time,
            "source_pages": sorted(set(pipe_pages + body_pages)),
            "body_excerpt": excerpt,
            "active": active,
            "selection_score": score,
        })
    selected_pool = [c for c in candidates if c["active"] and (c["stage"] != "Marketed" or c["catalyst_time"] != "未明确")]
    selected = sorted(selected_pool, key=lambda c: c["selection_score"], reverse=True)[:6]
    if len(selected) < 5:
        fallback = [c for c in candidates if c["active"] and c not in selected]
        selected.extend(sorted(fallback, key=lambda c: c["selection_score"], reverse=True)[: 5 - len(selected)])
    opening_pages = list(range(2, min(len(page_texts), 5) + 1))
    highlights = extract_highlights(page_texts, opening_pages)
    payload = {
        "report": {
            "title": f"Therapeutic Categories Outlook: {detect_topic(page_texts, path)}",
            "topic": detect_topic(page_texts, path),
            "report_date": report_date,
            "page_count": len(page_texts),
            "input_pdf": str(path),
            "is_td_cowen_outlook": bool(re.search(r"Therapeutic Categories Outlook", joined_first, re.I) and re.search(r"TD Cowen|TD Securities", "\n".join(page_texts[:8]), re.I)),
            "sections": sections,
            "pipeline_pages": pipe_pages,
        },
        **highlights,
        "sub_indications": infer_sub_indications(page_texts, detect_topic(page_texts, path)),
        "pipeline_candidates": candidates,
        "selected_candidates": selected,
        "sources": {
            "note": "仅使用 TD Cowen 研报原文；页码为 PDF 页码。",
            "pages": sorted(set(opening_pages + pipe_pages + [p for c in selected for p in c["source_pages"]])),
        },
    }
    output = Path(args.output).expanduser().resolve() if args.output else path.with_suffix(".outlook.json")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "candidates": len(candidates), "selected": len(selected), "pipeline_pages": pipe_pages}, ensure_ascii=False))


if __name__ == "__main__":
    main()
