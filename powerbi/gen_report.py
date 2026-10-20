"""The 5-page Power BI report as code: writes a PBIR definition to powerbi/report/.

    python powerbi/gen_report.py [--model-id <semantic model id>]

Adapted from Ajay0704/ecommerce-powerbi (powerbi/gen_report.py). Published with the Fabric REST API
(Items - Create Report) from a signed-in app.powerbi.com tab, bound to the semantic model by id.
Titles, KPI tiles and notes are imported from tableau/make_workbook.py, so the Power BI report, the
Tableau story and the approved mockup use identical, verified wording.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
OUT = HERE / "report"
sys.path.insert(0, str(ROOT / "tableau"))
import make_workbook as TW  # noqa: E402  (titles, KPI tiles and notes)

MODEL_NAME = "AI Model Market"
W, H, G = 1280, 1000, 16
HALF = (W - 3 * G) // 2
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
THEME_NAME = "AIModelMarket.json"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#6f6d67"
PLANE, SURFACE, BORDER, GRID = "#f9f9f7", "#fcfcfb", "#e1e0d9", "#e1e0d9"
CHINA, US, GRAY, ACCENT = "#2a78d6", "#eb6834", "#898781", "#6250d6"

THEME = {
    "name": "AI Model Market",
    "dataColors": [CHINA, US, GRAY, ACCENT, "#1baf7a", "#eda100", "#e87ba4", "#008300"],
    "background": SURFACE, "foreground": INK, "tableAccent": ACCENT,
    "textClasses": {
        "title": {"fontFace": "Segoe UI Semibold", "fontSize": 11, "color": INK},
        "label": {"fontFace": "Segoe UI", "fontSize": 9, "color": INK2},
        "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 20, "color": INK},
        "header": {"fontFace": "Segoe UI Semibold", "fontSize": 10, "color": INK},
    },
    "visualStyles": {
        "page": {"*": {"background": [{"color": {"solid": {"color": PLANE}}, "transparency": 0}]}},
        "*": {"*": {
            "background": [{"show": True, "color": {"solid": {"color": SURFACE}}, "transparency": 0}],
            "border": [{"show": True, "color": {"solid": {"color": BORDER}}, "radius": 10}],
            "padding": [{"top": 12, "bottom": 10, "left": 14, "right": 14}],
            "title": [{"fontColor": {"solid": {"color": INK}}, "fontFamily": "Segoe UI Semibold", "fontSize": 11, "alignment": "left"}],
            "subTitle": [{"fontColor": {"solid": {"color": MUTED}}, "fontFamily": "Segoe UI", "fontSize": 8}],
            "valueAxis": [{"gridlineShow": True, "gridlineColor": {"solid": {"color": GRID}}, "gridlineStyle": "solid",
                           "gridlineThickness": 1, "labelColor": {"solid": {"color": INK2}}, "fontSize": 8, "showAxisTitle": False}],
            "categoryAxis": [{"gridlineShow": False, "labelColor": {"solid": {"color": INK2}}, "fontSize": 8, "showAxisTitle": False}],
            "legend": [{"show": True, "position": "TopLeft", "labelColor": {"solid": {"color": INK2}}, "fontSize": 8, "showTitle": False}],
            "labels": [{"color": {"solid": {"color": INK}}, "fontSize": 8}],
        }},
        "lineChart": {"*": {"lineStyles": [{"strokeWidth": 2, "showMarker": False}]}},
        "textbox": {"*": {"background": [{"show": False}], "border": [{"show": False}]}},
    },
}


def lit(v) -> dict:
    return {"expr": {"Literal": {"Value": v}}}


def s(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def M(entity: str, prop: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def C(entity: str, prop: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def A(entity: str, prop: str, fn: int = 0) -> dict:
    """An aggregated column (0 = Sum)."""
    return {"Aggregation": {"Expression": C(entity, prop), "Function": fn}}


def ref(field: dict) -> tuple[str, str]:
    if "Aggregation" in field:
        e = field["Aggregation"]["Expression"]["Column"]
        fn = {0: "Sum"}.get(field["Aggregation"]["Function"], "Agg")
        return f"{fn}({e['Expression']['SourceRef']['Entity']}.{e['Property']})", e["Property"]
    kind = "Measure" if "Measure" in field else "Column"
    return f"{field[kind]['Expression']['SourceRef']['Entity']}.{field[kind]['Property']}", field[kind]["Property"]


def proj(field: dict, name: str | None = None, active: bool = True) -> dict:
    q, native = ref(field)
    out = {"field": field, "queryRef": q, "nativeQueryRef": native}
    if "Column" in field and active:
        out["active"] = True
    if name:
        out["displayName"] = name
    return out


def color(hexv: str) -> dict:
    return {"solid": {"color": lit(s(hexv))}}


def by_value(col: dict, mapping: dict[str, str]) -> list[dict]:
    """dataPoint colours keyed by a series column's values: colour follows the entity, never its rank."""
    return [{"properties": {"fill": color(c)},
             "selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": col, "Right": {"Literal": {"Value": s(v)}}}}}]}}
            for v, c in mapping.items()]


def by_measure(mapping: dict[str, str]) -> list[dict]:
    return [{"properties": {"fill": color(c)}, "selector": {"metadata": qref}} for qref, c in mapping.items()]


def single(c: str) -> list[dict]:
    return [{"properties": {"fill": color(c)}}]


SHEETS = {sh.name: sh for sh in TW.sheets()}


def headings(sheet: str) -> dict:
    sh = SHEETS[sheet]
    return {"title": [{"properties": {"show": lit("true"), "text": lit(s(sh.title))}}],
            "subTitle": [{"properties": {"show": lit("true"), "text": lit(s(sh.subtitle))}}]}


class Page:
    def __init__(self, tab: str, height: int = H):
        self.name = tab.split(" · ", 1)[1]
        self.id = hashlib.sha1(tab.encode()).hexdigest()[:20]
        self.visuals, self.z, self.height = [], 0, height
        rows = next(r for n, _, r in TW.PAGES if n == tab)
        head = [t.strip() for t, _ in rows[0][1][0][1]]
        self.text((G, 8, W - 2 * G, 84), [(head[0], 9, MUTED, False), (head[1], 18, INK, True), (head[2], 10, INK2, False)])
        kw = (W - 2 * G - 3 * G) // 4
        for i, (_, runs, _) in enumerate(rows[1][1]):
            label, value, delta = [t.strip() for t, _ in runs]
            self.text((G + i * (kw + G), 100, kw, 84), [(label, 9, INK2, False), (value, 20, INK, True), (delta, 8, MUTED, False)], card=True)
        self.note_runs = [t for t, _ in rows[-1][1][0][1]]

    def add(self, box, visual: dict):
        x, y, w, h = box
        vid = hashlib.sha1(f"{self.name}{len(self.visuals)}".encode()).hexdigest()[:20]
        visual.setdefault("drillFilterOtherVisuals", True)
        self.visuals.append({"$schema": f"{SCHEMA}/visualContainer/2.13.0/schema.json", "name": vid,
                             "position": {"x": x, "y": y, "z": self.z, "height": h, "width": w, "tabOrder": self.z},
                             "visual": visual})
        self.z += 1

    def text(self, box, paragraphs, card=False):
        paras = [{"textRuns": [{"value": t, "textStyle": {"fontSize": f"{size}pt", "color": c,
                                                          **({"fontWeight": "bold"} if bold else {})}}]} for t, size, c, bold in paragraphs]
        vco = {"background": [{"properties": {"show": lit("true" if card else "false"), "color": color(SURFACE)}}],
               "border": [{"properties": {"show": lit("true" if card else "false"), "color": color(BORDER), "radius": lit("10D")}}]}
        self.add(box, {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": paras}}]},
                       "visualContainerObjects": vco})

    def note(self, y: int):
        bold, rest = self.note_runs[0].strip(), self.note_runs[1].strip()
        self.add((G, y, W - 2 * G, 64), {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": bold + " ", "textStyle": {"fontWeight": "bold", "fontSize": "9pt", "color": INK}},
                          {"value": rest, "textStyle": {"fontSize": "9pt", "color": INK2}}]},
            {"textRuns": [{"value": TW.SOURCE + ". Model and report generated as code: github.com/Ajay0704/ai-model-market",
                           "textStyle": {"fontSize": "8pt", "color": MUTED}}]}]}}]},
            "visualContainerObjects": {"background": [{"properties": {"show": lit("false")}}], "border": [{"properties": {"show": lit("false")}}]}})

    def chart(self, vtype: str, box, sheet: str, roles: dict[str, list], objects: dict | None = None, sort=None):
        qs = {r: {"projections": [proj(*f) if isinstance(f, tuple) else proj(f) for f in fs]} for r, fs in roles.items()}
        visual = {"visualType": vtype, "query": {"queryState": qs}, "visualContainerObjects": headings(sheet)}
        if sort:
            visual["query"]["sortDefinition"] = {"sort": [{"field": sort[0], "direction": sort[1]}], "isDefaultSort": True}
        if objects:
            visual["objects"] = objects
        self.add(box, visual)


LABELS = {"labels": [{"properties": {"show": lit("true")}}]}
SERIES_LABELS = {"seriesLabels": [{"properties": {"show": lit("true")}}]}
GROUP3 = {"China": CHINA, "US": US, "Everyone else": GRAY}
MEASURE2 = {"Share of tokens": GRAY, "Share of estimated spend": ACCENT}


def pages() -> list[Page]:
    week, month = C("dim_date", "week_start"), C("dim_month", "month_label")

    p1 = Page("1 · Leadership")
    grp = C("dim_lab", "chart_group")
    p1.chart("lineChart", (G, 200, W - 2 * G, 360), "Weekly share",
             {"Category": [week], "Y": [(M("fct_model_day", "Token Share"), "Share of tokens")], "Series": [grp]},
             {"dataPoint": by_value(grp, GROUP3), **SERIES_LABELS}, sort=(week, "Ascending"))
    p1.chart("clusteredColumnChart", (G, 576, HALF, 330), "Daily volume",
             {"Category": [month], "Y": [(M("fct_model_day", "Tokens per Day (T)"), "Tokens per day (T)")]},
             {"dataPoint": single(ACCENT)}, sort=(month, "Ascending"))
    p1.chart("lineChart", (2 * G + HALF, 576, HALF, 330), "Concentration",
             {"Category": [month], "Y": [(M("mart_model_month", "Lab HHI (full months)"), "Lab HHI"),
                                         (M("mart_model_month", "Highly Concentrated Line"), '1,800 "highly concentrated" (DOJ/FTC 2023)')]},
             {"dataPoint": by_measure({"mart_model_month.Lab HHI (full months)": ACCENT, "mart_model_month.Highly Concentrated Line": GRAY})},
             sort=(month, "Ascending"))
    p1.note(918)

    p2 = Page("2 · Pricing & finance")
    cg = C("dim_lab", "country_group")
    p2.chart("clusteredBarChart", (G, 200, HALF, 350), "Groups: tokens vs spend",
             {"Category": [cg], "Y": [(M("mart_model_month", "Token Share Sep 2026"), "Share of tokens"),
                                      (M("mart_model_month", "Spend Share Sep 2026"), "Share of estimated spend")]},
             {"dataPoint": by_measure({"mart_model_month.Token Share Sep 2026": GRAY, "mart_model_month.Spend Share Sep 2026": ACCENT}), **LABELS},
             sort=(M("mart_model_month", "Spend Share Sep 2026"), "Descending"))
    lab, meas = C("chart_labs_tokens_spend", "Lab"), C("chart_labs_tokens_spend", "Measure")
    p2.chart("clusteredBarChart", (2 * G + HALF, 200, HALF, 350), "Labs: tokens vs spend",
             {"Category": [lab], "Y": [(A("chart_labs_tokens_spend", "Share"), "Share")], "Series": [meas]},
             {"dataPoint": by_value(meas, MEASURE2), **LABELS}, sort=(lab, "Ascending"))
    tier, tmeas = C("chart_price_tiers", "Tier"), C("chart_price_tiers", "Measure")
    p2.chart("clusteredBarChart", (G, 566, HALF, 350), "Price tiers",
             {"Category": [tier], "Y": [(A("chart_price_tiers", "Share"), "Share")], "Series": [tmeas]},
             {"dataPoint": by_value(tmeas, MEASURE2), **LABELS}, sort=(tier, "Ascending"))
    pm, ps = C("chart_price_index", "Month"), C("chart_price_index", "Series")
    p2.chart("lineChart", (2 * G + HALF, 566, HALF, 350), "Price index",
             {"Category": [pm], "Y": [(A("chart_price_index", "Index (Jan 2025 = 100)"), "Index, Jan 2025 = 100")], "Series": [ps]},
             {"dataPoint": by_value(ps, {"Average price paid": ACCENT, "Same-model list price": GRAY}), **SERIES_LABELS}, sort=(pm, "Ascending"))
    p2.note(930)

    p3 = Page("3 · AI platform")
    qg = C("chart_quality_price", "Group")
    p3.chart("scatterChart", (G, 200, W - 2 * G, 700), "Quality vs price",
             {"Category": [C("chart_quality_price", "Model")], "Series": [qg],
              "X": [(A("chart_quality_price", "Price per M"), "Blended price per million tokens")],
              "Y": [(A("chart_quality_price", "Intelligence Index"), "Intelligence Index")],
              "Size": [(A("chart_quality_price", "Share of 90-day Tokens"), "Share of last-90-day tokens")]},
             {"dataPoint": by_value(qg, {"China": CHINA, "US": US, "Other": GRAY}),
              "categoryAxis": [{"properties": {"axisScale": lit("'log'"), "showAxisTitle": lit("true")}}],
              "valueAxis": [{"properties": {"start": lit("10D"), "end": lit("60D"), "showAxisTitle": lit("true")}}],
              "categoryLabels": [{"properties": {"show": lit("false")}}]})
    p3.note(916)

    p4 = Page("4 · Competitive intel")
    cm = C("chart_china_labs", "Month")
    p4.chart("lineChart", (G, 200, W - 2 * G, 420), "Chinese labs",
             {"Category": [cm], "Y": [(A("chart_china_labs", "Share"), "Share of tokens")], "Rows": [C("chart_china_labs", "Lab")]},
             {"dataPoint": single(CHINA)}, sort=(cm, "Ascending"))
    p4.chart("pivotTable", (G, 636, W - 2 * G, 270), "Robustness",
             {"Rows": [(C("chart_robustness", "Way of Counting"), "Way of counting")], "Columns": [(C("chart_robustness", "Month"), "Month")],
              "Values": [(M("chart_robustness", "Robustness Result"), "China vs US share of tokens")]},
             {"subTotals": [{"properties": {"rowSubtotals": lit("false"), "columnSubtotals": lit("false")}}]})
    p4.note(920)

    p5 = Page("5 · Product & GTM")
    lw, lsr = C("chart_launch_curve", "Weeks Since Launch"), C("chart_launch_curve", "Series")
    lw_w = int((W - 3 * G) * 0.58)
    p5.chart("lineChart", (G, 200, lw_w, 360), "Launch curve",
             {"Category": [lw], "Y": [(A("chart_launch_curve", "Share (% of peak)"), "% of the model's peak")], "Series": [lsr]},
             {"dataPoint": by_value(lsr, {"The lab": ACCENT, "The model": GRAY}), **SERIES_LABELS}, sort=(lw, "Ascending"))
    km, kc = C("chart_categories", "Month"), C("chart_categories", "Category")
    p5.chart("lineChart", (2 * G + lw_w, 200, W - 3 * G - lw_w, 360), "Categories",
             {"Category": [km], "Y": [(A("chart_categories", "Share"), "Share of categorized tokens")], "Series": [kc]},
             {"dataPoint": by_value(kc, {"Programming": ACCENT, "Roleplay": GRAY}), **SERIES_LABELS}, sort=(km, "Ascending"))
    p5.chart("clusteredBarChart", (G, 576, W - 2 * G, 340), "Top apps",
             {"Category": [C("chart_top_apps", "App")], "Y": [(A("chart_top_apps", "Share of September Tokens"), "Share of September tokens")]},
             {"dataPoint": single(ACCENT), **LABELS}, sort=(A("chart_top_apps", "Share of September Tokens"), "Descending"))
    p5.note(930)
    return [p1, p2, p3, p4, p5]


def build(model_id: str) -> dict[str, str]:
    ps = pages()
    ver = {"visual": "2.14.0", "report": "3.4.0", "page": "2.3.1"}
    files = {
        "definition.pbir": {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
                            "version": "4.0",
                            "datasetReference": {"byConnection": {"connectionString":
                                f'Data Source="powerbi://api.powerbi.com/v1.0/myorg/My workspace";initial catalog="{MODEL_NAME}";'
                                f"integrated security=ClaimsToken;semanticmodelid={model_id}"}}},
        "definition/version.json": {"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"},
        "definition/report.json": {
            "$schema": f"{SCHEMA}/report/3.3.0/schema.json",
            "themeCollection": {
                "baseTheme": {"name": "Fluent2-CY26SU10", "reportVersionAtImport": ver, "type": "SharedResources"},
                "customTheme": {"name": THEME_NAME, "reportVersionAtImport": ver, "type": "RegisteredResources"}},
            "resourcePackages": [
                {"name": "SharedResources", "type": "SharedResources",
                 "items": [{"name": "Fluent2-CY26SU10", "path": "BaseThemes/Fluent2-CY26SU10.json", "type": "BaseTheme"}]},
                {"name": "RegisteredResources", "type": "RegisteredResources",
                 "items": [{"name": THEME_NAME, "path": THEME_NAME, "type": "CustomTheme"}]}],
            "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                         "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                         "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}},
        "definition/pages/pages.json": {"$schema": f"{SCHEMA}/pagesMetadata/1.1.0/schema.json",
                                        "pageOrder": [p.id for p in ps], "activePageName": ps[0].id},
        f"StaticResources/RegisteredResources/{THEME_NAME}": THEME,
    }
    for p in ps:
        files[f"definition/pages/{p.id}/page.json"] = {"$schema": f"{SCHEMA}/page/2.1.0/schema.json", "name": p.id,
                                                      "displayName": p.name, "displayOption": "FitToWidth",
                                                      "height": p.height, "width": W}
        for v in p.visuals:
            files[f"definition/pages/{p.id}/visuals/{v['name']}/visual.json"] = v
    return {k: json.dumps(v, indent=2, ensure_ascii=False) for k, v in files.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", default="00000000-0000-0000-0000-000000000000")
    a = ap.parse_args()
    files = build(a.model_id)
    for path, text in files.items():
        f = OUT / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text + "\n")
    n = sum(1 for p in files if p.endswith("visual.json"))
    print(f"{n} visuals on {sum(1 for p in files if p.endswith('page.json'))} pages -> {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
