#!/usr/bin/env python3
"""Refresh peer financials via free AkShare (A-share + HK)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import akshare as ak

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

A_CODES = ["605136", "003010", "300792", "301110", "300740"]
HK_CODES = ["09991", "02177"]


def pull_hk(year: int) -> dict:
    out = {}
    for code in HK_CODES:
        df = ak.stock_financial_hk_analysis_indicator_em(symbol=code, indicator="年度")
        row = df[df["REPORT_DATE"].astype(str).str.startswith(f"{year}-12-31")].iloc[0]
        oi = float(row["OPERATE_INCOME"])
        ocf_sales = float(row["OCF_SALES"]) / 100.0
        out[code] = {
            "name": str(row["SECURITY_NAME_ABBR"]),
            "operate_income": oi,
            "holder_profit": float(row["HOLDER_PROFIT"]),
            "gross_profit_ratio": float(row["GROSS_PROFIT_RATIO"]) / 100.0,
            "roe_avg": float(row["ROE_AVG"]) / 100.0,
            "ocf_est": oi * ocf_sales,
            "ocf_sales": ocf_sales,
            "currency": str(row["CURRENCY"]),
        }
    return out


def pull_a_zygc(year: int) -> dict:
    sym = {
        "605136": "SH605136",
        "003010": "SZ003010",
        "300792": "SZ300792",
        "301110": "SZ301110",
        "300740": "SZ300740",
    }
    names = {
        "605136": "丽人丽妆",
        "003010": "若羽臣",
        "300792": "壹网壹创",
        "301110": "青木科技",
        "300740": "水羊股份",
    }
    target = f"{year}-12-31"
    out = {}
    for code in A_CODES:
        df = ak.stock_zygc_em(symbol=sym[code])
        df = df[df["报告日期"].astype(str).str.startswith(target)]
        segs = []
        for _, r in df.iterrows():
            segs.append(
                {
                    "分类类型": r["分类类型"],
                    "主营构成": r["主营构成"],
                    "主营收入_亿": round(float(r["主营收入"]) / 1e8, 2)
                    if r["主营收入"] == r["主营收入"]
                    else None,
                    "收入比例": round(float(r["收入比例"]), 4)
                    if r["收入比例"] == r["收入比例"]
                    else None,
                    "毛利率": round(float(r["毛利率"]), 4)
                    if r["毛利率"] == r["毛利率"]
                    else None,
                }
            )
        out[code] = {"name": names[code], "period": target, "segments": segs}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2024)
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)

    print("pulling HK indicators…")
    hk = pull_hk(args.year)
    (DATA / "peer_hk_2024.json").write_text(
        json.dumps(hk, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote data/peer_hk_2024.json")

    print("pulling A-share business composition…")
    zygc = pull_a_zygc(args.year)
    (DATA / "peer_zygc_2024.json").write_text(
        json.dumps(zygc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote data/peer_zygc_2024.json")

    print(
        "Note: A-share full compare_peers matrix needs ashare-mcp or "
        "manual Eastmoney/Sina statement pulls; see data/peer_set_2024_a.json snapshot."
    )


if __name__ == "__main__":
    main()
