# kc-competitive-analysis

免费层中国同业对标骨架：**AkShare**（A 股三表 + 港股分析指标）+ 东财主营构成 / 巨潮画像。

本仓库是从丽人丽妆美妆电商对标池跑通的可复用骨架，不是交易建议。

## 结构

```
skills/kc-competitive-analysis/  # Skill 配方（KC 占位）
examples/kc-placeholder/            # KC 私有财报 overlay 样例（全 null）
examples/lrlz-beauty-ecom/          # 上市对标池示例报告
data/                               # 拉取结果 JSON
scripts/pull_peers.py               # AkShare 刷新脚本
scripts/render_html.py              # 生成单文件 HTML 看板（stdlib，ECharts CDN）
requirements.txt
```

**不打包 MCP。** 有已安装的行情 MCP 就用；否则直接 `pip install akshare` 跑脚本。KC 数据只走本地 overlay，勿做成对外 MCP。

## 快速开始

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/pull_peers.py --year 2024
python scripts/render_html.py --data data --kc examples/kc-placeholder/kc_financials.sample.json --out examples/lrlz-beauty-ecom/dashboard.html --title "丽人丽妆对标池 2024"
```

**交付物：** 默认是 `skeleton.md` + 单文件 `dashboard.html`（数据内嵌，双击即可打开，可在 Workbuddy 等任意 agent 宿主中使用；离线时图表降级为表格）。Grok Canvas 仅为可选展示面。

默认对标池（可改脚本内 `A_CODES` / `HK_CODES`）：

| 公司 | 代码 |
|---|---|
| 丽人丽妆 | 605136 |
| 若羽臣 | 003010 |
| 壹网壹创 | 300792 |
| 青木科技 | 301110 |
| 水羊股份 | 300740 |
| 宝尊电商-W | 09991.HK |
| 优趣汇控股 | 02177.HK |

示例读数见 [`examples/lrlz-beauty-ecom/skeleton.md`](examples/lrlz-beauty-ecom/skeleton.md)，看板见 [`examples/lrlz-beauty-ecom/dashboard.html`](examples/lrlz-beauty-ecom/dashboard.html)。

## 口径说明

- A 股：资产/营收/归母净利/经营现金流/权益/ROE（平均权益法，视数据源）。
- 港股：`stock_financial_hk_analysis_indicator_em`；OCF 可由 `OCF_SALES × 营收` 估得；总资产/权益需另拉报表项对齐。
- 巨潮公告列表 API 可能偶发失败，年报 MD&A 建议下 PDF 再抽。

## License

MIT
