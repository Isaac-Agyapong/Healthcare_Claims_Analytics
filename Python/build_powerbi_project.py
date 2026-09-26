"""
Generate the Power BI Project (PBIP) for the claims dashboard:

    dashboard/Healthcare_Claims.pbip                 <- open this in Power BI Desktop
    dashboard/Healthcare_Claims.SemanticModel/       <- data model as TMDL text files
    dashboard/Healthcare_Claims.Report/              <- report pages and visuals as PBIR JSON

The model reads the CSVs in Data/clean/ through the `DataFolder` parameter. After opening
the .pbip, click Refresh to load the data.
"""
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard"
NAME = "Healthcare_Claims"
SM = DASH / f"{NAME}.SemanticModel"
RPT = DASH / f"{NAME}.Report"
DATA_FOLDER = str(ROOT / "Data" / "clean") + "\\"

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
S_PBIP = f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json"
S_PBISM = f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json"
S_PBIR = f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json"
S_VERSION = f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json"
S_REPORT = f"{SCHEMA}/item/report/definition/report/1.2.0/schema.json"
S_PAGES = f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json"
S_PAGE = f"{SCHEMA}/item/report/definition/page/1.3.0/schema.json"
S_VISUAL = f"{SCHEMA}/item/report/definition/visualContainer/1.4.0/schema.json"

BASE_THEME = "CY24SU10"
BASE_THEME_SRC = Path(r"C:\Program Files\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_2.157.1354.0_x64__8wekyb3d8bbwe"
                      r"\bin\WebView2Resources\minerva\sharedresources\BaseThemes") / f"{BASE_THEME}.json"
CUSTOM_THEME = "ClaimsPortfolioTheme.json"

# PALETTE-V2: blue = claims / paid, crimson = denials, amber = flagged providers, slate/grey = neutral
# DARK-THEME palette: cyan = claims / paid, rose = denials, gold = flagged providers
BLUE, CRIMSON, AMBER, SLATE, GREY = "#38BDF8", "#FB7185", "#FBBF24", "#94A3B8", "#3A4E72"
FACT = "claims_clean"


def tag(*parts):
    """Stable lineage tag so rebuilding produces the same ids."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "claims/" + "/".join(parts)))


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, obj):
    write(path, json.dumps(obj, indent=2) + "\n")


def q(name):
    """Quote a TMDL object name when needed."""
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


# =====================================================================
# Semantic model (TMDL)
# =====================================================================
# (column, tmdl dataType, M type, formatString or None, summarizeBy)
CLAIM_COLS = [
    ("claim_id", "string", "type text", None, "none"),
    ("patient_id", "string", "type text", None, "none"),
    ("provider_id", "string", "type text", None, "none"),
    ("service_date", "dateTime", "type date", "yyyy-mm-dd", "none"),
    ("submission_date", "dateTime", "type date", "yyyy-mm-dd", "none"),
    ("processed_date", "dateTime", "type date", "yyyy-mm-dd", "none"),
    ("claim_type", "string", "type text", None, "none"),
    ("diagnosis_category", "string", "type text", None, "none"),
    ("cpt_code", "string", "type text", None, "none"),
    ("billed_amount", "decimal", "Currency.Type", r"\$#,0.00;(\$#,0.00);\$#,0.00", "sum"),
    ("allowed_amount", "decimal", "Currency.Type", r"\$#,0.00;(\$#,0.00);\$#,0.00", "sum"),
    ("paid_amount", "decimal", "Currency.Type", r"\$#,0.00;(\$#,0.00);\$#,0.00", "sum"),
    ("claim_status", "string", "type text", None, "none"),
    ("denial_reason", "string", "type text", None, "none"),
    ("billed_imputed", "boolean", "type logical", None, "none"),
    ("age_at_service", "int64", "Int64.Type", "0", "none"),
    ("age_group", "string", "type text", None, "none"),
    ("days_to_submit", "int64", "Int64.Type", "0", "sum"),
    ("days_to_process", "double", "type number", "0", "sum"),
    ("is_denied", "int64", "Int64.Type", "0", "sum"),
    ("member_responsibility", "decimal", "Currency.Type", r"\$#,0.00;(\$#,0.00);\$#,0.00", "sum"),
]
# the clean CSV also carries these convenience columns; the model gets them through relationships instead
CLAIM_DROP = ["plan_type", "specialty", "network_status", "service_month", "service_year"]

PATIENT_COLS = [
    ("patient_id", "string", "type text", None, "none"),
    ("gender", "string", "type text", None, "none"),
    ("date_of_birth", "dateTime", "type date", "yyyy-mm-dd", "none"),
    ("state", "string", "type text", None, "none"),
    ("plan_type", "string", "type text", None, "none"),
    ("enrollment_date", "dateTime", "type date", "yyyy-mm-dd", "none"),
]
PROVIDER_COLS = [(c, "string", "type text", None, "none")
                 for c in ["provider_id", "provider_name", "specialty", "state", "network_status"]]

PCT, MONEY, INT = "0.0%;-0.0%;0.0%", r"\$#,0;(\$#,0);\$#,0", "#,0"
MEASURES = [
    # (name, DAX, formatString, folder)
    ("Total Claims", "COUNTROWS ( claims_clean )", INT, "Volume"),
    ("Decided Claims", 'CALCULATE ( [Total Claims], claims_clean[claim_status] <> "Pending" )', INT, "Volume"),
    ("Denied Claims", 'CALCULATE ( [Total Claims], claims_clean[claim_status] = "Denied" )', INT, "Volume"),
    ("Unique Patients", "DISTINCTCOUNT ( claims_clean[patient_id] )", INT, "Volume"),
    ("Total Billed", "SUM ( claims_clean[billed_amount] )", MONEY, "Money"),
    ("Total Paid", "SUM ( claims_clean[paid_amount] )", MONEY, "Money"),
    ("Denied Billed $", 'CALCULATE ( [Total Billed], claims_clean[claim_status] = "Denied" )', MONEY, "Money"),
    ("Paid to Billed %", "DIVIDE ( [Total Paid], [Total Billed] )", PCT, "Money"),
    ("Paid YTD", "TOTALYTD ( [Total Paid], DimDate[Date] )", MONEY, "Money"),
    ("Denial Rate", "DIVIDE ( [Denied Claims], [Decided Claims] )", PCT, "Rates"),
    ("Denial Rate (trend)",
     "// December 2025 is left out of trend lines: most of its claims are still pending\n"
     "IF ( MAX ( DimDate[Date] ) >= DATE ( 2025, 12, 1 ), BLANK (), [Denial Rate] )", PCT, "Rates"),
    ("Peer Denial Rate",
     "// denial rate of all providers with the same claim type and network status\n"
     "VAR _type = SELECTEDVALUE ( claims_clean[claim_type] )\n"
     "VAR _network = SELECTEDVALUE ( providers_clean[network_status] )\n"
     "RETURN\n"
     "    CALCULATE (\n"
     "        [Denial Rate],\n"
     "        REMOVEFILTERS ( providers_clean ),\n"
     "        claims_clean[claim_type] = _type,\n"
     "        providers_clean[network_status] = _network\n"
     "    )", PCT, "Providers"),
    ("Excess Denial (pts)",
     "IF ( NOT ISBLANK ( [Denial Rate] ), ( [Denial Rate] - [Peer Denial Rate] ) * 100 )", "0.0", "Providers"),
    ("Excess Rank",
     "IF (\n"
     "    HASONEVALUE ( providers_clean[provider_name] ),\n"
     "    RANKX ( ALLSELECTED ( providers_clean[provider_name] ), [Excess Denial (pts)], , DESC )\n"
     ")", "0", "Providers"),
    ("Top 10 Excess (pts)",
     "VAR _rank = [Excess Rank]\n"
     "RETURN IF ( NOT ISBLANK ( _rank ) && _rank <= 10, [Excess Denial (pts)] )", "0.0", "Providers"),
    ("Excess Colour", f'IF ( [Excess Denial (pts)] >= 10, "{AMBER}", "{GREY}" )', None, "Providers"),
    ("Avg Days to Process", "AVERAGE ( claims_clean[days_to_process] )", "0.0", "Time"),
    ("Prior Auth Denials",
     'CALCULATE ( [Denied Claims], claims_clean[denial_reason] = "Missing prior authorization" )', INT, "Denials"),
    ("Other Denials", "[Denied Claims] - [Prior Auth Denials]", INT, "Denials"),
    ("Prior Auth Denials 2024", "CALCULATE ( [Prior Auth Denials], DimDate[Year] = 2024 )", INT, "Denials"),
    ("Prior Auth Denials 2025", "CALCULATE ( [Prior Auth Denials], DimDate[Year] = 2025 )", INT, "Denials"),
    ("Prior Auth YoY %",
     "DIVIDE ( [Prior Auth Denials 2025] - [Prior Auth Denials 2024], [Prior Auth Denials 2024] )", PCT, "Denials"),
    ("Denial Rate (complete)",
     "// December 2025 is left out: most of its claims are still pending\n"
     "CALCULATE ( [Denial Rate], KEEPFILTERS ( DimDate[Date] < DATE ( 2025, 12, 1 ) ) )", PCT, "Rates"),
    ("Denied Share of Billed", "DIVIDE ( [Denied Billed $], [Total Billed] )", PCT, "Money"),
    ("Reason Colour",
     'IF ( SELECTEDVALUE ( claims_clean[denial_reason] ) = "Missing prior authorization", "#FB7185", "#7C4A5E" )',
     None, "Denials"),
    ("In-Network Denial Rate", 'CALCULATE ( [Denial Rate], providers_clean[network_status] = "In-Network" )', PCT, "Rates"),
    ("Out-of-Network Denial Rate", 'CALCULATE ( [Denial Rate], providers_clean[network_status] = "Out-of-Network" )',
     PCT, "Rates"),
    ("Denials 2024", "CALCULATE ( [Denied Claims], DimDate[Year] = 2024 )", INT, "Denials"),
    ("Denials 2025", "CALCULATE ( [Denied Claims], DimDate[Year] = 2025 )", INT, "Denials"),
    ("Denials YoY %", "DIVIDE ( [Denials 2025] - [Denials 2024], [Denials 2024] )", "+0%;-0%;0%", "Denials"),
    ("Flagged Providers",
     "COUNTROWS ( FILTER ( VALUES ( providers_clean[provider_name] ), [Excess Denial (pts)] >= 10 ) )", INT, "Providers"),
    ("Flagged Denied $",
     "SUMX ( FILTER ( VALUES ( providers_clean[provider_name] ), [Excess Denial (pts)] >= 10 ), [Denied Billed $] )",
     MONEY, "Providers"),
    ("Flagged Coding Share",
     "VAR _flagged = FILTER ( VALUES ( providers_clean[provider_name] ), [Excess Denial (pts)] >= 10 )\n"
     "RETURN DIVIDE (\n"
     '    CALCULATE ( [Denied Claims], _flagged, claims_clean[denial_reason] IN { "Coding error", "Duplicate claim" } ),\n'
     "    CALCULATE ( [Denied Claims], _flagged ) )", "0%", "Providers"),
    ("KPI Claims Context",
     'FORMAT ( [Unique Patients], "#,0" ) & " patients"',
     None, "Context"),
    ("KPI Paid Context", 'FORMAT ( [Paid to Billed %], "0%" ) & " of billed charges"', None, "Context"),
    ("KPI Denial Context",
     'FORMAT ( [Denied Claims], "#,0" ) & " of " & FORMAT ( [Decided Claims], "#,0" ) & " decided"', None, "Context"),
    ("KPI Denied Context", 'FORMAT ( [Denied Share of Billed], "0.0%" ) & " of all billed charges"', None, "Context"),
    ("KPI Days Context",
     '"denied: " & FORMAT ( CALCULATE ( [Avg Days to Process], claims_clean[claim_status] = "Denied" ), "0" )\n'
     '    & " days  ·  paid: " & FORMAT ( CALCULATE ( [Avg Days to Process], claims_clean[claim_status] = "Paid" ), "0" )',
     None, "Context"),
    ("KPI Prior Auth Context", '"vs " & FORMAT ( [Prior Auth Denials 2024], "#,0" ) & " in 2024"', None, "Context"),
    ("KPI YoY Context", '"the fastest-growing denial reason"', None, "Context"),
    ("KPI Network Context", '"vs " & FORMAT ( [In-Network Denial Rate], "0.0%" ) & " in-network"', None, "Context"),
    ("KPI Flagged Context", '"10+ points above their peers"', None, "Context"),
    ("KPI Flagged $ Context", 'FORMAT ( DIVIDE ( [Flagged Denied $], [Denied Billed $] ), "0.0%" ) & " of all denied charges"',
     None, "Context"),
    ("KPI Coding Context", '"fixable with a claim scrubber and billing training"', None, "Context"),
]

DATE_DAX = """ADDCOLUMNS (
    CALENDAR ( DATE ( 2024, 1, 1 ), DATE ( 2025, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Month Number", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "mmm yyyy" ),
    "Month Sort", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
    "Quarter", "Q" & QUARTER ( [Date] ),
    "Quarter Label", YEAR ( [Date] ) & " Q" & QUARTER ( [Date] ),
    "Quarter Sort", YEAR ( [Date] ) * 10 + QUARTER ( [Date] )
)"""


def indent(text, tabs):
    return "\n".join("\t" * tabs + line if line else "" for line in text.splitlines())


def column_tmdl(table, name, dtype, fmt, summarize, source=None, extra=()):
    lines = [f"\tcolumn {q(name)}", f"\t\tdataType: {dtype}"]
    if fmt:
        lines.append(f"\t\tformatString: {fmt}")
    lines += [f"\t\tlineageTag: {tag(table, name)}", f"\t\tsummarizeBy: {summarize}"]
    lines += [f"\t\t{e}" for e in extra]
    lines.append(f"\t\tsourceColumn: {source or name}")
    lines.append("")
    lines.append("\t\tannotation SummarizationSetBy = Automatic")
    if dtype == "dateTime":
        lines += ["", "\t\tannotation UnderlyingDateTimeDataType = Date"]
    return "\n".join(lines) + "\n"


def csv_table_tmdl(table, cols, drop=(), measures=()):
    out = [f"table {table}", f"\tlineageTag: {tag(table)}", ""]
    for name, dax, fmt, folder in measures:
        if "\n" in dax:
            out.append(f"\tmeasure {q(name)} =")
            out.append(indent(dax, 3))
        else:
            out.append(f"\tmeasure {q(name)} = {dax}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tdisplayFolder: {folder}")
        out.append(f"\t\tlineageTag: {tag(table, 'measure', name)}")
        out.append("")
    for name, dtype, _, fmt, summarize in cols:
        out.append(column_tmdl(table, name, dtype, fmt, summarize))
    types = ", ".join(f'{{"{c}", {m}}}' for c, _, m, _, _ in cols)
    steps = [
        f'Source = Csv.Document(File.Contents(DataFolder & "{table}.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
    ]
    last = "Promoted"
    if drop:
        steps.append(f"Removed = Table.RemoveColumns(Promoted, {{{', '.join(chr(34) + d + chr(34) for d in drop)}}}),")
        last = "Removed"
    steps.append(f'Typed = Table.TransformColumnTypes({last}, {{{types}}}, "en-US")')
    m = "let\n" + "\n".join("    " + s for s in steps) + "\nin\n    Typed"
    out += [f"\tpartition {table} = m", "\t\tmode: import", "\t\tsource =", indent(m, 4), ""]
    out += ["\tannotation PBI_ResultType = Table", ""]
    return "\n".join(out)


def date_table_tmdl():
    t = "DimDate"
    out = [f"table {t}", f"\tlineageTag: {tag(t)}", "\tdataCategory: Time", ""]
    out.append(column_tmdl(t, "Date", "dateTime", "yyyy-mm-dd", "none", "[Date]", ["isKey", "isNameInferred"]))
    out.append(column_tmdl(t, "Year", "int64", "0", "none", "[Year]", ["isNameInferred"]))
    out.append(column_tmdl(t, "Month Number", "int64", "0", "none", "[Month Number]", ["isNameInferred"]))
    out.append(column_tmdl(t, "Month", "string", None, "none", "[Month]", ["isNameInferred", "sortByColumn: 'Month Sort'"]))
    out.append(column_tmdl(t, "Month Sort", "int64", "0", "none", "[Month Sort]", ["isHidden", "isNameInferred"]))
    out.append(column_tmdl(t, "Quarter", "string", None, "none", "[Quarter]", ["isNameInferred"]))
    out.append(column_tmdl(t, "Quarter Label", "string", None, "none", "[Quarter Label]",
                           ["isNameInferred", "sortByColumn: 'Quarter Sort'"]))
    out.append(column_tmdl(t, "Quarter Sort", "int64", "0", "none", "[Quarter Sort]", ["isHidden", "isNameInferred"]))
    out += [f"\tpartition {t} = calculated", "\t\tmode: import", "\t\tsource =", indent(DATE_DAX, 4), ""]
    return "\n".join(out)


def build_model():
    shutil.rmtree(SM, ignore_errors=True)
    d = SM / "definition"
    write_json(SM / "definition.pbism", {"$schema": S_PBISM, "version": "4.0", "settings": {}})
    write(d / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n")
    tables = ["claims_clean", "patients_clean", "providers_clean", "DimDate"]
    write(d / "model.tmdl", "\n".join([
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: en-US",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        f'annotation PBI_QueryOrder = ["DataFolder","claims_clean","patients_clean","providers_clean"]',
        "",
        *[f"ref table {t}" for t in tables],
        "",
    ]))
    write(d / "expressions.tmdl", "\n".join([
        f'expression DataFolder = "{DATA_FOLDER}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
        f"\tlineageTag: {tag('DataFolder')}",
        "",
        "\tannotation PBI_ResultType = Text",
        "",
    ]))
    write(d / "tables" / "claims_clean.tmdl", csv_table_tmdl("claims_clean", CLAIM_COLS, CLAIM_DROP, MEASURES))
    write(d / "tables" / "patients_clean.tmdl", csv_table_tmdl("patients_clean", PATIENT_COLS))
    write(d / "tables" / "providers_clean.tmdl", csv_table_tmdl("providers_clean", PROVIDER_COLS))
    write(d / "tables" / "DimDate.tmdl", date_table_tmdl())
    rels = [("claims_clean", "patient_id", "patients_clean", "patient_id"),
            ("claims_clean", "provider_id", "providers_clean", "provider_id"),
            ("claims_clean", "service_date", "DimDate", "Date")]
    write(d / "relationships.tmdl", "\n".join(
        f"relationship {tag('rel', a, b)}\n\tfromColumn: {a}.{q(ac)}\n\ttoColumn: {b}.{q(bc)}\n"
        for a, ac, b, bc in rels))


# =====================================================================
# Report (PBIR)
#
# Visual identity: dark "command centre" theme (deliberately unlike the light opioid project):
#   * deep-navy page with glowing colour blooms and a faint network-of-nodes background
#   * dark glass tiles with rounded corners; KPI cards glow in their accent colour
#   * title and pill-shaped page navigation float on the background (no bars, no rail)
#   * one colour, one meaning: cyan = claims / paid, rose = denials / revenue at risk,
#     gold = flagged providers, slate = everything else
# =====================================================================
SKY = BLUE                                     # accent for labels and lines
PAGE_BG, TILE, TILE_2, TILE_BORDER = "#0B1426", "#12203A", "#18294A", "#263A5F"
INK, INK_2 = "#EAF1FB", "#9DB0CE"
TOP = 136                         # content starts under the title and the headline row


def lit(value):
    return {"expr": {"Literal": {"Value": value}}}


def s(text):
    return lit("'" + text.replace("'", "''") + "'")


def solid(hex_):
    return {"solid": {"color": s(hex_)}}


def field(entity, prop, measure=False):
    kind = "Measure" if measure else "Column"
    return {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def C(entity, prop):
    return (entity, prop, False)


def M(prop):
    return (FACT, prop, True)


def MN(prop, name):
    return (FACT, prop, True, name)


LABELS = {"plan_type": "Plan type", "network_status": "Network", "claim_type": "Claim type",
          "provider_name": "Provider", "specialty": "Specialty", "denial_reason": "Denial reason",
          "claim_status": "Claim status"}


def projections(fields):
    out = []
    for e, p, m, *name in fields:
        proj = {"field": field(e, p, m), "queryRef": f"{e}.{p}", "nativeQueryRef": p}
        if name:
            proj["displayName"] = name[0]
        elif p in LABELS:
            proj["displayName"] = LABELS[p]
        out.append(proj)
    return {"projections": out}


def tile(title=None, subtitle=None, background=TILE, border=True, pad=(12, 10, 14, 14), radius=14, glow=None,
         transparency=8):
    objs = {
        "background": [{"properties": {"show": lit("true"), "color": solid(background),
                                       "transparency": lit(f"{transparency}D")}}],
        "border": [{"properties": {"show": lit("true" if border else "false"), "color": solid(TILE_BORDER),
                                   "radius": lit(f"{radius}D")}}],
        "dropShadow": [{"properties": {"show": lit("false")}}] if not glow else [{"properties": {
            "show": lit("true"), "color": solid(glow), "position": s("Outer"), "preset": s("Custom"),
            "transparency": lit("55D"), "shadowBlur": lit("16D"), "shadowSpread": lit("1D"),
            "shadowDistance": lit("0D"), "angle": lit("90D")}}],
        "padding": [{"properties": {"top": lit(f"{pad[0]}D"), "bottom": lit(f"{pad[1]}D"),
                                    "left": lit(f"{pad[2]}D"), "right": lit(f"{pad[3]}D")}}],
        "title": [{"properties": {"show": lit("true" if title else "false"), **({
            "text": s(title), "fontColor": solid(INK), "fontSize": lit("14D"), "bold": lit("true"),
            "fontFamily": s("Segoe UI Semibold")} if title else {})}}],
        "visualHeader": [{"properties": {"background": solid(TILE), "border": solid(TILE),
                                         "foreground": solid(INK_2)}}],
    }
    if subtitle:
        objs["subTitle"] = [{"properties": {"show": lit("true"), "text": s(subtitle), "fontColor": solid(INK_2),
                                            "fontSize": lit("11D"), "titleWrap": lit("true")}}]
    return objs


LABELS_ON = {"labels": [{"properties": {"show": lit("true"), "color": solid(INK), "fontSize": lit("11D"),
                                        "bold": lit("true")}}]}
NO_VALUE_AXIS = {"valueAxis": [{"properties": {"show": lit("false"), "gridlineShow": lit("false")}}]}
QUARTER = C("DimDate", "Quarter Label")


def by_value(entity, prop, value):
    return {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": field(entity, prop),
                                                 "Right": {"Literal": {"Value": f"'{value}'"}}}}}]}


def chart(vtype, roles, title, subtitle=None, sort=None, objects=None):
    objects = dict(objects or {})
    for axis in ("categoryAxis", "valueAxis"):
        if vtype in ("lineChart", "areaChart", "clusteredBarChart", "clusteredColumnChart", "columnChart", "barChart"):
            objects.setdefault(axis, [{"properties": {}}])
            objects[axis][0]["properties"].setdefault("showAxisTitle", lit("false"))
            objects[axis][0]["properties"].setdefault("fontSize", lit("11D"))
            objects[axis][0]["properties"]["labelColor"] = solid(INK_2)
    if "legend" in objects:
        objects["legend"][0]["properties"].setdefault("fontSize", lit("11D"))
        objects["legend"][0]["properties"]["labelColor"] = solid(INK)
    v = {"visualType": vtype,
         "query": {"queryState": {role: projections(f) for role, f in roles.items()}},
         "visualContainerObjects": tile(title, subtitle),
         "drillFilterOtherVisuals": True}
    if sort:
        (e, p, m, *_), direction = sort
        v["query"]["sortDefinition"] = {"sort": [{"field": field(e, p, m), "direction": direction}],
                                        "isDefaultSort": False}
    if objects:
        v["objects"] = objects
    return v


def textbox(paragraphs, background=None, pad=(8, 6, 12, 12), border=False, radius=14, align=None, glow=None):
    def run(t, size, bold, col):
        return {"value": t, "textStyle": {"fontSize": f"{size}pt", "color": col,
                                          **({"fontWeight": "bold"} if bold else {})}}
    paras = [{"textRuns": [run(*r) for r in (p if isinstance(p, list) else [p])],
              **({"horizontalTextAlignment": align} if align else {})} for p in paragraphs if p]
    v = {"visualType": "textbox", "drillFilterOtherVisuals": True,
         "objects": {"general": [{"properties": {"paragraphs": paras}}]}}
    v["visualContainerObjects"] = tile(background=background, border=border, pad=pad, radius=radius, glow=glow) \
        if background else {"background": [{"properties": {"show": lit("false")}}]}
    return v


def card(measure, label, value_colour=INK, size=28, show_label=True, pad=(4, 2, 12, 12)):
    v = {"visualType": "card", "query": {"queryState": {"Values": projections([M(measure)])}},
         "objects": {"labels": [{"properties": {"color": solid(value_colour), "fontSize": lit(f"{size}D"),
                                                "fontFamily": s("Segoe UI Semibold")}}],
                     "categoryLabels": [{"properties": {"show": lit("true" if show_label else "false"),
                                                        "color": solid(INK_2), "fontSize": lit("12D")}}]},
         "visualContainerObjects": {"background": [{"properties": {"show": lit("false")}}],
                                    "padding": [{"properties": {"top": lit(f"{pad[0]}D"), "bottom": lit(f"{pad[1]}D"),
                                                                "left": lit(f"{pad[2]}D"), "right": lit(f"{pad[3]}D")}}]},
         "drillFilterOtherVisuals": True}
    v["query"]["queryState"]["Values"]["projections"][0]["displayName"] = label
    return v


def slicer(entity, prop, title):
    return {"visualType": "slicer", "query": {"queryState": {"Values": projections([C(entity, prop)])}},
            "objects": {"data": [{"properties": {"mode": s("Dropdown")}}],
                        "header": [{"properties": {"text": s(title), "fontColor": solid(INK_2), "bold": lit("true"),
                                                   "fontSize": lit("10D")}}],
                        "items": [{"properties": {"fontSize": lit("11D"), "fontColor": solid(INK),
                                                  "background": solid(TILE_2)}}]},
            "visualContainerObjects": tile(pad=(4, 4, 10, 10)), "drillFilterOtherVisuals": True}


def navigator():
    state = lambda sid, props: {"properties": props, "selector": {"id": sid}}
    return {"visualType": "pageNavigator", "drillFilterOtherVisuals": True,
            "objects": {
                "layout": [{"properties": {"orientation": lit("0D"), "cellPadding": lit("10L")}}],
                "pages": [{"properties": {"showHiddenPages": lit("false"), "showTooltipPages": lit("false")}}],
                "shape": [{"properties": {"tileShape": s("rectangleRounded"), "rectangleRoundedCurve": lit("20L")}}],
                "fill": [state("default", {"show": lit("true"), "fillColor": solid(TILE_2), "transparency": lit("0D")}),
                         state("hover", {"fillColor": solid("#22385F")}),
                         state("selected", {"fillColor": solid(BLUE)})],
                "text": [state("default", {"fontColor": solid(INK_2), "fontSize": lit("11D")}),
                         state("selected", {"fontColor": solid(PAGE_BG), "bold": lit("true")})],
                "outline": [state("default", {"show": lit("true"), "lineColor": solid(TILE_BORDER), "weight": lit("1D")}),
                            state("selected", {"show": lit("false")})],
            },
            "visualContainerObjects": {"background": [{"properties": {"show": lit("false")}}]}}


class Page:
    def __init__(self, name, display):
        self.name, self.display, self.visuals, self.no_filter = name, display, [], []

    def add(self, vid, x, y, w, h, visual):
        n = len(self.visuals)
        self.visuals.append({"$schema": S_VISUAL, "name": vid, "visual": visual,
                             "position": {"x": x, "y": y, "z": n * 1000, "height": h, "width": w,
                                          "tabOrder": n * 1000}})

    def json(self):
        page = {"$schema": S_PAGE, "name": self.name, "displayName": self.display, "displayOption": "FitToPage",
                "height": 720, "width": 1280,
                "objects": {"background": [{"properties": {
                    "color": solid(PAGE_BG), "transparency": lit("0D"),
                    "image": {"image": {"name": s("page_background.png"),
                                        "url": {"expr": {"ResourcePackageItem": {
                                            "PackageName": "RegisteredResources", "PackageType": 1,
                                            "ItemName": "page_background.png"}}},
                                        "scaling": s("Fit")}}}}],
                            "outspace": [{"properties": {"color": solid(PAGE_BG)}}]}}
        if self.no_filter:
            page["visualInteractions"] = [{"source": a, "target": b, "type": "NoFilter"} for a, b in self.no_filter]
        return page


def frame(page, section, headline, filters=True):
    """Title and pill navigation floating on the dark background, then section label + headline + filters."""
    page.add("title", 20, 4, 660, 66, textbox(
        [[("Healthcare Claims ", 20, True, INK), ("Analytics", 20, True, BLUE)],
         ("Where is claim revenue being lost?   ·   50,000 synthetic claims, 2024-2025   ·   Built by Isaac Agyapong",
          9, False, INK_2)], pad=(0, 0, 4, 4)))
    page.add("titleAccentA", 24, 70, 64, 3, textbox([None], background=BLUE, radius=0, pad=(0, 0, 0, 0), border=False))
    page.add("titleAccentB", 92, 70, 28, 3, textbox([None], background=CRIMSON, radius=0, pad=(0, 0, 0, 0), border=False))
    page.add("navigator", 700, 14, 556, 42, navigator())
    page.add("headline", 24, 76, 860 if filters else 1232, 56, textbox(
        [(section.upper(), 10, True, BLUE), (headline, 16, True, INK)], pad=(4, 0, 4, 4)))
    if filters:
        page.add("slicerYear", 896, 78, 176, 52, slicer("DimDate", "Year", "Year"))
        page.add("slicerPlan", 1084, 78, 172, 52, slicer("patients_clean", "plan_type", "Plan type"))


def kpi(page, i, x, y, w, measure, label, context, colour, h=120, size=28):
    # glowing card: the glow colour is the KPI's meaning colour
    page.add(f"kpiTile{i}", x, y, w, h, textbox([None], background=TILE, border=True, glow=colour))
    page.add(f"kpiAccent{i}", x + 16, y + 1, 48, 3, textbox([None], background=colour, radius=0, pad=(0, 0, 0, 0)))
    page.add(f"kpi{i}", x + 8, y + 6, w - 12, h - 38, card(measure, label, value_colour=colour, size=size))
    page.add(f"kpiContext{i}", x + 8, y + h - 34, w - 12, 28,
             card(context, "", value_colour=INK_2, size=11, show_label=False, pad=(0, 0, 12, 12)))


def data_bar(measure, colour):
    return {"properties": {"dataBars": {"positiveColor": solid(colour), "negativeColor": solid(colour),
                                        "axisColor": solid("#FFFFFF"), "reverseDirection": lit("false"),
                                        "hideText": lit("false")}},
            "selector": {"metadata": f"{FACT}.{measure}"}}


TABLE_TEXT = {"values": [{"properties": {"fontSize": lit("11D"), "fontColorPrimary": solid(INK),
                                         "fontColorSecondary": solid(INK), "backColorPrimary": solid(TILE),
                                         "backColorSecondary": solid(TILE_2)}}],
              "columnHeaders": [{"properties": {"fontSize": lit("11D"), "bold": lit("true"), "fontColor": solid(INK_2),
                                                "backColor": solid(TILE)}}],
              "grid": [{"properties": {"gridHorizontal": lit("false"), "outlineColor": solid(TILE_BORDER)}}],
              "total": [{"properties": {"totals": lit("false")}}]}


def build_pages():
    # ---------------------------------------------------------------- 1. Overview
    p1 = Page("overview", "Overview")
    frame(p1, "Executive summary", "1 in 8 decided claims is denied, putting $19M of billed charges at risk")
    kpis = [("Total Claims", "Claims", "KPI Claims Context", BLUE),
            ("Total Paid", "Paid", "KPI Paid Context", BLUE),
            ("Denial Rate", "Denial rate", "KPI Denial Context", CRIMSON),
            ("Denied Billed $", "Billed charges denied", "KPI Denied Context", CRIMSON),
            ("Avg Days to Process", "Avg days to decision", "KPI Days Context", SLATE)]
    for i, (m, label, ctx, colour) in enumerate(kpis):
        kpi(p1, i + 1, 24 + i * 249, TOP, 237, m, label, ctx, colour)
    p1.add("denialTrend", 24, 268, 440, 440, chart(
        "areaChart", {"Category": [QUARTER], "Y": [MN("Denial Rate (complete)", "Denial rate")]},
        "The denial rate climbed through 2025",
        "Denied as a share of decided claims, by quarter (Q4 2025 = Oct-Nov; December mostly pending)",
        sort=(QUARTER, "Ascending"),
        objects={**LABELS_ON,
                 # axis hidden but fixed, so the top label is never clipped
                 "valueAxis": [{"properties": {"show": lit("false"), "gridlineShow": lit("false"),
                                               "start": lit("0.09D"), "end": lit("0.15D")}}],
                 "lineStyles": [{"properties": {"showMarker": lit("true"), "markerSize": lit("7D")}}],
                 "dataPoint": [{"properties": {"fill": solid(CRIMSON)},
                                "selector": {"metadata": f"{FACT}.Denial Rate (complete)"}}]}))
    p1.add("reasonBars", 476, 268, 492, 440, chart(
        "clusteredBarChart", {"Category": [C(FACT, "denial_reason")], "Y": [MN("Denied Billed $", "Denied billed $")]},
        "Missing prior authorization is the #1 cost",
        "Billed charges denied, by denial reason", sort=(M("Denied Billed $"), "Descending"),
        objects={**LABELS_ON, **NO_VALUE_AXIS,
                 "labels": [{"properties": {"show": lit("true"), "color": solid(INK), "fontSize": lit("11D"),
                                            "bold": lit("true"), "labelDisplayUnits": lit("1000000D"),
                                            "labelPrecision": lit("1L")}}],
                 "categoryAxis": [{"properties": {"maxMarginFactor": lit("50L"), "fontSize": lit("11D"),
                                                  "labelColor": solid(INK)}}],
                 "dataPoint": [{"properties": {"fill": {"solid": {"color": {"expr": field(FACT, "Reason Colour", True)}}}},
                                "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}]}))
    status_colours = {"Paid": BLUE, "Denied": CRIMSON, "Pending": "#475569"}
    p1.add("statusDonut", 980, 268, 276, 440, chart(
        "donutChart", {"Category": [C(FACT, "claim_status")], "Y": [MN("Total Claims", "Claims")]},
        "Where every claim ended up", "All 50,000 claims by status",
        objects={"labels": [{"properties": {"show": lit("true"), "labelStyle": s("Category, percent of total"),
                                            "percentageLabelPrecision": lit("0L"), "fontSize": lit("11D"),
                                            "color": solid(INK)}}],
                 "legend": [{"properties": {"show": lit("false")}}],
                 "dataPoint": [{"properties": {"fill": solid(c)}, "selector": by_value(FACT, "claim_status", k)}
                               for k, c in status_colours.items()]}))

    # ---------------------------------------------------------------- 2. Denial drivers
    p2 = Page("denials", "Denial Drivers")
    frame(p2, "Denial drivers", "Prior-auth denials doubled; out-of-network claims are denied 2x as often")
    kpis = [("Prior Auth Denials 2025", "Prior-auth denials, 2025", "KPI Prior Auth Context", CRIMSON),
            ("Prior Auth YoY %", "Change from 2024", "KPI YoY Context", CRIMSON),
            ("Out-of-Network Denial Rate", "Out-of-network denial rate", "KPI Network Context", CRIMSON),
            ("Denied Billed $", "Billed charges denied", "KPI Denied Context", CRIMSON)]
    for i, (m, label, ctx, colour) in enumerate(kpis):
        kpi(p2, i + 1, 24 + i * 311, TOP, 299, m, label, ctx, colour)
    p2.add("priorAuthQuarters", 24, 268, 600, 440, chart(
        "clusteredColumnChart", {"Category": [QUARTER], "Y": [MN("Prior Auth Denials", "Prior-auth denials")]},
        "Missing prior-authorization denials doubled in 2025",
        "Denied claims with reason 'missing prior authorization', by quarter", sort=(QUARTER, "Ascending"),
        objects={**LABELS_ON, **NO_VALUE_AXIS, "dataPoint": [{"properties": {"fill": solid(CRIMSON)}}]}))
    network_colours = {"In-Network": BLUE, "Out-of-Network": CRIMSON}
    p2.add("planNetwork", 636, 268, 620, 216, chart(
        "clusteredBarChart", {"Category": [C("patients_clean", "plan_type")],
                              "Series": [C("providers_clean", "network_status")], "Y": [MN("Denial Rate", "Denial rate")]},
        "Out-of-network claims are denied about 2x as often", "Denial rate by plan type and provider network",
        objects={**LABELS_ON, **NO_VALUE_AXIS,
                 "legend": [{"properties": {"show": lit("true"), "position": s("TopRight"), "showTitle": lit("false")}}],
                 "dataPoint": [{"properties": {"fill": solid(c)}, "selector": by_value("providers_clean", "network_status", k)}
                               for k, c in network_colours.items()]}))
    p2.add("reasonTable", 636, 496, 620, 212, chart(
        "tableEx", {"Values": [C(FACT, "denial_reason"), MN("Denials 2024", "2024"), MN("Denials 2025", "2025"),
                               MN("Denials YoY %", "Change"), MN("Denied Billed $", "Denied $")]},
        "Denials by reason, 2024 vs. 2025", None, sort=(M("Denied Billed $"), "Descending"),
        objects={**TABLE_TEXT, "columnFormatting": [data_bar("Denied Billed $", "#8A3A4C")]}))

    # ---------------------------------------------------------------- 3. Providers
    p3 = Page("providers", "Providers")
    frame(p3, "Provider scorecard", "Three providers deny far above their peers, mostly from coding and duplicate errors")
    kpis = [("Flagged Providers", "Providers flagged", "KPI Flagged Context", AMBER),
            ("Flagged Denied $", "Billed charges denied at flagged providers", "KPI Flagged $ Context", AMBER),
            ("Flagged Coding Share", "of their denials are coding or duplicate errors", "KPI Coding Context", AMBER)]
    for i, (m, label, ctx, colour) in enumerate(kpis):
        kpi(p3, i + 1, 24 + i * 415, TOP, 403, m, label, ctx, colour)
    p3.add("topProviders", 24, 268, 560, 440, chart(
        "clusteredBarChart", {"Category": [C("providers_clean", "provider_name")],

                              "Y": [MN("Top 10 Excess (pts)", "Points above peers")]},
        "Denial rate above peers: top 10 providers",
        "Percentage points above providers with the same claim type and network (amber = 10+ points)",
        sort=(M("Top 10 Excess (pts)"), "Descending"),
        objects={**LABELS_ON, **NO_VALUE_AXIS,
                 "categoryAxis": [{"properties": {"maxMarginFactor": lit("45L"), "fontSize": lit("11D"),
                                                  "labelColor": solid(INK)}}],
                 "dataPoint": [{"properties": {"fill": {"solid": {"color": {"expr": field(FACT, "Excess Colour", True)}}}},
                                "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}]}))
    p3.add("providerTable", 596, 268, 660, 440, chart(
        "tableEx", {"Values": [C("providers_clean", "provider_name"), C("providers_clean", "specialty"),
                               MN("Denial Rate", "Denial rate"), MN("Peer Denial Rate", "Peer rate"),
                               MN("Excess Denial (pts)", "Pts above peers")]},
        "Every provider vs. its peers", None, sort=(M("Excess Denial (pts)"), "Descending"),
        objects={**TABLE_TEXT, "columnFormatting": [data_bar("Excess Denial (pts)", "#8A6A1C")]}))
    p3.no_filter += [("topProviders", "providerTable")]

    # ---------------------------------------------------------------- 4. Data notes
    p4 = Page("dataNotes", "Data Notes")
    frame(p4, "Data notes", "Sources, definitions and limitations", filters=False)
    cols = [
        ("Data", ["50,000 synthetic claims (2024-2025), 8,000 patients, 250 providers",
                  "Generated in Python with real-world patterns: seasonality, network effects, a prior-auth policy "
                  "change and three problem providers",
                  "Raw export deliberately messy (duplicates, mixed date formats, missing values); cleaned in Python",
                  "No real patient information is used"]),
        ("Definitions", ["Denial rate = denied / decided (paid + denied) claims; pending excluded",
                         "Denied billed $ = billed charges on denied claims (revenue at risk before appeals)",
                         "Peer rate = denial rate of providers with the same claim type and network status",
                         "Flagged provider = 10+ percentage points above its peer rate"]),
        ("Limitations", ["Synthetic data: patterns are realistic but the numbers are not real",
                         "December 2025 is mostly pending, so trend charts stop at November",
                         "Denied charges are billed amounts, not the amount a payer would have paid",
                         "A flag is a reason to review billing, not proof of wrongdoing"]),
    ]
    for i, (heading, lines) in enumerate(cols):
        x = 24 + i * 415
        p4.add(f"notes{i + 1}", x, TOP, 403, 572, textbox(
            [(heading, 18, True, INK)] + [("•  " + t, 13, False, INK) for t in lines],
            background=TILE, border=True, pad=(18, 12, 20, 20)))
        p4.add(f"notesAccent{i + 1}", x + 18, TOP + 1, 60, 3, textbox([None], background=SKY, radius=0,
                                                                     pad=(0, 0, 0, 0)))
    return [p1, p2, p3, p4]


def build_report():
    shutil.rmtree(RPT, ignore_errors=True)
    d = RPT / "definition"
    write_json(RPT / "definition.pbir", {"$schema": S_PBIR, "version": "4.0",
                                         "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    write_json(d / "version.json", {"$schema": S_VERSION, "version": "2.0.0"})
    write_json(d / "report.json", {
        "$schema": S_REPORT,
        "themeCollection": {
            "baseTheme": {"name": BASE_THEME, "reportVersionAtImport": "5.59", "type": "SharedResources"},
            "customTheme": {"name": CUSTOM_THEME, "reportVersionAtImport": "5.59", "type": "RegisteredResources"},
        },
        "layoutOptimization": "None",
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": BASE_THEME, "path": f"BaseThemes/{BASE_THEME}.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": CUSTOM_THEME, "path": CUSTOM_THEME, "type": "CustomTheme"},
                       {"name": "page_background.png", "path": "page_background.png", "type": "Image"}]},
        ],
    })
    static = RPT / "StaticResources"
    (static / "SharedResources" / "BaseThemes").mkdir(parents=True, exist_ok=True)
    shutil.copy(BASE_THEME_SRC, static / "SharedResources" / "BaseThemes" / f"{BASE_THEME}.json")
    write_json(static / "RegisteredResources" / CUSTOM_THEME, {
        "name": "Claims Portfolio",
        "dataColors": [BLUE, CRIMSON, AMBER, SLATE, "#818CF8", "#34D399", "#F472B6", "#60A5FA"],
        "foreground": "#EAF1FB", "foregroundNeutralSecondary": "#9DB0CE", "background": "#12203A",
        "backgroundLight": "#18294A", "backgroundNeutral": "#263A5F",
        "tableAccent": BLUE, "good": "#0CA30C", "neutral": "#FAB219", "bad": "#D03B3B",
    })
    # page background image (generated by Python/make_background.py)
    subprocess.run([sys.executable, str(ROOT / "Python" / "make_background.py")], check=True)
    shutil.copy(DASH / "assets" / "page_background.png", static / "RegisteredResources" / "page_background.png")
    pages = build_pages()
    write_json(d / "pages" / "pages.json", {"$schema": S_PAGES, "pageOrder": [p.name for p in pages],
                                            "activePageName": pages[0].name})
    for p in pages:
        write_json(d / "pages" / p.name / "page.json", p.json())
        for v in p.visuals:
            write_json(d / "pages" / p.name / "visuals" / v["name"] / "visual.json", v)


def main():
    build_model()
    build_report()
    write_json(DASH / f"{NAME}.pbip", {"$schema": S_PBIP, "version": "1.0",
                                       "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                       "settings": {"enableAutoRecovery": True}})
    print(f"wrote {DASH.relative_to(ROOT)}/{NAME}.pbip")


if __name__ == "__main__":
    main()
