# Power BI Dashboard

The dashboard is saved as a **Power BI Project (PBIP)**: the model and report are stored as readable
text files instead of a single binary `.pbix`, so every table, relationship, measure and visual can be
reviewed on GitHub and tracked in version control.

```
dashboard/
├── Healthcare_Claims.pbip                  <- open this in Power BI Desktop
├── Healthcare_Claims.SemanticModel/        <- data model (TMDL)
│   └── definition/
│       ├── tables/claims_clean.tmdl        <- fact table + all 22 measures
│       ├── tables/DimDate.tmdl             <- calculated date table
│       ├── relationships.tmdl
│       └── expressions.tmdl                <- DataFolder parameter (path to the CSVs)
├── Healthcare_Claims.Report/               <- 3 report pages, one JSON file per visual (PBIR)
└── measures.dax                            <- all measures in one readable file
```

## Open it

1. Open `Healthcare_Claims.pbip` in **Power BI Desktop** (2024 or later).
2. If you cloned the repo to a different folder: **Home → Transform data → Edit parameters** and set
   `DataFolder` to the full path of your `Data\clean\` folder, including the trailing `\`.
3. Click **Refresh**.

## Model

Star schema: one fact table and three dimensions, all many-to-one with single-direction filtering.

```
            patients_clean
                  │ 1
                  │ *
 DimDate ─1────*─ claims_clean ─*────1─ providers_clean
```

- Plan type, specialty and network status are dropped from the fact table in Power Query, so visuals use the dimension tables through the relationships.
- `DimDate` is a calculated table marked as the date table (used by `TOTALYTD`).
- Auto date/time is off.

## Pages

| Page | Visuals | Question it answers |
|---|---|---|
| **Executive Overview** | 5 KPI cards, claim volume trend, denial rate by claim type, denied $ by reason, 4 slicers | How big is the problem and is it growing? |
| **Denial Deep Dive** | Prior-auth cards (2024 vs 2025), reason × year matrix, plan × network denial rates, prior-auth vs other denials trend | Why are claims denied? |
| **Provider Scorecard** | Top 10 providers vs peers (orange = 10+ pts above peers), full provider table, paid by specialty treemap | Who should we act on? |

## DAX highlights

- **Peer benchmarking:** `Peer Denial Rate` uses `REMOVEFILTERS` plus `SELECTEDVALUE` to compare each provider
  with every provider of the same claim type and network status.
- **Dynamic Top N without a visual filter:** `Excess Rank` (`RANKX` over `ALLSELECTED`) feeds `Top 10 Excess (pts)`.
- **Conditional formatting from a measure:** `Excess Colour` returns a hex code that drives the bar colours.
- **Handling incomplete data:** `Denial Rate (trend)` blanks out December 2025, when most claims are still pending.
- **Time intelligence:** `Paid YTD` uses `TOTALYTD` over the marked date table.

## Validation

With no filters, the report matches the SQL and Excel outputs exactly:

| Measure | Value |
|---|---|
| Total Claims | 50,000 |
| Total Paid | $47,571,952 |
| Denial Rate | 12.2% |
| Denied Billed $ | $19,162,951 |
| Prior-auth denials 2024 → 2025 | 438 → 870 (+98.6%) |
| Silver Partners, excess over peers | +25.3 pts |

## Rebuilding from code

`Python/build_powerbi_project.py` generates the whole PBIP from Python. Running it **replaces** this
folder, including the saved data cache, so open the report and click Refresh afterwards.
