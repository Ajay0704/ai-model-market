# Style guide: charts that look like a tech company made them

Ajay's brief (2026-10-19): the charts must look like how tech companies would make them. The rules below come from tech companies' own published data-visualization design systems, cited per rule. Two more sources are labeled as what they are: Ajay's own Olist case study, and the chart method used to validate colors (a tool, not a company). Where the sources disagree, the stricter rule wins, and the guide says so.

## Sources
| Short name | What it is | Link |
|---|---|---|
| Carbon | IBM Carbon Design System, data-visualization color palettes | https://carbondesignsystem.com/data-visualization/color-palettes/ |
| Pajamas charts | GitLab Pajamas Design System, charts | https://design.gitlab.com/data-visualization/charts |
| Pajamas dashboards | GitLab Pajamas Design System, dashboards pattern | https://design.gitlab.com/patterns/dashboards |
| Atlassian | Atlassian Design System, data-visualization color | https://atlassian.design/foundations/color-new/data-visualization-color |
| Olist playbook | Ajay's own Olist BI case study (`~/Downloads/Olist_BI_Case_Study_Playbook.pdf`) | local |
| Chart method | The data-viz method and its palette validator (colorblind separation, contrast) | tooling |

## 1. Page layout
- **Summary at the top, detail below.** Pajamas dashboards: put "high-level information at the top and detailed information towards the bottom". So every page opens with a KPI row, then charts.
- **One chart per panel** (Pajamas dashboards, "Maintain simplicity").
- **A 12-column grid that collapses to one column** on narrow screens (Pajamas dashboards, Structure).
- **Concise page title, plus its purpose** (Pajamas dashboards, Structure). Here, the page title is the stakeholder's finding and the subtitle is the decision it informs.
- **Meeting-ready:** it should read well as a screenshot or on a shared screen (Pajamas dashboards, "Design for sharing").
- **The date range sits under every panel title** (Pajamas dashboards, Exceptions), along with the source line.

## 2. Titles and numbers
- **Insight titles with verified numbers**, never labels. "China passed the US on Apr 27", not "Share by country" (Olist playbook). Every number in a title must exist in `docs/ANSWER_KEY.md` or `docs/FINDINGS.md`.
- **Compact units:** 576T tokens, $0.68/M, 58.5%. Percentages get one decimal; HHI has none. Units go in parentheses in axis titles (Pajamas charts).
- **Table rows use tabular figures; big standalone numbers don't** (chart method).

## 3. Color
- **Color follows the entity, and one entity keeps one color on every page.** China blue, US orange, other named labs aqua. They're assigned in a fixed order, the way Carbon says categorical colors "should be applied in sequence strictly".
- **Chart colors go on data marks only.** Axes and text use the text and border tokens (Atlassian). Text is never colored to match a series.
- **Emphasis means fading the rest.** Atlassian fades non-selected data. Here, any chart that isn't about countries is monochrome: violet for the measure the title is about, gray for its comparison.
- **Magnitude uses one hue,** darkest = largest in the light theme (Carbon, sequential), and never a gradient standing in for a sequential palette (Carbon).
- **Validated, not eyeballed** (chart method). Results:

| Set | Mode | Separation (colorblind / normal vision) | Contrast vs surface |
|---|---|---|---|
| China / US / other named (`#2a78d6 #eb6834 #1baf7a`), all pairs | light | pass (9.2 / 24.0) | aqua 2.74:1, so direct labels and a table view are required |
| Same hues, dark steps (`#3987e5 #d95926 #199e70`) | dark | pass (9.4 / 20.9) | all at least 3:1 |
| China / US / everyone else (gray `#898781`) | light | pass (9.8 / 17.6) | all at least 3:1 |
| Same, dark (gray `#6e6c66`) | dark | pass (9.1 / 19.0) | all at least 3:1 |
| Accent violet vs comparison gray | both | pass (21.5 / 22.7 light; 19.5 / 20.7 dark) | all at least 3:1 |

  The gray is meant to read as neutral, so it "fails" the chroma floor by design. **Rejected:** gray as a 4th band next to aqua (normal-vision ΔE 14.7, under the floor of 15). That's why page 1 uses lines, not a stacked area.

## 4. Chart forms
- **Columns, not pies** (Pajamas charts: column charts "more clearly communicate data").
- **A legend whenever there are 2+ series** (Pajamas charts), plus selective direct labels. No legend for a single series; the title names it.
- **No more than 5 values per dimension** in grouped or stacked charts (Pajamas charts).
- **No dual y-axis charts.** Pajamas allows them for data of different magnitudes. The Olist playbook and the chart method both ban them, so the stricter rule wins. Two measures on different scales become two charts, or are indexed to a common base (e.g. price index, Jan 2025 = 100).
- **Two measures in the same unit** (token share vs spend share) become a dumbbell on one % axis.

## 5. Marks
- Bars at most 24px thick, with a 4px rounded end at the value and square at the baseline. Lines 2px. Markers at least 8px with a 2px surface ring. Gridlines are solid 1px hairlines, never dashed (chart method).
- A 2px surface gap between touching bars, never a border drawn around a mark (chart method).

## 6. Interaction and accessibility
- **Hover tooltips:** the header shows the x value; the body shows the series and value (Pajamas charts, chart popovers). Tooltips enhance; they never gate a value.
- **Every chart has a table view** (chart method). Light and dark themes are both designed, not auto-inverted.

## 7. Carrying it into the two tools (step 5b)
- **Power BI:** a report theme JSON with `dataColors` in the fixed order above, the text and background tokens, and gridlines at the hairline color.
- **Tableau:** a custom palette in `Preferences.tps`, gray hairline gridlines and no borders, set in the generated `.twb` XML.

Both use the system UI font stack the mockup uses.
