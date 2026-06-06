# TD Cowen研报结构化skill

一个面向 Codex 的公开 Skill，用于将 TD Cowen / TD Securities `Therapeutic Categories Outlook` 系列 PDF 结构化为中文治疗格局长图。

## Description

拖入一篇 TD Cowen `Therapeutic Categories Outlook` 报告后，Skill 会识别疾病或治疗类别、报告时点与核心章节，提取疾病简介、流行病学、现有治疗格局、Cowen 关键观点、R&D Pipeline、重点药物及 Catalyst，并生成按临床阶段排列的赛马图。

最终输出包括：

- 简体中文研究长图
- 可复核的结构化 JSON
- 自包含 HTML
- `1080px` 宽 PNG
- 药物、公司、临床阶段、Catalyst 时间与 PDF 来源页

Skill 严格采用研报发布时点的信息，不联网更新事件，也不会生成主观成功率评分。

## 能力边界

- 适用于 TD Cowen / TD Securities `Therapeutic Categories Outlook` 系列疾病、治疗类别及多适应症报告。
- 不适用于普通单公司研报。
- 最终叙述内容强制使用简体中文；公司名、药物名、试验名、机制缩写与时间表达可保留英文。
- 默认精选 5–6 个活跃重点项目，并排除已终止、失败、撤回或被降级的项目。
- 所有关键事实均保留 PDF 来源页，便于人工复核。

## 安装

使用 Codex Skill 安装器从 GitHub 安装：

```text
Install the skill from https://github.com/pfli1993-ship-it/td-cowen-research-structuring-skill
```

或克隆到个人 Skills 目录：

```bash
git clone https://github.com/pfli1993-ship-it/td-cowen-research-structuring-skill \
  ~/.codex/skills/structure-td-cowen-therapeutic-outlook
```

## 使用

在 Codex 中拖入 PDF，并使用：

```text
使用 $structure-td-cowen-therapeutic-outlook 将这篇 TD Cowen Therapeutic Categories Outlook 研报制作成中文长图。
```

Skill 的标准流程为：

1. 从 PDF 提取结构化草稿。
2. 基于研报证据完成中文编辑与重点项目筛选。
3. 校验中文、阶段、Catalyst 和来源页。
4. 生成 HTML 并导出 PNG。

## 依赖

- Python 3.10+
- [`pypdf`](https://pypi.org/project/pypdf/)
- [`futu-api`](https://pypi.org/project/futu-api/) 与正在运行的 Futu OpenD（用于可选公司行情模块）
- Node.js 18+
- Playwright，或 Codex bundled runtime 中的 Playwright
- Chrome 或 Playwright 可用浏览器

Pixea 为可选依赖。macOS 安装 Pixea 后，导出脚本会尝试自动打开生成的 PNG。

安装运行依赖：

```bash
python3 -m pip install -r requirements.txt
npm install
npx playwright install chromium
```

## 核心命令

```bash
python3 scripts/extract_outlook.py report.pdf --output report.json
python3 scripts/fetch_futu_market_data.py 'Biogen=US.BIIB' 'Acadia=US.ACAD' --output futu_market_data.json
python3 scripts/validate_outlook.py report.json --require-chinese
python3 scripts/render_outlook.py report.json --output structured_report.html
node scripts/export_long_images.mjs structured_report.html
```

## Disclaimer

本项目仅用于研究资料结构化和信息展示，不构成投资、医疗或交易建议。使用者应确保其拥有处理相关研报的合法权限；仓库不包含任何 TD Cowen 研报原文或受版权保护的报告内容。
