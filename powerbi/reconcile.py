"""Reconcile the live Power BI model's DAX against the independent pandas answer key.

The DAX side is one query run in Power BI web's DAX query view (see docs/POWERBI_RECONCILIATION.md); its
single-cell result is pasted below as DAX_RESULT. The key side is scripts/answer_key.py's pandas numbers.
Usage: python powerbi/reconcile.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import answer_key as AK  # noqa: E402

DAX_RESULT = ("01=2368187299116173.000000000000|02=2230133956091.000000000000|03=575897453150323.000000000000|"
              "04=19.196581771677|05=0.059875493559|06=0.227750375955|07=0.585139223666|08=0.811364440016|"
              "09=0.647953395100|10=0.288706671683|11=3072.364851388210|12=1355.534346761350|13=0.012072278875|"
              "14=0.396799618842|15=0.978493375689|16=0.602533798278|17=2.025944240637|18=0.677461139393|"
              "19=0.585139223666|20=0.396799618842|21=-1.000000000000|22=33354.000000000000")
DAX_QUERY_RUN = "2026-10-19, semantic model 6922d090-0624-428c-aeda-22f0399d64ea, after a full refresh from GitHub"

CHECKS = [  # (id, label, measure, answer-key name or literal, scale)
    ("01", "Total tokens, all days", "[Total Tokens]", "Total tokens, all days", 1),
    ("02", "Tokens, Jan 2025", "[Total Tokens]", "Tokens, 2025-01", 1),
    ("03", "Tokens, Sep 2026", "[Total Tokens]", "Tokens, 2026-09", 1),
    ("04", "Tokens per day, Sep 2026 (T)", "[Tokens per Day (T)]", "Avg tokens per day, 2026-09", 1e-12),
    ("05", "China token share, Jan 2025", "[China Token Share]", "Token share China, 2025-01", 1),
    ("06", "China token share, Jan 2026", "[China Token Share]", "Token share China, 2026-01", 1),
    ("07", "China token share, Sep 2026", "[China Token Share]", "Token share China, 2026-09", 1),
    ("08", "US token share, Jan 2025", "[US Token Share]", "Token share US, 2025-01", 1),
    ("09", "US token share, Jan 2026", "[US Token Share]", "Token share US, 2026-01", 1),
    ("10", "US token share, Sep 2026", "[US Token Share]", "Token share US, 2026-09", 1),
    ("11", "Lab HHI, Jan 2025", "[Lab HHI]", "HHI lab, 2025-01", 1),
    ("12", "Lab HHI, Sep 2026", "[Lab HHI]", "HHI lab, 2026-09", 1),
    ("13", "China spend share, Jan 2025", "[China Spend Share]", "Spend share China, 2025-01", 1),
    ("14", "China spend share, Sep 2026", "[China Spend Share]", "Spend share China, 2026-09", 1),
    ("15", "US spend share, Jan 2025", "[US Spend Share]", "Spend share US, 2025-01", 1),
    ("16", "US spend share, Sep 2026", "[US Spend Share]", "Spend share US, 2026-09", 1),
    ("17", "Average price paid $/M, Jan 2025", "[Avg Price Paid]", "Average price paid $/M, 2025-01", 1),
    ("18", "Average price paid $/M, Sep 2026", "[Avg Price Paid]", "Average price paid $/M, 2026-09", 1),
    ("19", "China token share, Sep 2026 (monthly fact)", "[Token Share Sep 2026]", "Token share China, 2026-09", 1),
    ("20", "China spend share, Sep 2026 (chart measure)", "[Spend Share Sep 2026]", "Spend share China, 2026-09", 1),
    ("21", "Partial month blanked in the HHI chart", "[Lab HHI (full months)] for Oct 2026", -1, None),
    ("22", "Daily fact rows", "COUNTROWS(fct_model_day)", 33354, None),
]


def main():
    dax = dict(x.split("=") for x in DAX_RESULT.split("|"))
    d, mm = AK.load_key()
    key = AK.key_numbers(d, mm)
    lines = ["# Power BI reconciliation", "",
             f"DAX run: {DAX_QUERY_RUN}. Key: `scripts/answer_key.py` (pandas on the raw pulls).",
             "A row passes when the two agree to 9 significant digits.", "",
             "| # | Check | DAX measure | Live model (DAX) | Answer key | Match |", "|---|---|---|---|---|---|"]
    ok_n = 0
    for i, label, meas, keyname, scale in CHECKS:
        v = float(dax[i])
        k = keyname if scale is None else key[keyname] * scale
        ok = abs(v - k) <= 1e-9 * max(1.0, abs(k))
        ok_n += ok
        lines.append(f"| {i} | {label} | `{meas}` | {v:,.9g} | {k:,.9g} | {'PASS' if ok else 'FAIL'} |")
    lines += ["", f"**{ok_n} of {len(CHECKS)} checks match.** (21: -1 means the measure correctly returns blank for the partial month.)"]
    (ROOT / "docs" / "POWERBI_RECONCILIATION.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0 if ok_n == len(CHECKS) else 1)


if __name__ == "__main__":
    main()
