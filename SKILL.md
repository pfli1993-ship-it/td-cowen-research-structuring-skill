---
name: structure-td-cowen-therapeutic-outlook
description: 将 TD Cowen / TD Securities Therapeutic Categories Outlook 系列 PDF 自动结构化为中文治疗格局长图。用户拖入或提到该系列的疾病、治疗类别或多适应症报告时使用；提取疾病简介、流行病学、现有治疗格局、Cowen 关键观点、R&D Pipeline、重点药物及报告时点的 Catalyst，生成临床阶段赛马图、HTML、JSON 和 PNG，并保存到下载目录后用 Pixea 打开。仅使用研报信息，不联网更新；不要用于普通单公司研报。
---

# TD Cowen Therapeutic Outlook Long Image

## Workflow

1. Confirm the PDF is a TD Cowen `Therapeutic Categories Outlook` report.
   - Run `scripts/extract_outlook.py <pdf> --output <json>`.
   - Stop and explain if `report.is_td_cowen_outlook` is false.
   - Treat `report.report_date` as the information cutoff. Do not browse or update events.

2. Review and complete the extracted JSON.
   - Read `references/schema.md` before editing the JSON.
   - Preserve every factual field's `source_pages`; do not add unsupported companies, stages, dates, or catalysts.
   - Translate and rewrite the final long-image content in concise Simplified Chinese. Do not render the extractor's English draft directly.
   - Chinese is mandatory for `disease_intro`, `epidemiology`, `treatment_landscape`, `key_trends`, `risks`, `cowen_view`, `key_data`, and `catalyst`.
   - Keep drug names, company names, trial names, mechanism abbreviations, regulatory abbreviations, and explicit timing expressions in English where appropriate.
   - For broad reports containing multiple sub-indications, summarize the major sub-indications in `sub_indications`, then select candidates across them.
   - If a broad report has no consolidated `R&D Pipeline` table, use the detected `sub_indications` as search anchors and build `pipeline_candidates` from explicit body evidence before selecting 5-6 projects.
   - Select 5-6 active candidates. Prioritize positive or strategically important Cowen commentary, then clear catalysts, body coverage, and later stage.
   - Exclude discontinued, halted, failed, withdrawn, or deprioritized programs from `selected_candidates`.
   - Do not create a probability-of-success score.

3. Validate and render.
   - Run `scripts/validate_outlook.py <json> --require-chinese`.
   - Do not render until the Chinese-language validation passes.
   - Run `scripts/render_outlook.py <json> --output structured_report_<topic>.html`.
   - The race chart must use `Preclinical → Phase I → Phase II → Phase III → NDA/BLA → Marketed`.
   - Show the report cutoff prominently and emphasize catalyst timing.

4. Export and open.
   - Run `node scripts/export_long_images.mjs <html>`.
   - Keep the JSON and HTML beside the source/work product.
   - Report the downloaded PNG path and any Pixea automation warning.

## Extraction Rules

- Use the opening pages for definition/backdrop, epidemiology, treatment landscape, and major trends.
- Use the ending `R&D Pipeline` pages to create the candidate universe.
- Search the detailed discussion for each candidate to recover mechanism, Cowen view, key data, catalyst, and timing.
- Prefer explicit dates such as `H2:26`, `mid-2026`, `Q1:26`, or `2027`. If timing is absent, use `未明确` rather than inferring it.
- Cite PDF pages, not embedded document page labels.

## Validation

- Confirm 5-6 selected candidates when enough active programs exist.
- Confirm selected candidates are active and have company, product, stage, Cowen evidence, and source pages.
- Confirm every catalyst time is either explicitly sourced or `未明确`.
- Confirm all narrative fields intended for display are written in Simplified Chinese; English is limited to proper nouns and technical abbreviations.
- Confirm the HTML contains all fixed modules and the report cutoff.
- Confirm exported PNG is non-empty and exactly 1080 pixels wide.
