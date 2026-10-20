"""Tableau workbook XML (.twb) writers for Tableau Desktop 2026.2 (workbook version 18.1).

Started from ~/olist-text2sql/scripts/tableau_xml.py, then extended with the formatting the style guide needs:
hairline gridlines, no borders or bands, Tableau's own sans faces, single-colour marks, line-end labels,
fixed axis ranges, hidden axis titles and card-style dashboard zones. Every <format> attribute used here
appears in Tableau-saved sample workbooks (see docs/STYLE_GUIDE.md section 7); the log-scale axis is the
one exception and is flagged in the build notes.
"""

import uuid
from xml.sax.saxutils import escape

DERIVATION = {"none": "None", "sum": "Sum", "avg": "Avg", "cnt": "Count", "attr": "Attribute",
              "usr": "User", "min": "Min", "max": "Max", "tmn": "Month-Trunc"}

# Style-guide tokens (light theme; Tableau has no viewer dark mode)
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#6f6d67"
GRID, AXIS, PLANE, SURFACE, BORDER = "#e1e0d9", "#c3c2b7", "#f9f9f7", "#fcfcfb", "#e1e0d9"
BOOK, SEMI = "Tableau Book", "Tableau Semibold"


def q(value):
    return "'" + escape(str(value), {"'": "&apos;"}) + "'"


def sid():
    return f"<simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' />"


class Field:
    def __init__(self, der, col, kind=None):
        self.der, self.col = der, col
        self.kind = kind or ("nk" if der == "none" else "qk")

    @property
    def inst(self):
        return f"[{self.der}:{self.col}:{self.kind}]"


class Datasource:
    def __init__(self, key, caption, directory, filename, columns, palettes=None, formats=None, dims=()):
        self.name = "federated." + key
        self.conn = "textscan." + key
        self.caption, self.directory, self.filename = caption, directory, filename
        self.columns = columns
        self.types = dict(columns)
        self.palettes = palettes or {}
        self.formats = formats or {}
        self.dims = set(dims)  # numeric columns used as continuous dimensions
        self.table = filename.replace(".", "#")
        self.obj = filename + "_" + uuid.uuid5(uuid.NAMESPACE_URL, key).hex.upper()

    def ref(self, field):
        return f"[{self.name}].{field.inst}"

    def column_def(self, col):
        dt = self.types[col]
        measure = dt in ("integer", "real") and col not in self.dims
        fmt = f" default-format={q(self.formats[col])}" if col in self.formats else ""
        role = "measure" if measure else "dimension"
        typ = "quantitative" if measure or dt == "date" or col in self.dims else "nominal"
        return f"<column datatype={q(dt)}{fmt} name={q('[' + col + ']')} role={q(role)} type={q(typ)} />"

    def relation(self):
        cols = "".join(f"<column datatype={q(dt)} name={q(n)} ordinal='{i}' />" for i, (n, dt) in enumerate(self.columns))
        return (f"<relation connection={q(self.conn)} name={q(self.filename)} table={q('[' + self.table + ']')} "
                f"type='table'><columns character-set='UTF-8' header='yes' locale='en_US' separator=','>"
                f"{cols}</columns></relation>")

    def xml(self):
        style = ""
        if self.palettes:
            rules = ""
            for col, mapping in self.palettes.items():
                maps = "".join(f"<map to={q(c)}><bucket>{escape(chr(34) + v + chr(34))}</bucket></map>" for v, c in mapping.items())
                rules += f"<encoding attr='color' field={q('[none:' + col + ':nk]')} type='palette'>{maps}</encoding>"
            style = f"<style><style-rule element='mark'>{rules}</style-rule></style>"
        cols = "".join(self.column_def(c) for c in sorted(self.types))
        return (
            f"<datasource caption={q(self.caption)} inline='true' name={q(self.name)} version='18.1'>"
            f"<connection class='federated'><named-connections>"
            f"<named-connection caption={q(self.caption)} name={q(self.conn)}>"
            f"<connection class='textscan' directory={q(self.directory)} filename={q(self.filename)} "
            f"password='' server='' /></named-connection></named-connections>"
            f"{self.relation()}</connection>"
            f"<aliases enabled='yes' />{cols}"
            f"<column caption={q(self.filename)} datatype='table' "
            f"name={q('[__tableau_internal_object_id__].[' + self.obj + ']')} role='measure' type='quantitative' />"
            f"<layout dim-ordering='alphabetic' measure-ordering='alphabetic' show-structure='true' />"
            f"{style}"
            f"<object-graph><objects><object caption={q(self.filename)} id={q(self.obj)}>"
            f"<properties context=''>{self.relation()}</properties></object></objects></object-graph>"
            f"</datasource>")


def fmt(attr, value, **kw):
    extra = "".join(f" {k}={q(v)}" for k, v in kw.items())
    return f"<format attr={q(attr)}{extra} value={q(value)} />"


class Sheet:
    """One worksheet in the house style.

    rows/cols: lists of Fields. mark: Bar | Line | Circle | Text | Area.
    color: Field coloured by the datasource palette, or mark_color for one fixed colour.
    labels: show mark labels; label_mode 'all' | 'line-ends' | 'most-recent'; text: Fields on the label shelf.
    axis_ranges: [(Field, 'rows'|'cols', min, max)]; hide_titles: [(Field, scope)]; log_axis: (Field, scope).
    label_formats: {Field: tableau number format} for mark labels.
    """

    def __init__(self, name, ds, title, subtitle="", rows=(), cols=(), mark="Bar", color=None, mark_color=None,
                 text=(), size=None, detail=(), filters=None, manual_sort=None, sort_by=None, labels=False,
                 label_mode="all", refline=None, axis_ranges=(), hide_titles=(), log_axis=None, label_formats=None,
                 hide_headers=(), cell_text=False):
        self.name, self.ds, self.title, self.subtitle = name, ds, title, subtitle
        self.rows, self.cols, self.mark = list(rows), list(cols), mark
        self.color, self.mark_color, self.text, self.size, self.detail = color, mark_color, list(text), size, list(detail)
        self.filters, self.manual_sort, self.sort_by = filters or {}, manual_sort, sort_by
        self.labels, self.label_mode, self.refline = labels, label_mode, refline
        self.axis_ranges, self.hide_titles, self.log_axis = list(axis_ranges), list(hide_titles), log_axis
        self.label_formats = label_formats or {}
        self.hide_headers, self.cell_text = list(hide_headers), cell_text

    def fields(self):
        fs = self.rows + self.cols + self.detail + self.text + [f for f in (self.color, self.size) if f]
        fs += [Field("none", c) for c in self.filters]
        for col, _ in self.sorts():
            fs.append(Field("none", col))
        if self.sort_by:
            fs += list(self.sort_by[:2])
        if self.refline:
            fs.append(self.refline["value"])
        seen, out = set(), []
        for f in fs:
            if f.inst not in seen:
                seen.add(f.inst)
                out.append(f)
        return out

    def sorts(self):
        if not self.manual_sort:
            return []
        return self.manual_sort if isinstance(self.manual_sort, list) else [self.manual_sort]

    def shelf(self, fields):
        if not fields:
            return ""
        parts = [self.ds.ref(f) for f in fields]
        return parts[0] if len(parts) == 1 else "(" + " / ".join(parts) + ")"

    def table_style(self):
        ds = self.ds
        axis = fmt("line-visibility", "off") + fmt("tick-color", "#00000000")
        for f, scope, lo, hi in self.axis_ranges:
            axis += (f"<encoding attr='space' class='0' field={q(ds.ref(f))} field-type='quantitative' max={q(hi)} "
                     f"min={q(lo)} range-type='fixed' scope={q(scope)} type='space' />")
        if self.log_axis:
            f, scope = self.log_axis
            axis += (f"<encoding attr='space' class='0' field={q(ds.ref(f))} field-type='quantitative' "
                     f"scale='log' scope={q(scope)} type='space' />")
        for f, scope in self.hide_titles:
            axis += fmt("title", "", **{"class": "0", "field": ds.ref(f), "scope": scope})
        label = fmt("font-family", SEMI) + fmt("font-size", "9") + fmt("color", INK)
        for f, code in self.label_formats.items():
            label += fmt("text-format", code, field=ds.ref(f))
        header = fmt("border-style", "none") + fmt("band-color", "#00000000") + fmt("font-family", BOOK) + fmt("color", INK2)
        for f in self.hide_headers:  # Tableau stores "Show Header: off" on the label element
            label += fmt("display", "false", field=ds.ref(f))
        cell = fmt("font-family", BOOK) + fmt("font-size", "10") + fmt("color", INK)
        ref = ""
        if self.refline:
            ref = ("<style-rule element='refline'>" + fmt("stroke-color", INK2, id="refline0") + fmt("stroke-size", "1", id="refline0")
                   + fmt("line-pattern-only", "solid", id="refline0") + fmt("font-family", BOOK, id="refline0")
                   + fmt("font-size", "8", id="refline0") + "</style-rule>")
        return (
            "<style>"
            f"<style-rule element='axis'>{axis}</style-rule>"
            f"<style-rule element='cell'>{cell}</style-rule>"
            f"<style-rule element='header'>{header}</style-rule>"
            f"<style-rule element='label'>{label}</style-rule>"
            "<style-rule element='gridline'>" + fmt("line-visibility", "on") + fmt("stroke-size", "1")
            + fmt("line-pattern-only", "solid") + fmt("stroke-color", GRID) + "</style-rule>"
            "<style-rule element='zeroline'>" + fmt("line-visibility", "on") + fmt("stroke-size", "1")
            + fmt("line-pattern-only", "solid") + fmt("stroke-color", AXIS) + "</style-rule>"
            "<style-rule element='dropline'>" + fmt("line-visibility", "off") + "</style-rule>"
            "<style-rule element='table-div'>" + fmt("line-visibility", "off") + fmt("stroke-size", "0") + "</style-rule>"
            "<style-rule element='header-div'>" + fmt("line-visibility", "off") + fmt("stroke-size", "0") + "</style-rule>"
            "<style-rule element='pane'>" + fmt("border-style", "none") + fmt("band-color", "#00000000") + "</style-rule>"
            "<style-rule element='table'>" + fmt("background-color", SURFACE) + fmt("show-null-value-warning", "false") + "</style-rule>"
            "<style-rule element='worksheet'>" + fmt("font-family", BOOK) + fmt("font-size", "9") + fmt("color", INK2)
            + fmt("display-field-labels", "false") + "</style-rule>"
            f"{ref}</style>")

    def xml(self):
        ds = self.ds
        fields = self.fields()
        deps = "".join(ds.column_def(c) for c in sorted({f.col for f in fields}))
        deps += "".join(
            f"<column-instance column={q('[' + f.col + ']')} derivation={q(DERIVATION[f.der])} "
            f"name={q(f.inst)} pivot='key' type={q('nominal' if f.kind == 'nk' else 'ordinal' if f.kind == 'ok' else 'quantitative')} />"
            for f in fields)
        filters, slices = "", ""
        for col, values in self.filters.items():
            lvl = f"[none:{col}:nk]"
            members = "".join(f"<groupfilter function='member' level={q(lvl)} member={q(chr(34) + v + chr(34))} />" for v in values)
            filters += (f"<filter class='categorical' column={q(ds.ref(Field('none', col)))}>"
                        f"<groupfilter function='union' user:ui-domain='database' user:ui-enumeration='inclusive' "
                        f"user:ui-marker='enumerate'>{members}</groupfilter></filter>")
            if lvl not in {f.inst for f in self.rows + self.cols}:
                slices += f"<column>{ds.ref(Field('none', col))}</column>"
        if slices:
            slices = f"<slices>{slices}</slices>"
        sorts = ""
        for col, order in self.sorts():
            buckets = "".join(f"<bucket>{escape(chr(34) + v + chr(34))}</bucket>" for v in order)
            sorts += (f"<manual-sort column={q(ds.ref(Field('none', col)))} direction='ASC'>"
                      f"<dictionary>{buckets}</dictionary></manual-sort>")
        if self.sort_by:
            dim, meas, direction = self.sort_by
            sorts += (f"<shelf-sorts><shelf-sort-v2 dimension-to-sort={q(ds.ref(dim))} direction={q(direction)} "
                      f"is-on-innermost-dimension='true' measure-to-sort-by={q(ds.ref(meas))} shelf='rows' />"
                      f"</shelf-sorts>")
        enc = ""
        if self.color:
            enc += f"<color column={q(ds.ref(self.color))} />"
        if self.size:
            enc += f"<size column={q(ds.ref(self.size))} />"
        for t in self.text:
            enc += f"<text column={q(ds.ref(t))} />"
        for d in self.detail:
            enc += f"<lod column={q(ds.ref(d))} />"
        enc = f"<encodings>{enc}</encodings>" if enc else ""
        mark_rules = ""
        if self.mark_color:
            mark_rules += fmt("mark-color", self.mark_color)
        if self.labels:
            mark_rules += fmt("mark-labels-show", "true") + fmt("mark-labels-cull", "true") + fmt("mark-labels-mode", self.label_mode)
        if self.mark in ("Line",):
            mark_rules += fmt("mark-markers-mode", "none")
        if self.mark == "Circle":
            mark_rules += fmt("has-stroke", "true") + fmt("stroke-color", SURFACE) + fmt("mark-transparency", "220")
        pane_style = "<style>"
        if mark_rules:
            pane_style += f"<style-rule element='mark'>{mark_rules}</style-rule>"
        if self.cell_text:
            pane_style += "<style-rule element='cell'>" + fmt("text-align", "left") + fmt("vertical-align", "center") + "</style-rule>"
        pane_style += "</style>"
        ref = ""
        if self.refline:
            r = self.refline
            ref = (f"<reference-line axis-column={q(ds.ref(r['axis']))} enable-instant-analytics='true' "
                   f"formula={q(r.get('formula', 'average'))} id='refline0' label={q(r['label'])} label-type='custom' "
                   f"scope={q(r.get('scope', 'per-table'))} value-column={q(ds.ref(r['value']))} z-order='1' />")
        title = f"<run bold='true' fontcolor={q(INK)} fontname={q(SEMI)} fontsize='11'>{escape(self.title)}</run>"
        if self.subtitle:
            title += f"<run>Æ&#10;</run><run fontcolor={q(MUTED)} fontname={q(BOOK)} fontsize='8'>{escape(self.subtitle)}</run>"
        return (
            f"<worksheet name={q(self.name)}><layout-options><title><formatted-text>{title}</formatted-text></title></layout-options>"
            f"<table><view><datasources><datasource caption={q(ds.caption)} name={q(ds.name)} /></datasources>"
            f"<datasource-dependencies datasource={q(ds.name)}>{deps}</datasource-dependencies>"
            f"{filters}{sorts}{slices}<aggregation value='true' /></view>"
            f"{self.table_style()}"
            f"<panes><pane selection-relaxation-option='selection-relaxation-allow'>"
            f"<view><breakdown value='auto' /></view><mark class={q(self.mark)} />{enc}{ref}{pane_style}"
            f"</pane></panes>"
            f"<rows>{self.shelf(self.rows)}</rows><cols>{self.shelf(self.cols)}</cols></table>"
            f"{sid()}</worksheet>")


# ---------- dashboards ----------

def run(text, size=10, font=BOOK, colour=INK, bold=False):
    attrs = {"fontcolor": colour, "fontname": font, "fontsize": str(size)}
    if bold:
        attrs["bold"] = "true"
    return (text, attrs)


def zone_style(card):
    if card:
        return ("<zone-style>" + fmt("border-color", BORDER) + fmt("border-style", "solid") + fmt("border-width", "1")
                + fmt("margin", "6") + fmt("padding", "10") + fmt("background-color", SURFACE) + "</zone-style>")
    return ("<zone-style>" + fmt("border-color", "#000000") + fmt("border-style", "none") + fmt("border-width", "0")
            + fmt("margin", "6") + fmt("padding", "4") + "</zone-style>")


def text_zone(zid, x, y, w, h, runs, card=False):
    body = "".join(f"<run{''.join(f' {k}={q(v)}' for k, v in attrs.items())}>{escape(t)}</run>" for t, attrs in runs)
    return (f"<zone h='{h}' id='{zid}' type-v2='text' w='{w}' x='{x}' y='{y}'>"
            f"<formatted-text>{body}</formatted-text>{zone_style(card)}</zone>")


def sheet_zone(zid, x, y, w, h, name):
    return f"<zone h='{h}' id='{zid}' name={q(name)} w='{w}' x='{x}' y='{y}'>{zone_style(True)}</zone>"


def dashboard(name, width, height, rows):
    """rows: [(height share, [(kind, content, width share)])]; kind 'sheet' | 'text' | 'card' (text in a card)."""
    zones, zid, y = [], 2, 0
    for r, (hshare, items) in enumerate(rows):
        h = 100000 - y if r == len(rows) - 1 else round(hshare * 100000)
        x = 0
        for i, (kind, content, wshare) in enumerate(items):
            w = 100000 - x if i == len(items) - 1 else round(wshare * 100000)
            zones.append(sheet_zone(zid, x, y, w, h, content) if kind == "sheet"
                         else text_zone(zid, x, y, w, h, content, card=(kind == "card")))
            zid += 1
            x += w
        y += h
    style = "<style><style-rule element='table'>" + fmt("background-color", PLANE) + "</style-rule></style>"
    return (f"<dashboard name={q(name)}>{style}"
            f"<size maxheight='{height}' maxwidth='{width}' minheight='{height}' minwidth='{width}' />"
            f"<zones><zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>"
            f"{''.join(zones)}</zone></zones>{sid()}</dashboard>")


def story(name, width, height, points):
    sp = "".join(f"<story-point caption={q(cap)} captured-sheet={q(sheet)} id='{i}' />" for i, (sheet, cap) in enumerate(points, 1))
    style = "<style><style-rule element='table'>" + fmt("background-color", PLANE) + "</style-rule></style>"
    return (f"<dashboard name={q(name)} type='storyboard'>{style}"
            f"<size maxheight='{height}' maxwidth='{width}' minheight='{height}' minwidth='{width}' />"
            f"<zones><zone h='100000' id='2' type-v2='layout-basic' w='100000' x='0' y='0'>"
            f"<zone h='98340' id='1' param='vert' removable='false' type-v2='layout-flow' w='98426' x='787' y='830'>"
            f"<zone h='4000' id='3' type-v2='title' w='98426' x='787' y='830' />"
            f"<zone h='12000' id='4' is-fixed='true' paired-zone-id='5' removable='false' type-v2='flipboard-nav' "
            f"w='98426' x='787' y='4830' />"
            f"<zone h='82340' id='5' paired-zone-id='4' removable='false' type-v2='flipboard' w='98426' x='787' y='16830'>"
            f"<flipboard active-id='1' nav-type='caption' show-nav-arrows='true'><story-points>{sp}</story-points>"
            f"</flipboard></zone></zone></zone></zones>{sid()}</dashboard>")


CARDS = ("<cards><edge name='left'><strip size='160'><card type='pages' /><card type='filters' />"
         "<card type='marks' /></strip></edge><edge name='top'><strip size='2147483647'>"
         "<card type='columns' /></strip><strip size='2147483647'><card type='rows' /></strip>"
         "<strip size='31'><card type='title' /></strip></edge></cards>")


def workbook(datasources, sheets, boards):
    windows = "".join(f"<window class='worksheet' name={q(s.name)}>{CARDS}{sid()}</window>" for s in sheets)
    windows += "".join(
        f"<window class='dashboard'{' maximized=' + q('true') if i == 0 else ''} name={q(name)}>"
        f"<viewpoints>{''.join(f'<viewpoint name={q(s)} />' for s in members)}</viewpoints>"
        f"<active id='-1' />{sid()}</window>"
        for i, (name, members, _) in enumerate(boards))
    font = "<style><style-rule element='all'>" + fmt("font-family", BOOK) + "</style-rule></style>"
    return (
        "<?xml version='1.0' encoding='utf-8' ?>\n"
        "<workbook original-version='18.1' source-build='2026.2.1 (20262.26.0708.1337)' "
        "source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>"
        "<document-format-change-manifest><AnimationOnByDefault /><IntuitiveSorting /><IntuitiveSorting_SP2 />"
        "<MarkAnimation /><ObjectModelEncapsulateLegacy /><ObjectModelExtractV2 /><ObjectModelTableType />"
        "<SchemaViewerObjectModel /><SetMembershipControl /><SheetIdentifierTracking /><SortTagCleanup />"
        "<WindowsPersistSimpleIdentifiers />"
        "</document-format-change-manifest>"
        "<preferences><preference name='ui.encoding.shelf.height' value='24' /><preference name='ui.shelf.height' value='26' /></preferences>"
        f"{font}"
        f"<datasources>{''.join(d.xml() for d in datasources)}</datasources>"
        f"<worksheets>{''.join(s.xml() for s in sheets)}</worksheets>"
        f"<dashboards>{''.join(x for _, _, x in boards)}</dashboards>"
        f"<windows source-height='30'>{windows}</windows></workbook>\n")
