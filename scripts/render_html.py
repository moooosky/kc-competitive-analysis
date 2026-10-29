#!/usr/bin/env python3
"""Render a single self-contained HTML dashboard from peer JSON + optional KC overlay.

Stdlib only. Never invents numbers: every value shown comes from the input JSON;
missing values render as "—".

Usage:
  python scripts/render_html.py --data data \
      --kc examples/kc-placeholder/kc_financials.sample.json \
      --out examples/lrlz-beauty-ecom/dashboard.html --title "丽人丽妆对标池 2024"
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import os
import sys

ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"


def _load(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:  # bad file -> treat as missing, record note
        print(f"[warn] cannot read {path}: {e}", file=sys.stderr)
        return None


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _bare(code):
    code = str(code or "")
    for p in ("SH", "SZ", "BJ"):
        if code.upper().startswith(p):
            return code[len(p):]
    return code.split(".")[0]


def _pick_file(data_dir, stem, year):
    cand = [f"{stem}_{year}.json"] if year else []
    cand.append(f"{stem}_2024.json")
    for c in cand:
        p = os.path.join(data_dir, c)
        if os.path.exists(p):
            return p
    return None


def build(data_dir, kc_path, year):
    notes, gaps, sources = [], [], []
    rows = []

    p_a = _pick_file(data_dir, "peer_set", year) or os.path.join(data_dir, f"peer_set_{year}_a.json")
    if not os.path.exists(p_a):
        p_a = os.path.join(data_dir, f"peer_set_{year or 2024}_a.json")
    a = _load(p_a)
    p_hk = _pick_file(data_dir, "peer_hk", year)
    hk = _load(p_hk)
    p_m = _pick_file(data_dir, "peer_margins", year)
    margins = _load(p_m)
    p_s = _pick_file(data_dir, "peer_sga", year)
    sga = _load(p_s)
    p_z = _pick_file(data_dir, "peer_zygc", year)
    zygc = _load(p_z)

    for label, p, d in (("A 股三表", p_a, a), ("港股分析指标", p_hk, hk), ("利润率", p_m, margins),
                        ("费用率", p_s, sga), ("主营构成", p_z, zygc)):
        if d is None:
            gaps.append(f"缺少{label}数据文件（{os.path.basename(p) if p else '未找到'}），相关列/板块留空。")
        else:
            sources.append(f"{label}: {os.path.relpath(p, data_dir) if p else '-'}")

    report_date = None
    sga_by = {_bare(x.get("code")): x for x in (sga or []) if isinstance(x, dict)}
    mg_by = {_bare(x.get("code")): x for x in (margins or []) if isinstance(x, dict)}

    if isinstance(a, dict):
        report_date = a.get("report_date")
        year = year or a.get("year")
        for err in a.get("errors") or []:
            gaps.append(f"A 股拉取错误：{err}")
        for c in a.get("companies") or []:
            v = c.get("values") or {}
            code = _bare(c.get("stock_code"))
            roe = _num(v.get("ROE"))
            row = {
                "code": code, "name": c.get("company_name") or code, "market": "A", "currency": "人民币",
                "revenue": _num(v.get("TOTAL_OPERATE_INCOME")), "parent_ni": _num(v.get("PARENT_NETPROFIT")),
                "ocf": _num(v.get("NETCASH_OPERATE")), "ocf_est": False,
                "assets": _num(v.get("TOTAL_ASSETS")), "equity": _num(v.get("TOTAL_EQUITY")),
                "roe": roe * 100 if roe is not None else None,
                "gross_margin": None, "gm_est": False, "sell_rate": None, "admin_rate": None, "sga_rate": None,
                "net_margin": None, "flags": [],
            }
            if c.get("fallbacks"):
                row["flags"].append(f"字段回退：{c.get('fallbacks')}")
                gaps.append(f"{row['name']} 部分字段使用回退口径：{c.get('fallbacks')}")
            if c.get("roe_method"):
                row["roe_method"] = c.get("roe_method")
            s = sga_by.get(code)
            if s:
                row["gross_margin"] = _num(s.get("gross_margin_pct"))
                row["sell_rate"] = _num(s.get("sell_rate_pct"))
                row["admin_rate"] = _num(s.get("admin_rate_pct"))
                if row["sell_rate"] is not None and row["admin_rate"] is not None:
                    row["sga_rate"] = round(row["sell_rate"] + row["admin_rate"], 2)
            m = mg_by.get(code)
            if m:
                row["net_margin"] = _num(m.get("销售净利率(%)"))
                if row["gross_margin"] is None:
                    gm = _num(m.get("销售毛利率(%)"))
                    if gm is None:
                        gm = _num(m.get("毛利率_估_100减成本率"))
                        row["gm_est"] = gm is not None
                    row["gross_margin"] = gm
            rows.append(row)

    if isinstance(hk, dict):
        for code, h in hk.items():
            if not isinstance(h, dict):
                continue
            gm, roe = _num(h.get("gross_profit_ratio")), _num(h.get("roe_avg"))
            ocf = _num(h.get("ocf_est"))
            rows.append({
                "code": f"{code}.HK", "name": h.get("name") or code, "market": "HK",
                "currency": h.get("currency") or "未注明",
                "revenue": _num(h.get("operate_income")), "parent_ni": _num(h.get("holder_profit")),
                "ocf": ocf, "ocf_est": ocf is not None, "assets": None, "equity": None,
                "roe": roe * 100 if roe is not None else None,
                "gross_margin": gm * 100 if gm is not None else None, "gm_est": False,
                "sell_rate": None, "admin_rate": None, "sga_rate": None, "net_margin": None,
                "flags": ["港股分析指标口径", "OCF=OCF/营收×营收 估算"],
            })
        if hk:
            notes.append("港股行（标 HK）来自 stock_financial_hk_analysis_indicator_em：经营现金流为 OCF/营收 × 营收 估算；"
                         "总资产/净资产未与 A 股三表逐项对齐，暂缺；货币见各行“币种”。")
            gaps.append("港股总资产/净资产未拉取，需另拉港股资产负债表对齐。")
            notes.append("港股毛利率为数据源 gross_profit_ratio，收入结构（如服务收入占比）与 A 股不同，横向比较需谨慎。")

    # KC overlay
    kc_row, kc_status = None, "未提供 KC overlay"
    kc = _load(kc_path) if kc_path else None
    if kc_path and kc is None:
        gaps.append(f"KC overlay 文件无法读取：{kc_path}")
    if isinstance(kc, dict):
        periods = kc.get("periods") or []
        per = next((p for p in periods if str(p.get("year")) == str(year)), periods[0] if periods else {})
        fields = {"revenue": "revenue", "parent_ni": "parent_net_profit", "ocf": "operating_cash_flow",
                  "assets": "total_assets", "equity": "total_equity", "gross_margin": "gross_margin_pct",
                  "sell_rate": "sell_expense_rate_pct", "admin_rate": "admin_expense_rate_pct", "roe": "roe_pct"}
        vals = {k: _num(per.get(src)) for k, src in fields.items()}
        missing = [src for k, src in fields.items() if vals[k] is None and src != "roe_pct"]
        if any(v is not None for v in vals.values()):
            sga_rate = (round(vals["sell_rate"] + vals["admin_rate"], 2)
                        if vals["sell_rate"] is not None and vals["admin_rate"] is not None else None)
            kc_row = {"code": "KC", "name": kc.get("company") or "KC", "market": "KC",
                      "currency": kc.get("currency") or "未注明", "ocf_est": False, "gm_est": False,
                      "sga_rate": sga_rate, "net_margin": None, "flags": ["私有 overlay，非公开数据"], **vals}
            rows.insert(0, kc_row)
            kc_status = f"KC overlay 已载入（{per.get('year', '?')}）"
            if missing:
                gaps.append("KC overlay 缺字段：" + "、".join(missing))
            notes.append("KC 行来自本地私有 overlay，ROE 仅在 overlay 提供 roe_pct 时显示（不自行推算）。勿对外发布。")
        else:
            kc_status = "KC overlay 全为 null（占位样例），矩阵不显示 KC 行"
            gaps.append("KC overlay 全为 null：填入 KC 合并口径数据（与同业同单位，元）后重跑本脚本。")

    if any(r.get("gm_est") for r in rows):
        notes.append("毛利率带 ≈ 的行：源数据“销售毛利率”为空，按 100 − 主营业务成本率 估算。")
    if sga_by:
        notes.append("销管费用率 = 销售费用率 + 管理费用率（不含研发、财务费用），来自利润表费用 / 营业总收入。")
    if any(r.get("roe_method") == "avg_equity" for r in rows):
        notes.append("A 股 ROE 为归母净利 / 平均归母权益；港股 ROE 为数据源 roe_avg（平均权益法）。")
    notes.append("金额单位：亿元（原始数据单位为元，展示时 ÷1e8）；比率单位 %。")

    segs = {}
    if isinstance(zygc, dict):
        for code, z in zygc.items():
            if not isinstance(z, dict):
                continue
            groups = {}
            for s in z.get("segments") or []:
                groups.setdefault(s.get("分类类型") or "其他", []).append({
                    "name": s.get("主营构成"), "rev_yi": _num(s.get("主营收入_亿")),
                    "share": _num(s.get("收入比例")), "gm": _num(s.get("毛利率")),
                })
            for g in groups.values():
                g.sort(key=lambda x: -(x["share"] or 0))
            segs[_bare(code)] = {"name": z.get("name") or code, "period": z.get("period"), "groups": groups}

    return {
        "year": year, "report_date": report_date, "rows": rows, "segments": segs,
        "notes": notes, "gaps": gaps, "sources": sources, "kc_status": kc_status,
        "has_hk": any(r["market"] == "HK" for r in rows),
        "generated": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1f2328;--mute:#6b7280;--line:#e5e7eb;--acc:#2f5d8a;--neg:#b42318;--pos:#067647;--hk:#8a5a00}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:24px 20px 48px}
h1{font-size:22px;margin:0 0 4px}
h2{font-size:16px;margin:28px 0 10px;padding-left:8px;border-left:3px solid var(--acc)}
.sub{color:var(--mute);font-size:12.5px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px;margin-top:16px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .l{color:var(--mute);font-size:12px}.kpi .v{font-size:20px;font-weight:600;margin-top:2px}.kpi .d{color:var(--mute);font-size:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:0 0 10px}
.bar label{font-size:13px;color:var(--mute)}
select,button{font:inherit;padding:4px 8px;border:1px solid var(--line);border-radius:6px;background:#fff}
.tog{display:inline-flex;gap:6px;align-items:center;cursor:pointer;user-select:none}
.tablewrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:#fafbfc;text-align:right;cursor:pointer;position:sticky;top:0;font-weight:600}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
td{text-align:right;font-variant-numeric:tabular-nums}
th.sorted-asc::after{content:" ▲";font-size:10px}th.sorted-desc::after{content:" ▼";font-size:10px}
tr.hk td{background:#fffaf0}tr.kc td{background:#eef4fb;font-weight:600}
.neg{color:var(--neg)}.tag{display:inline-block;font-size:11px;padding:0 5px;border-radius:4px;margin-left:4px;border:1px solid var(--line);color:var(--mute)}
.tag.hk{color:var(--hk);border-color:#f0d9a8}.tag.kc{color:var(--acc);border-color:#bcd0e6}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:860px){.grid2{grid-template-columns:1fr}}
.chart{height:340px}
.fallback{display:none;color:var(--mute);font-size:13px;padding:10px;border:1px dashed var(--line);border-radius:8px}
.segs{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.seg h3{font-size:14px;margin:0 0 6px}.seg .g{font-size:12px;color:var(--mute);margin-top:6px}
.seg ul{margin:2px 0 0;padding-left:18px;font-size:12.5px}
.notes li{margin:3px 0;font-size:13px}
footer{margin-top:30px;color:var(--mute);font-size:12px}
</style>
</head>
<body>
<div class="wrap">
  <h1>__TITLE__</h1>
  <div class="sub" id="meta"></div>
  <div class="kpis" id="kpis"></div>

  <h2>财务矩阵</h2>
  <div class="card">
    <div class="bar">
      <label class="tog"><input type="checkbox" id="incHK" checked> 包含港股</label>
      <span class="sub">点击表头排序；<span class="tag hk">HK</span> 行为港股分析指标口径，<span class="tag">估</span> 为估算值。金额单位：亿元。</span>
    </div>
    <div class="tablewrap"><table id="matrix"><thead></thead><tbody></tbody></table></div>
  </div>

  <h2>图表</h2>
  <div class="fallback" id="nochart">图表库（ECharts CDN）未能加载，可能处于离线环境；以上表格数据完整可用。</div>
  <div class="grid2" id="charts">
    <div class="card">
      <div class="bar"><label>指标</label><select id="metric"></select></div>
      <div class="chart" id="barChart"></div>
    </div>
    <div class="card">
      <div class="bar"><label>营收（亿元）× ROE（%）</label></div>
      <div class="chart" id="scatter"></div>
    </div>
  </div>

  <div id="segWrap">
    <h2>主营构成速览</h2>
    <div class="segs" id="segs"></div>
  </div>

  <h2>口径说明与缺口</h2>
  <div class="card notes">
    <b>口径</b><ul id="notes"></ul>
    <b>缺口 / 下一步</b><ul id="gaps"></ul>
    <b>数据来源</b><ul id="sources"></ul>
  </div>
  <footer id="foot"></footer>
</div>

<script id="dash-data" type="application/json">__DATA__</script>
<script>
(function(){
const D = JSON.parse(document.getElementById('dash-data').textContent);
const COLS = [
  {k:'name', t:'公司', fmt:'name'},
  {k:'code', t:'代码', fmt:'str'},
  {k:'revenue', t:'营收', fmt:'yi'},
  {k:'parent_ni', t:'归母净利', fmt:'yi'},
  {k:'ocf', t:'经营现金流', fmt:'yi'},
  {k:'assets', t:'总资产', fmt:'yi'},
  {k:'equity', t:'净资产', fmt:'yi'},
  {k:'roe', t:'ROE', fmt:'pct'},
  {k:'gross_margin', t:'毛利率', fmt:'pct'},
  {k:'sga_rate', t:'销管费用率', fmt:'pct'},
  {k:'sell_rate', t:'销售费用率', fmt:'pct'},
  {k:'net_margin', t:'净利率', fmt:'pct'},
  {k:'currency', t:'币种', fmt:'str'}
];
const METRICS = COLS.filter(c => c.fmt==='yi' || c.fmt==='pct').filter(c => D.rows.some(r => r[c.k]!=null));
const DASH = '—';
const isNum = v => typeof v === 'number' && isFinite(v);
function fmtVal(r, c){
  const v = r[c.k];
  if (c.fmt==='name'){
    let s = esc(v);
    if (r.market==='HK') s += '<span class="tag hk">HK</span>';
    if (r.market==='KC') s += '<span class="tag kc">KC</span>';
    return s;
  }
  if (c.fmt==='str') return v==null||v==='' ? DASH : esc(v);
  if (!isNum(v)) return DASH;
  let s = c.fmt==='yi' ? (v/1e8).toFixed(2) : v.toFixed(1)+'%';
  if ((c.k==='ocf' && r.ocf_est) || (c.k==='gross_margin' && r.gm_est)) s = '≈'+s+'<span class="tag">估</span>';
  return v<0 ? '<span class="neg">'+s+'</span>' : s;
}
function esc(s){return String(s).replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]));}
let sortKey = 'revenue', sortDir = -1;
const incHK = document.getElementById('incHK');
if (!D.has_hk) incHK.parentElement.style.display = 'none';
function visRows(){ return D.rows.filter(r => incHK.checked || r.market!=='HK'); }

function renderTable(){
  const thead = document.querySelector('#matrix thead'), tbody = document.querySelector('#matrix tbody');
  const cols = COLS.filter(c => c.fmt!=='yi' && c.fmt!=='pct' || D.rows.some(r => r[c.k]!=null));
  thead.innerHTML = '<tr>' + cols.map(c => '<th data-k="'+c.k+'" class="'+(c.k===sortKey?(sortDir>0?'sorted-asc':'sorted-desc'):'')+'">'+c.t+'</th>').join('') + '</tr>';
  const rows = visRows().slice().sort((a,b) => {
    if (a.market==='KC' && b.market!=='KC') return -1; if (b.market==='KC' && a.market!=='KC') return 1;
    const x=a[sortKey], y=b[sortKey];
    if (x==null && y==null) return 0; if (x==null) return 1; if (y==null) return -1;
    return (typeof x==='number' ? x-y : String(x).localeCompare(String(y),'zh')) * sortDir;
  });
  tbody.innerHTML = rows.map(r => '<tr class="'+(r.market==='HK'?'hk':r.market==='KC'?'kc':'')+'" title="'+esc((r.flags||[]).join('；'))+'">' +
    cols.map(c => '<td>'+fmtVal(r,c)+'</td>').join('') + '</tr>').join('');
  thead.querySelectorAll('th').forEach(th => th.onclick = () => {
    const k = th.dataset.k; if (k===sortKey) sortDir = -sortDir; else { sortKey = k; sortDir = -1; } renderTable();
  });
}

function median(a){ if(!a.length) return null; const s=a.slice().sort((x,y)=>x-y), m=s.length>>1; return s.length%2?s[m]:(s[m-1]+s[m])/2; }
function renderKPIs(){
  const rows = visRows().filter(r => r.market!=='KC');
  const vals = k => rows.map(r => r[k]).filter(isNum);
  const top = (k, dir) => { const rs = rows.filter(r => isNum(r[k])); if(!rs.length) return null; return rs.reduce((a,b) => (b[k]-a[k])*dir>0?b:a); };
  const rev = vals('revenue'), roe = vals('roe'), gm = vals('gross_margin'), sga = vals('sga_rate');
  const tRev = top('revenue',1), tRoe = top('roe',1), lossN = rows.filter(r => isNum(r.parent_ni) && r.parent_ni<0).length;
  const cards = [
    ['对标公司数', rows.length+' 家', (D.has_hk ? (incHK.checked?'含港股':'仅 A 股') : '仅 A 股') + (D.rows.some(r=>r.market==='KC')?'（不含 KC）':'')],
    ['营收中位数', rev.length ? (median(rev)/1e8).toFixed(2)+' 亿' : DASH, tRev ? '最高：'+tRev.name+' '+(tRev.revenue/1e8).toFixed(2)+' 亿' : ''],
    ['ROE 中位数', roe.length ? median(roe).toFixed(1)+'%' : DASH, tRoe ? '最高：'+tRoe.name+' '+tRoe.roe.toFixed(1)+'%' : ''],
    ['毛利率中位数', gm.length ? median(gm).toFixed(1)+'%' : DASH, gm.length+' 家有数据'],
    ['销管费用率中位数', sga.length ? median(sga).toFixed(1)+'%' : DASH, sga.length ? sga.length+' 家有数据（仅 A 股）' : '无费用率数据'],
    ['归母亏损家数', lossN+' 家', '归母净利 < 0'],
    ['KC 状态', D.rows.some(r=>r.market==='KC') ? '已载入' : '未载入', D.kc_status]
  ];
  document.getElementById('kpis').innerHTML = cards.map(c => '<div class="kpi"><div class="l">'+c[0]+'</div><div class="v">'+c[1]+'</div><div class="d">'+esc(c[2])+'</div></div>').join('');
}

let barC = null, scC = null;
const metricSel = document.getElementById('metric');
metricSel.innerHTML = METRICS.map(c => '<option value="'+c.k+'">'+c.t+(c.fmt==='yi'?'（亿元）':'（%）')+'</option>').join('');
function renderCharts(){
  if (!window.echarts) return;
  const c = METRICS.find(m => m.k===metricSel.value) || METRICS[0];
  if (!c) return;
  const rs = visRows().filter(r => isNum(r[c.k])).sort((a,b) => b[c.k]-a[c.k]);
  const val = r => c.fmt==='yi' ? +(r[c.k]/1e8).toFixed(2) : +r[c.k].toFixed(2);
  const color = r => r.market==='KC' ? '#2f5d8a' : r.market==='HK' ? '#d9a441' : '#7b97b5';
  barC = barC || echarts.init(document.getElementById('barChart'));
  barC.setOption({
    grid:{left:60,right:16,top:20,bottom:60},
    tooltip:{trigger:'axis',formatter:p => p[0].name+'<br>'+c.t+'：'+p[0].value+(c.fmt==='yi'?' 亿':'%')+(((c.k==='ocf'&&rs[p[0].dataIndex].ocf_est)||(c.k==='gross_margin'&&rs[p[0].dataIndex].gm_est))?'（估）':'')},
    xAxis:{type:'category',data:rs.map(r => r.name),axisLabel:{interval:0,rotate:rs.length>6?30:0}},
    yAxis:{type:'value',axisLabel:{formatter:v => c.fmt==='pct'?v+'%':v}},
    series:[{type:'bar',data:rs.map(r => ({value:val(r),itemStyle:{color:color(r)}})),label:{show:true,position:'top',fontSize:11}}]
  }, true);
  const ps = visRows().filter(r => isNum(r.revenue) && isNum(r.roe));
  scC = scC || echarts.init(document.getElementById('scatter'));
  scC.setOption({
    grid:{left:60,right:24,top:34,bottom:50},
    tooltip:{formatter:p => p.data[2]+'<br>营收 '+p.data[0]+' 亿<br>ROE '+p.data[1]+'%'},
    xAxis:{type:'log',name:'营收（亿元，对数）',nameLocation:'middle',nameGap:30,scale:true},
    yAxis:{type:'value',name:'ROE %',axisLabel:{formatter:'{value}%'}},
    series:[{type:'scatter',symbolSize:14,
      data:ps.map(r => ({value:[+(r.revenue/1e8).toFixed(2), +r.roe.toFixed(2), r.name], itemStyle:{color:color(r)}})),
      label:{show:true,formatter:p => p.data.value[2],position:'right',fontSize:11},
      markLine:{silent:true,symbol:'none',lineStyle:{type:'dashed',color:'#999'},data:[{yAxis:0}]}}]
  }, true);
}
function renderSegs(){
  const keys = Object.keys(D.segments||{});
  if (!keys.length){ document.getElementById('segWrap').style.display='none'; return; }
  const pct = v => isNum(v) ? (v*100).toFixed(0)+'%' : DASH;
  document.getElementById('segs').innerHTML = keys.map(code => {
    const s = D.segments[code];
    const gs = Object.keys(s.groups).map(g => '<div class="g">'+esc(g)+'</div><ul>' +
      s.groups[g].slice(0,4).map(x => '<li>'+esc(x.name)+'：'+pct(x.share)+(isNum(x.gm)?'（毛利 '+pct(x.gm)+'）':'')+(isNum(x.rev_yi)?' · '+x.rev_yi.toFixed(2)+' 亿':'')+'</li>').join('') +
      (s.groups[g].length>4 ? '<li>…另 '+(s.groups[g].length-4)+' 项</li>' : '') + '</ul>').join('');
    return '<div class="card seg"><h3>'+esc(s.name)+' <span class="sub">'+esc(code)+' · '+esc(s.period||'')+'</span></h3>'+gs+'</div>';
  }).join('');
}
function list(id, arr){ document.getElementById(id).innerHTML = (arr&&arr.length ? arr : ['无']).map(x => '<li>'+esc(x)+'</li>').join(''); }

document.getElementById('meta').textContent = '报告期：'+(D.report_date || D.year || DASH)+' · 数据：AkShare（东财/巨潮）免费层 · 仅供研究，非投资建议';
document.getElementById('foot').textContent = '生成于 '+D.generated+' · scripts/render_html.py · 以 data/ 与 overlay 为准，本页仅为展示';
list('notes', D.notes); list('gaps', D.gaps); list('sources', D.sources);
function all(){ renderKPIs(); renderTable(); renderCharts(); }
incHK.onchange = all; metricSel.onchange = renderCharts;
renderSegs(); all();

function noCharts(){ document.getElementById('charts').style.display='none'; document.getElementById('nochart').style.display='block'; }
if (!window.echarts){
  const s = document.createElement('script'); s.src = '__ECHARTS__';
  s.onload = () => { renderCharts(); window.addEventListener('resize', () => { barC&&barC.resize(); scC&&scC.resize(); }); };
  s.onerror = noCharts;
  document.head.appendChild(s);
  setTimeout(() => { if (!window.echarts) noCharts(); }, 8000);
}
})();
</script>
</body>
</html>
"""


def render(payload, title):
    data = json.dumps(payload, ensure_ascii=False, indent=1)
    data = data.replace("</", "<\\/")  # keep </script> out of the JSON block
    return (TEMPLATE.replace("__TITLE__", html.escape(title))
            .replace("__ECHARTS__", ECHARTS_CDN)
            .replace("__DATA__", data))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render self-contained HTML peer dashboard")
    ap.add_argument("--data", default="data", help="dir with peer_*.json")
    ap.add_argument("--kc", default=None, help="KC overlay JSON (optional)")
    ap.add_argument("--out", required=True, help="output .html path")
    ap.add_argument("--title", default="KC 同业对标")
    ap.add_argument("--year", type=int, default=None, help="fiscal year (default: from data)")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.data):
        ap.error(f"--data dir not found: {a.data}")
    payload = build(a.data, a.kc, a.year)
    if not payload["rows"]:
        print("[warn] no peer rows found; dashboard will only show notes/gaps", file=sys.stderr)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(render(payload, a.title))
    print(f"wrote {a.out}  rows={len(payload['rows'])}  kc={payload['kc_status']}")


if __name__ == "__main__":
    main()
