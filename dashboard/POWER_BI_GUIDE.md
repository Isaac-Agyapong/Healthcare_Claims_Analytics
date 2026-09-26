# Power BI Dashboard: Build Guide

Estimated time: 45-60 minutes. The finished file goes in this folder as
`Healthcare_Claims_Dashboard.pbix`, and a screenshot of each page goes in `Image/`.

All measures are in [`measures.dax`](measures.dax).

---

## 1. Load the data (5 min)

1. Open **Power BI Desktop** → **Get data** → **Text/CSV**.
2. Load these three files from `Data/clean/`:
   - `claims_clean.csv`
   - `patients_clean.csv`
   - `providers_clean.csv`
3. Click **Transform data** (opens Power Query) and, in `claims_clean`:
   - Remove columns `plan_type`, `specialty` and `network_status`. They already exist in the
     dimension tables, and removing them forces the report to use the relationships (a proper star schema).
   - Check the types: dates → **Date**, money columns → **Fixed decimal number**, `cpt_code` → **Text**.
4. **Close & Apply**.

## 2. Build the model (5 min)

1. **Modeling → New table** → paste the `Date` table from the bottom of `measures.dax`.
   Then **Table tools → Mark as date table** and pick the `Date` column.
2. Select `Date[Month]` → **Column tools → Sort by column → Month Sort**.
3. In **Model view**, create these relationships (all many-to-one, single direction):

| From (many)                    | To (one)                     |
|--------------------------------|------------------------------|
| `claims_clean[patient_id]`     | `patients_clean[patient_id]` |
| `claims_clean[provider_id]`    | `providers_clean[provider_id]` |
| `claims_clean[service_date]`   | `Date[Date]`                 |

```
            patients_clean
                  │ 1
                  │
 Date ─1────*─ claims_clean ─*────1─ providers_clean
```

4. **Home → Enter data** → name the table `_Measures` → **Load**. Add every measure from
   `measures.dax` to it (**New measure**, paste, Enter). Set formats:
   rates → Percentage (1 decimal); money → Currency (0 decimals).

## 3. Theme (2 min)

**View → Themes → Customize current theme** → Name and colours:
`#2A78D6` (blue), `#EB6834` (orange), `#1BAF7A` (aqua). Page background `#FCFCFB`.
Keep blue for "normal" and orange for "problem", consistently on every page.

## 4. Page 1: Executive Overview

| Visual | Fields | Notes |
|--------|--------|-------|
| 5 × **Card** (top row) | `Total Claims`, `Total Paid`, `Denial Rate`, `Denied Billed $`, `Avg Days to Process` | Card (new) visual; put `Denial Rate Subtitle` as the reference label on the denial card |
| **Line chart** | X: `Date[Month]`, Y: `Total Claims` | Title: *Monthly claim volume* |
| **Line chart** | X: `Date[Month]`, Y: `Denial Rate`, Legend: `claims_clean[claim_type]` | Title: *Denial rate by claim type*. Filter out Dec 2025 (mostly pending) |
| **Bar chart** | Y: `denial_reason`, X: `Denied Billed $` | Filter `claim_status = Denied`; sort descending |
| **Slicers** | `Date[Year]`, `patients_clean[plan_type]`, `providers_clean[network_status]` | Put them in one row above the visuals |

## 5. Page 2: Denial Deep Dive

| Visual | Fields | Notes |
|--------|--------|-------|
| **Matrix** | Rows: `denial_reason`; Columns: `Date[Year]`; Values: `Denied Claims` | Add `Denials YoY %` as a second value; conditional-format it with a colour scale |
| **Clustered column** | X: `plan_type`, Legend: `network_status`, Y: `Denial Rate` | Data labels on. This is the out-of-network story |
| **Line chart** | X: `Date[Month]`, Y: `Denied Claims`, Legend: `denial_reason` | Keep only *Missing prior authorization* and *Coding error* via the filter pane |
| **Card** | `Denials YoY %` filtered to *Missing prior authorization* | The headline: prior-auth denials roughly doubled |

## 6. Page 3: Provider Scorecard

| Visual | Fields | Notes |
|--------|--------|-------|
| **Table** | `provider_name`, `specialty`, `network_status`, `Decided Claims`, `Denial Rate`, `Peer Denial Rate`, `Excess Denial (pts)`, `Denied Billed $` | Visual-level filter: `Decided Claims` ≥ 100. Sort by `Excess Denial (pts)` descending. Conditional-format `Excess Denial (pts)` with a diverging colour scale (blue → white → orange) |
| **Bar chart** | Y: `provider_name`, X: `Excess Denial (pts)` | Top N filter = 10 by `Excess Denial (pts)`. **Format → Bars → fx** → Field value → `Excess Colour` |
| **Treemap** | Group: `specialty`, Values: `Total Paid` | Shows that hospitals account for about 70% of paid dollars |

## 7. Finishing touches (5 min)

- Add a text box title on each page, plus a one-line takeaway under it (e.g. *"Prior-auth denials up 99% YoY"*).
- **Edit interactions** so the slicers filter every visual.
- Add a **tooltip page** or turn on tooltips showing `Total Claims` and `Denied Billed $`.
- Save as `dashboard/Healthcare_Claims_Dashboard.pbix`.
- **File → Export → Export to PDF**, or take screenshots of each page and save them as
  `Image/powerbi_page1.png`, `Image/powerbi_page2.png` and `Image/powerbi_page3.png`. The README already links to these names.

## Numbers to check against

If your visuals match these (all data, no filters), the model is right:

| Measure | Expected |
|---------|----------|
| Total Claims | 50,000 |
| Total Paid | $47,571,952 |
| Denial Rate | 12.2% |
| Denied Billed $ | $19,162,951 |
| Silver Partners, Excess Denial (pts) | 25.3 |
| Prior-auth denials 2024 → 2025 | 438 → 870 |
