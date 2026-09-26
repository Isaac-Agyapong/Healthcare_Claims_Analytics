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

BLUE, ORANGE, AQUA, GREY = "#2A78D6", "#EB6834", "#1BAF7A", "#C3C2B7"
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
    ("Excess Colour", f'IF ( [Excess Denial (pts)] >= 10, "{ORANGE}", "{GREY}" )', None, "Providers"),
    ("Avg Days to Process", "AVERAGE ( claims_clean[days_to_process] )", "0.0", "Time"),
    ("Prior Auth Denials",
     'CALCULATE ( [Denied Claims], claims_clean[denial_reason] = "Missing prior authorization" )', INT, "Denials"),
    ("Other Denials", "[Denied Claims] - [Prior Auth Denials]", INT, "Denials"),
    ("Prior Auth Denials 2024", "CALCULATE ( [Prior Auth Denials], DimDate[Year] = 2024 )", INT, "Denials"),
    ("Prior Auth Denials 2025", "CALCULATE ( [Prior Auth Denials], DimDate[Year] = 2025 )", INT, "Denials"),
    ("Prior Auth YoY %",
     "DIVIDE ( [Prior Auth Denials 2025] - [Prior Auth Denials 2024], [Prior Auth Denials 2024] )", PCT, "Denials"),
]

DATE_DAX = """ADDCOLUMNS (
    CALENDAR ( DATE ( 2024, 1, 1 ), DATE ( 2025, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Month Number", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "mmm yyyy" ),
    "Month Sort", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
    "Quarter", "Q" & QUARTER ( [Date] )
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
# =====================================================================
def lit(value):
    return {"expr": {"Literal": {"Value": value}}}


def s(text):
    return lit("'" + text.replace("'", "''") + "'")


def colour(hex_):
    return {"solid": {"color": s(hex_)}}


def field(entity, prop, measure=False):
    kind = "Measure" if measure else "Column"
    return {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def C(entity, prop):
    return (entity, prop, False)


def M(prop):
    return (FACT, prop, True)


LABELS = {"plan_type": "Plan type", "network_status": "Network", "claim_type": "Claim type",
          "provider_name": "Provider", "specialty": "Specialty", "denial_reason": "Denial reason"}


def projections(fields):
    out = []
    for e, p, m in fields:
        proj = {"field": field(e, p, m), "queryRef": f"{e}.{p}", "nativeQueryRef": p}
        if p in LABELS:
            proj["displayName"] = LABELS[p]
        out.append(proj)
    return {"projections": out}


def container_title(text, show=True):
    props = {"show": lit("true" if show else "false")}
    if show:
        props["text"] = s(text)
    return {"title": [{"properties": props}]}


class Page:
    def __init__(self, name, display):
        self.name, self.display, self.visuals = name, display, []

    def add(self, vid, x, y, w, h, visual):
        self.visuals.append({
            "$schema": S_VISUAL, "name": vid,
            "position": {"x": x, "y": y, "z": len(self.visuals) * 1000, "height": h, "width": w,
                         "tabOrder": len(self.visuals) * 1000},
            "visual": visual,
        })


AXIS_TITLES_OFF = {"categoryAxis": [{"properties": {"showAxisTitle": lit("false")}}],
                   "valueAxis": [{"properties": {"showAxisTitle": lit("false")}}]}


def chart(vtype, roles, title, sort=None, objects=None):
    if vtype in ("lineChart", "clusteredBarChart", "clusteredColumnChart"):
        objects = {**AXIS_TITLES_OFF, **(objects or {})}
    v = {"visualType": vtype,
         "query": {"queryState": {role: projections(f) for role, f in roles.items()}},
         "visualContainerObjects": container_title(title),
         "drillFilterOtherVisuals": True}
    if sort:
        (e, p, m), direction = sort
        v["query"]["sortDefinition"] = {"sort": [{"field": field(e, p, m), "direction": direction}],
                                        "isDefaultSort": False}
    if objects:
        v["objects"] = objects
    return v


def textbox(text, size, bold=False, colour_hex="#0B0B0B"):
    style = {"fontSize": f"{size}pt", "color": colour_hex}
    if bold:
        style["fontWeight"] = "bold"
    return {"visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": text, "textStyle": style}]}]}}]},
            "drillFilterOtherVisuals": True}


def card(measure, label):
    return {"visualType": "card",
            "query": {"queryState": {"Values": projections([M(measure)])}},
            "objects": {"categoryLabels": [{"properties": {"show": lit("true")}}]},
            "visualContainerObjects": container_title(label, show=False),
            "drillFilterOtherVisuals": True}


def slicer(entity, prop, title):
    return {"visualType": "slicer",
            "query": {"queryState": {"Values": projections([C(entity, prop)])}},
            "objects": {"data": [{"properties": {"mode": s("Dropdown")}}],
                        "header": [{"properties": {"text": s(title)}}]},
            "visualContainerObjects": container_title(title, show=False),
            "drillFilterOtherVisuals": True}


LABELS_ON = {"labels": [{"properties": {"show": lit("true")}}]}
MONTH = C("DimDate", "Month")


def header(page, title, subtitle):
    page.add("title", 24, 4, 1000, 56, textbox(title, 20, bold=True))
    page.add("subtitle", 24, 50, 1200, 34, textbox(subtitle, 11, colour_hex="#52514E"))


def slicer_row(page, y=84):
    page.add("slicerYear", 24, y, 200, 64, slicer("DimDate", "Year", "Year"))
    page.add("slicerPlan", 236, y, 200, 64, slicer("patients_clean", "plan_type", "Plan type"))
    page.add("slicerNetwork", 448, y, 200, 64, slicer("providers_clean", "network_status", "Network"))
    page.add("slicerClaimType", 660, y, 200, 64, slicer(FACT, "claim_type", "Claim type"))


def build_pages():
    # ---- Page 1: Executive overview
    p1 = Page("executiveOverview", "Executive Overview")
    header(p1, "Healthcare Claims: Executive Overview",
           "Where is claim revenue being lost? 50,000 claims, 2024-2025 (synthetic data)")
    slicer_row(p1)
    kpis = [("Total Claims", "Total claims"), ("Total Paid", "Total paid"), ("Denial Rate", "Denial rate"),
            ("Denied Billed $", "Denied billed $"), ("Avg Days to Process", "Avg days to process")]
    for i, (m, label) in enumerate(kpis):
        p1.add(f"kpi{i + 1}", 24 + i * 248, 150, 236, 108, card(m, label))
    p1.add("volumeTrend", 24, 266, 612, 194, chart(
        "lineChart", {"Category": [MONTH], "Y": [M("Total Claims")]}, "Monthly claim volume",
        sort=(MONTH, "Ascending"),
        objects={"valueAxis": [{"properties": {"start": lit("0D"), "showAxisTitle": lit("false")}}]}))
    p1.add("denialTrend", 648, 266, 608, 194, chart(
        "lineChart", {"Category": [MONTH], "Y": [M("Denial Rate (trend)")], "Series": [C(FACT, "claim_type")]},
        "Denial rate by claim type (Dec 2025 excluded: mostly pending)", sort=(MONTH, "Ascending")))
    p1.add("denialReasons", 24, 468, 1232, 244, chart(
        "clusteredBarChart", {"Category": [C(FACT, "denial_reason")], "Y": [M("Denied Billed $")]},
        "Denied billed $ by reason", sort=(M("Denied Billed $"), "Descending"),
        objects={**LABELS_ON, "dataPoint": [{"properties": {"fill": colour(BLUE)}}]}))

    # ---- Page 2: Denial deep dive
    p2 = Page("denialDeepDive", "Denial Deep Dive")
    header(p2, "Denial Deep Dive",
           "Missing prior authorization is the largest and fastest-growing reason; out-of-network claims are denied about 2x as often")
    slicer_row(p2)
    for i, (m, label) in enumerate([("Prior Auth Denials 2024", "Prior-auth denials 2024"),
                                    ("Prior Auth Denials 2025", "Prior-auth denials 2025"),
                                    ("Prior Auth YoY %", "Prior-auth change YoY"),
                                    ("Denied Claims", "All denied claims")]):
        p2.add(f"paCard{i + 1}", 24 + i * 308, 160, 296, 104, card(m, label))
    p2.add("reasonMatrix", 24, 280, 612, 208, chart(
        "pivotTable", {"Rows": [C(FACT, "denial_reason")], "Columns": [C("DimDate", "Year")],
                       "Values": [M("Denied Claims")]}, "Denied claims by reason and year"))
    p2.add("planNetwork", 648, 280, 608, 208, chart(
        "clusteredColumnChart", {"Category": [C("patients_clean", "plan_type")], "Y": [M("Denial Rate")],
                                 "Series": [C("providers_clean", "network_status")]},
        "Denial rate by plan type and network status", objects=LABELS_ON))
    p2.add("priorAuthTrend", 24, 496, 1232, 208, chart(
        "lineChart", {"Category": [MONTH], "Y": [M("Prior Auth Denials"), M("Other Denials")]},
        "Monthly denials: missing prior authorization vs all other reasons (Nov-Dec 2025 partly pending)", sort=(MONTH, "Ascending")))

    # ---- Page 3: Provider scorecard
    p3 = Page("providerScorecard", "Provider Scorecard")
    header(p3, "Provider Scorecard",
           "Each provider vs peers with the same claim type and network status. Orange = 10+ points above peers")
    slicer_row(p3)
    fill_by_measure = {"solid": {"color": {"expr": field(FACT, "Excess Colour", measure=True)}}}
    p3.add("topProviders", 24, 160, 500, 544, chart(
        "clusteredBarChart", {"Category": [C("providers_clean", "provider_name")], "Y": [M("Top 10 Excess (pts)")]},
        "Top 10 providers: denial rate above peers (percentage points)",
        sort=(M("Top 10 Excess (pts)"), "Descending"),
        objects={**LABELS_ON, "dataPoint": [{"properties": {"fill": fill_by_measure},
                                             "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}]}))
    p3.add("providerTable", 536, 160, 720, 344, chart(
        "tableEx", {"Values": [C("providers_clean", "provider_name"), C("providers_clean", "specialty"),
                               C("providers_clean", "network_status"), M("Decided Claims"), M("Denial Rate"),
                               M("Peer Denial Rate"), M("Excess Denial (pts)"), M("Denied Billed $")]},
        "All providers", sort=(M("Excess Denial (pts)"), "Descending")))
    p3.add("paidTreemap", 536, 512, 720, 192, chart(
        "treemap", {"Group": [C("providers_clean", "specialty")], "Values": [M("Total Paid")]},
        "Total paid by specialty"))
    return [p1, p2, p3]


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
             "items": [{"name": CUSTOM_THEME, "path": CUSTOM_THEME, "type": "CustomTheme"}]},
        ],
    })
    static = RPT / "StaticResources"
    (static / "SharedResources" / "BaseThemes").mkdir(parents=True, exist_ok=True)
    shutil.copy(BASE_THEME_SRC, static / "SharedResources" / "BaseThemes" / f"{BASE_THEME}.json")
    write_json(static / "RegisteredResources" / CUSTOM_THEME, {
        "name": "Claims Portfolio",
        "dataColors": [BLUE, ORANGE, AQUA, "#EDA100", "#E87BA4", "#008300", "#4A3AA7", "#E34948"],
        "foreground": "#0B0B0B", "foregroundNeutralSecondary": "#52514E", "background": "#FFFFFF",
        "tableAccent": BLUE, "good": "#0CA30C", "neutral": "#FAB219", "bad": "#D03B3B",
    })
    pages = build_pages()
    write_json(d / "pages" / "pages.json", {"$schema": S_PAGES, "pageOrder": [p.name for p in pages],
                                            "activePageName": pages[0].name})
    for p in pages:
        write_json(d / "pages" / p.name / "page.json", {
            "$schema": S_PAGE, "name": p.name, "displayName": p.display,
            "displayOption": "FitToPage", "height": 720, "width": 1280})
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
