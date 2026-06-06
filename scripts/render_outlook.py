#!/usr/bin/env python3
"""Render structured TD Cowen Outlook JSON into a self-contained 1080px HTML long image."""

import argparse
import html
import json
import re
import sys
from pathlib import Path

STAGES = ["Preclinical", "Phase I", "Phase II", "Phase III", "NDA/BLA", "Marketed"]
STAGE_ZH = {"Preclinical": "临床前", "Phase I": "I期", "Phase II": "II期", "Phase III": "III期", "NDA/BLA": "申报", "Marketed": "上市"}


def esc(value): return html.escape(str(value or ""))
def pages(value): return "P" + ", ".join(str(x) for x in value or [])
def has_chinese(value): return bool(re.search(r"[\u4e00-\u9fff]", str(value or "")))


def require_chinese(data):
    missing = []
    intro = data.get("disease_intro", {})
    if intro.get("text") and not has_chinese(intro.get("text")):
        missing.append("disease_intro.text")
    for section in ("epidemiology", "treatment_landscape", "key_trends", "risks"):
        for idx, item in enumerate(data.get(section, []), 1):
            text = item.get("text", "") if isinstance(item, dict) else item
            if text and not has_chinese(text):
                missing.append(f"{section}[{idx}].text")
    for idx, candidate in enumerate(data.get("selected_candidates", []), 1):
        for field in ("cowen_view", "catalyst"):
            if candidate.get(field) and not has_chinese(candidate.get(field)):
                missing.append(f"selected_candidates[{idx}].{field}")
        if candidate.get("key_data") and not has_chinese(candidate.get("key_data")):
            missing.append(f"selected_candidates[{idx}].key_data")
    if missing:
        print(json.dumps({
            "error": "Final long-image narrative must be written in Simplified Chinese.",
            "fields_to_translate": missing,
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)


def cards(items, cls="card"):
    out = []
    for item in items:
        if isinstance(item, str):
            text, source = item, []
        else:
            text, source = item.get("text", ""), item.get("source_pages", [])
        out.append(f'<div class="{cls}"><p>{esc(text)}</p><span class="source">{esc(pages(source))}</span></div>')
    return "".join(out) or '<div class="empty">研报未提供明确内容</div>'

def chart_bars(items):
    if not items:
        return ""
    max_by_unit = {}
    for item in items:
        unit = item.get("unit", "")
        value = float(item.get("value") or 0)
        max_by_unit[unit] = max(max_by_unit.get(unit, 0), value)
    rows = []
    for item in items:
        value = float(item.get("value") or 0)
        unit = item.get("unit", "")
        max_value = max_by_unit.get(unit) or value or 1
        width = max(5, min(100, value / max_value * 100))
        rows.append(f'''<div class="bar-row">
          <div class="bar-label">{esc(item.get("label"))}</div>
          <div class="bar-track"><div class="bar-fill" style="width:{width:.1f}%"></div></div>
          <div class="bar-value">{esc(item.get("display") or value)}</div>
          <div class="source">{esc(pages(item.get("source_pages")))}</div>
        </div>''')
    return f'<div class="chart-card">{''.join(rows)}</div>'


def treatment_chart(chart):
    if not chart:
        return ""
    chart_type = chart.get("type", "bars")
    title = chart.get("title", "")
    items = chart.get("items", [])
    if chart_type == "market_share":
        rows = []
        for item in items:
            share = float(item.get("value") or 0)
            rows.append(f'''<div class="share-row">
              <span>{esc(item.get("label"))}</span>
              <div class="share-track"><div class="share-fill" style="width:{max(2,min(100,share)):.1f}%"></div></div>
              <b>{esc(item.get("display") or f"{share:.0f}%")}</b>
            </div>''')
        return f'<div class="chart-card"><h3>{esc(title)}</h3>{''.join(rows)}<span class="source">{esc(pages(chart.get("source_pages")))}</span></div>'
    return chart_bars(items)


def market_cards(records):
    if not records:
        return '<div class="quote none">富途行情：未匹配上市公司</div>'
    parts = []
    for record in records:
        if record.get("error") and not record.get("last_price"):
            parts.append(f'''<div class="quote error"><b>{esc(record.get("company"))}</b><span>{esc(record.get("code"))}</span><em>{esc(record.get("error"))}</em></div>''')
            continue
        ytd = record.get("ytd_change_pct")
        ytd_class = "pos" if isinstance(ytd, (int, float)) and ytd >= 0 else "neg"
        parts.append(f'''<div class="quote">
          <b>{esc(record.get("company"))}</b><span>{esc(record.get("code"))}</span>
          <p>现价 {esc(record.get("last_price_display","暂无有效数据"))}</p>
          <p>市值 {esc(record.get("market_cap_display","暂无有效数据"))}</p>
          <p>YTD <strong class="{ytd_class}">{esc(record.get("ytd_change_display","暂无有效数据"))}</strong></p>
        </div>''')
    return ''.join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()
    source = Path(args.json_file).resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    require_chinese(data)
    report = data["report"]
    candidates = data.get("selected_candidates", [])
    rows = []
    for c in candidates:
        pos = STAGES.index(c["stage"])
        cells = []
        for idx, stage in enumerate(STAGES):
            if idx == pos:
                cells.append(f'''<div class="lane active">
                  <div class="horse"><strong>{esc(c["product"])}</strong><small>{esc(c["company"])}</small></div>
                </div>''')
            else:
                cells.append('<div class="lane"></div>')
        rows.append(f'''<div class="race-row">
          <div class="race-meta"><b>{esc(c["product"])}</b><span>{esc(c["company"])}</span><em>{esc(c.get("mechanism",""))}</em></div>
          <div class="track">{''.join(cells)}</div>
          <div class="catalyst"><span>{esc(c.get("catalyst_time","未明确"))}</span><p>{esc(c.get("catalyst",""))}</p><small>{esc(pages(c.get("source_pages")))}</small><div class="quotes">{market_cards(c.get("market_data", []))}</div></div>
        </div>''')
    trend_items = data.get("key_trends", [])
    risks = data.get("risks", [])
    intro = data.get("disease_intro", {})
    sub = data.get("sub_indications", [])
    html_doc = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>{esc(report["topic"])}</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#0a1623;color:#172536;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",Arial,sans-serif}}
.page{{width:1080px;margin:0 auto;background:#f2f5f7;padding:0 54px 60px}} header{{margin:0 -54px 28px;padding:54px;background:linear-gradient(135deg,#071827,#123c57);color:white;position:relative}}
.eyebrow{{color:#65d4c5;letter-spacing:2px;font-size:14px;font-weight:800}} h1{{font-size:48px;line-height:1.08;margin:15px 0}} .subtitle{{font-size:18px;color:#c9d7df;max-width:800px}}
.cutoff{{position:absolute;right:54px;top:54px;background:#ffca54;color:#322300;padding:12px 16px;border-radius:10px;font-weight:900}} h2{{font-size:27px;margin:30px 0 14px;color:#0d3349}}
.chart-card{{background:white;border-radius:18px;padding:22px;box-shadow:0 7px 24px #14334b14;margin-bottom:14px}} .chart-card h3{{margin:0 0 14px;color:#0d3349;font-size:18px}}
.bar-row{{display:grid;grid-template-columns:210px 1fr 135px 48px;gap:12px;align-items:center;margin:12px 0}} .bar-label{{font-weight:800;color:#153d50}} .bar-track,.share-track{{height:28px;background:#e7eff1;border-radius:999px;overflow:hidden}} .bar-fill,.share-fill{{height:100%;background:linear-gradient(90deg,#20b8a7,#0d746f);border-radius:999px}} .bar-value{{font-weight:900;color:#0d3349;text-align:right}}
.share-row{{display:grid;grid-template-columns:170px 1fr 70px;gap:12px;align-items:center;margin:13px 0}} .share-row span{{font-weight:800;color:#153d50}} .share-row b{{color:#0d3349;text-align:right}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}} .card,.empty{{background:white;border-radius:14px;padding:18px;box-shadow:0 4px 16px #14334b12;border-left:5px solid #3bb7a7;min-height:90px}}
.card p{{margin:0;font-size:16px;line-height:1.55}} .source{{display:block;margin-top:9px;color:#78909c;font-size:12px}} .intro{{font-size:18px;line-height:1.65;background:white;border-radius:16px;padding:22px;border-top:5px solid #ffca54}}
.pillbox{{display:flex;gap:8px;flex-wrap:wrap}} .pill{{background:#d9eceb;color:#164b4d;border-radius:99px;padding:8px 12px;font-weight:700}}
.race{{background:white;border-radius:18px;padding:20px;box-shadow:0 7px 24px #14334b14}} .stage-head,.race-row{{display:grid;grid-template-columns:190px 1fr 310px;gap:12px}}
.stage-head{{margin-bottom:8px}} .stages,.track{{display:grid;grid-template-columns:repeat(6,1fr);gap:3px}} .stages div{{text-align:center;font-size:12px;color:#58727f;font-weight:800}}
.race-row{{padding:14px 0;border-top:1px solid #e4ecef;align-items:center}} .race-meta b{{display:block;font-size:17px;color:#0d3349}} .race-meta span{{display:block;color:#3b6b77;font-weight:700;margin:3px 0}} .race-meta em{{display:block;font-size:11px;color:#80939b;font-style:normal;line-height:1.3}}
.track{{height:64px;background:repeating-linear-gradient(90deg,#eef4f5 0,#eef4f5 calc(16.66% - 3px),white calc(16.66% - 3px),white 16.66%);border-radius:9px;padding:5px}}
.lane{{position:relative;border-right:1px dashed #c3d2d7}} .horse{{position:absolute;left:1px;right:1px;top:8px;background:#0f7f78;color:white;border-radius:8px;padding:7px;text-align:center;box-shadow:0 4px 9px #0f7f7840}}
.horse strong,.horse small{{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} .horse strong{{font-size:11px}} .horse small{{font-size:9px;color:#d9fffa}}
.catalyst span{{display:inline-block;background:#ffca54;color:#3b2d00;border-radius:7px;padding:5px 8px;font-weight:900}} .catalyst p{{font-size:12px;line-height:1.35;margin:6px 0;color:#3c5059}} .catalyst small{{color:#82949c}}
.quotes{{margin-top:8px;display:grid;grid-template-columns:1fr;gap:6px}} .quote{{background:#f1f7f7;border:1px solid #d7e6e8;border-radius:9px;padding:7px;font-size:11px;color:#31515d}} .quote b{{display:inline;color:#0d3349;margin-right:5px}} .quote span{{color:#607d87}} .quote p{{margin:2px 0;font-size:11px;line-height:1.2}} .quote .pos{{color:#09845f}} .quote .neg{{color:#c0392b}} .quote.error em,.quote.none{{color:#8a5a00;font-style:normal}}
.footer{{margin-top:32px;background:#0d3349;color:#d8e3e8;padding:20px;border-radius:14px;font-size:13px;line-height:1.6}} .footer b{{color:#ffca54}}
</style></head><body><main class="page"><header><div class="eyebrow">TD COWEN · THERAPEUTIC CATEGORIES OUTLOOK</div><h1>{esc(report["topic"])}</h1><div class="subtitle">疾病格局、重点管线与关键催化剂赛马图</div><div class="cutoff">研报时点<br>{esc(report["report_date"])}</div></header>
<h2>疾病简介</h2><div class="intro">{esc(intro.get("text",""))}<span class="source">{esc(pages(intro.get("source_pages")))}</span></div>
{f'<h2>主要子适应症</h2><div class="pillbox">{"".join(f"<span class=pill>{esc(x)}</span>" for x in sub)}</div>' if sub else ''}
<h2>流行病学与疾病负担</h2>{chart_bars(data.get("epidemiology_chart", [])) or f'<div class="grid">{cards(data.get("epidemiology", []))}</div>'}
<h2>现有治疗格局</h2>{treatment_chart(data.get("treatment_landscape_chart", {})) or f'<div class="grid">{cards(data.get("treatment_landscape", []))}</div>'}
<h2>TD Cowen 关键趋势</h2><div class="grid">{cards(trend_items)}</div>
<h2>潜力药物赛马图</h2><div class="race"><div class="stage-head"><div></div><div class="stages">{''.join(f'<div>{STAGE_ZH[s]}</div>' for s in STAGES)}</div><div></div></div>{''.join(rows) or '<div class=empty>未筛选出符合规则的活跃管线</div>'}</div>
<h2>关键风险</h2><div class="grid">{cards(risks)}</div>
<div class="footer"><b>口径说明：</b>疾病、治疗格局与Catalyst仅使用 TD Cowen 研报原文，所有研报事件均以 {esc(report["report_date"])} 为信息时点，不联网更新。公司行情来自 Futu OpenAPI 当前快照，与研报时点不同。潜力项目代表 Cowen 重点关注度与明确催化剂，不代表独立成功率判断。<br><b>来源页：</b>{esc(pages(data.get("sources", {}).get("pages")))}</div>
</main></body></html>'''
    output = Path(args.output).resolve() if args.output else source.with_suffix(".html")
    output.write_text(html_doc, encoding="utf-8")
    print(json.dumps({"output": str(output), "width": 1080, "selected_candidates": len(candidates)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
