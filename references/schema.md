# Structured Outlook JSON Schema

The extractor creates a JSON draft. Preserve its factual evidence and complete the Chinese editorial fields before rendering.

## Language Policy

- The final long image must be in Simplified Chinese.
- Translate/rewrite all displayed narrative fields before rendering.
- Required Chinese narrative fields: `disease_intro.text`, every item in `epidemiology`, `treatment_landscape`, `key_trends`, and `risks`, plus candidate `cowen_view`, `key_data`, and `catalyst`.
- Keep drug names, company names, trial names, mechanisms such as `GLP-1`/`anti-Tau mAb`, regulatory abbreviations such as `FDA`/`NDA`/`BLA`, and catalyst timings such as `H2:26` in English.
- The extractor's English text is evidence-bearing draft material, not final display copy.

## Top Level

- `report`: title, topic, report date, page count, input path, TD Cowen detection, and section page ranges.
- `disease_intro`: short Chinese overview with `text` and `source_pages`.
- `epidemiology`: 2-4 high-signal burden/prevalence/incidence facts. Each item has `text` and `source_pages`.
- `epidemiology_chart`: optional bar-chart data for epidemiology or disease-burden metrics. Each item has `label`, `value`, `unit`, `display`, and `source_pages`.
- `treatment_landscape`: current standard of care, approved disease-modifying options, and major limitations.
- `treatment_landscape_chart`: optional chart data for market size, market share, standard-of-care split, or adoption assumptions. Use `type` plus `items`.
- `sub_indications`: major sub-indications for broad category reports; otherwise empty.
- `key_trends`: 3-5 Cowen trends, each with `text` and `source_pages`.
- `pipeline_candidates`: deterministic candidate universe extracted from the R&D Pipeline and body.
- `selected_candidates`: 5-6 candidates copied from `pipeline_candidates` and editorially refined.
- `risks`: 2-4 report-supported scientific, clinical, regulatory, access, or commercial risks.
- `sources`: source note and relevant page list.

## Candidate

Required:

- `company`
- `product`
- `stage`: one of `Preclinical`, `Phase I`, `Phase II`, `Phase III`, `NDA/BLA`, `Marketed`
- `mechanism`
- `cowen_view`: concise report-supported assessment, not an independent opinion
- `catalyst`
- `catalyst_time`: explicit report wording or `未明确`
- `source_pages`: PDF page numbers supporting the candidate
- `active`: boolean
- `market_data`: optional list of Futu quote records for public companies associated with the drug. Each record has `company`, `code`, `quote_source`, `quote_time`, `last_price`, `currency`, `market_cap`, `market_cap_display`, `ytd_change_pct`, and optional `error`.

Optional:

- `indication`
- `key_data`
- `pipeline_comment`
- `body_excerpt`
- `selection_score`: deterministic extraction aid only; never display as success probability

## Evidence Policy

- Never remove source pages when shortening prose.
- Never convert a vague date into a precise date.
- Never treat a historical event before the report date as the next catalyst.
- Do not select candidates whose evidence says discontinued, halted, failed, withdrawn, terminated, or deprioritized.
- Keep report-derived data and current Futu quote data separate. Quote data should show its own `quote_time` and source label.
