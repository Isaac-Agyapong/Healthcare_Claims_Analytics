# Healthcare Claims Analytics: Where Is Claim Revenue Being Lost?

A health plan was losing money to denied claims and didn't know where to start. I analysed 50,000 health insurance
claims from 2024 and 2025 to find out where the money goes and what would fix it. I used Python, SQL, Excel and
Power BI.

> **In short:** $19.2 million in charges were denied. Denials because the provider didn't get approval from the plan
> before treatment (called "prior authorization") **nearly doubled in one year**. Claims from providers outside the
> plan's network are denied **about twice as often**, and three providers make far more billing errors than others
> like them. The project ends with four practical fixes.
>
> **The claims are realistic sample data I generated, not real patients.**

![Power BI dashboard](Image/powerbi_page1.png)

The rest of this page has the details.

---

## Dashboard

A Power BI report with four pages, with year and plan filters on every page. An Excel version is included too.

**Executive summary:** the main numbers, the denial rate each quarter, denied dollars by reason, and claim status
(shown above).

**Why claims are denied:** prior authorization denials by quarter, denial rates by plan and network, and reasons in
2024 against 2025.
![Denial drivers](Image/powerbi_page2.png)

**Provider scorecard:** providers ranked by how far their denial rate sits above similar providers.
![Provider scorecard](Image/powerbi_page3.png)

**Data notes:** where the data comes from and what the words mean.
![Data notes](Image/powerbi_page4.png)

**Excel version** (built with live formulas):
![Excel dashboard](Image/excel_dashboard.png)

## The questions

The plan's team saw denied claims rising but couldn't say where to act first. They asked:

1. How much billed money is being denied, and is it getting worse?
2. Why are claims denied?
3. Which providers, plans and network arrangements cause the most denials?
4. Which fixes would recover the most money?

## What I found

The query behind each number is in [SQL/query_results.md](SQL/query_results.md).

| Finding | Query |
|---|---|
| $19.2 million of billed charges (13.8%) were denied. Overall, 12.2% of claims were denied. | 1 |
| Denials for missing prior authorization almost doubled (up 99%) from 2024 to 2025. They are now the top reason, at 34% of denied dollars. | 3, 4 |
| Hospital stays were denied about 12-15% of the time in 2024, rising to about 20% by late 2025. | 4 |
| Claims from providers outside the network are denied about twice as often (20-25% against 9-12%), on every type of plan. | 5 |
| Three providers have denial rates 19 to 25 points higher than similar providers, mostly because of coding mistakes and duplicate claims. | 6, 7 |
| Claims sent more than 90 days after the visit are always denied ($1.6 million, all preventable). Denied claims also take 23 days to settle, against 13 for the rest. | 11, 12 |

## What could help

1. **Check for prior authorization when the visit is booked,** for hospital stays and imaging. This is the biggest
   and fastest-growing loss (about $6.4 million).
2. **Audit and train the three flagged providers,** and use software that checks claims for coding mistakes and
   duplicates before they are sent.
3. **Steer referrals to providers inside the network,** and recruit more providers in the specialties where patients
   most often go outside it.
4. **Send an alert at 60 days** for any visit that hasn't been billed yet. This would stop late-filing denials
   completely.

## The data

| Table | Rows | One row per |
|---|---|---|
| claims | 50,000 | claim |
| patients | 8,000 | member (plan type, age, state) |
| providers | 250 | provider (specialty, in or out of network) |

**The data is sample data, not real patients.** I generated it with [Python/generate_data.py](Python/generate_data.py).
I built in the kinds of patterns real claims have (seasons, network effects, a prior authorization policy change and
a few problem providers), so the same methods work on real data.

I also built in the problems real data has, and fixed them in the cleaning notebook: 750 duplicate rows, two date
formats, inconsistent codes ("F", "female", "Female"), and missing or negative billed amounts.

## Technical details

For readers who want the specifics:

| Step | Tool | Output |
|---|---|---|
| Making the data | Python (NumPy, pandas) | [Python/generate_data.py](Python/generate_data.py) |
| Cleaning | Python, Jupyter | [01_data_cleaning.ipynb](Python/01_data_cleaning.ipynb): removing duplicates, fixing dates, filling gaps, 10 checks |
| Exploring | Python (matplotlib) | [02_exploratory_analysis.ipynb](Python/02_exploratory_analysis.ipynb): 7 charts |
| Database and questions | SQL (SQLite) | [SQL/](SQL/): star schema, data checks, 13 questions and [results](SQL/query_results.md) |
| Spreadsheet | Excel | [Excel/Healthcare_Claims_Analysis.xlsx](Excel/Healthcare_Claims_Analysis.xlsx): formula-driven dashboard and provider scorecard |
| Dashboard | Power BI | [dashboard/](dashboard/): four pages, generated from code |

- **SQL:** joins, CTEs, CASE, conditional sums, window functions (`LAG`, `SUM() OVER`, `AVG() OVER (PARTITION BY)`,
  `ROW_NUMBER`, `DENSE_RANK`, `NTILE`), and a median worked out without a MEDIAN function.
- **Excel:** `COUNTIFS`, `SUMIFS`, `AVERAGE`, running year-to-date totals, tables, data bars, colour scales, filters
  and charts.
- **Power BI:** star-schema model, Power Query with a folder setting, a date table, year-to-date measures
  (`TOTALYTD`), comparison with similar providers (`CALCULATE`, `REMOVEFILTERS`), a Top N ranking (`RANKX`) and
  colours driven by measures. The report is generated from code
  ([Python/build_powerbi_project.py](Python/build_powerbi_project.py)), so all 44 DAX measures can be read on GitHub.

### Charts from the analysis notebook

| | |
|---|---|
| ![](Image/02_denial_rate_trend.png) | ![](Image/03_denials_by_reason.png) |
| ![](Image/04_network_plan_denials.png) | ![](Image/05_provider_outliers.png) |
| ![](Image/06_paid_by_specialty.png) | ![](Image/07_processing_time.png) |

### Files

```
Data/raw/     the messy source files
Data/clean/   cleaned files used by SQL, Excel and Power BI
Python/       data generator, notebooks, database loader, Excel builder
SQL/          tables, data checks, questions and results
Excel/        formula-driven workbook
dashboard/    Power BI project (Healthcare_Claims.pbip)
Image/        charts and screenshots
run_all.py    rebuilds everything
```

### Run it yourself

```bash
pip install -r requirements.txt
python run_all.py
```

This makes the data, runs both notebooks, builds the database, answers every SQL question and rebuilds the Excel
workbook. To see the dashboard, open `dashboard/Healthcare_Claims.pbip` in Power BI Desktop. If you saved the
project in a different folder, go to Transform data > Edit parameters, set `DataFolder` to your `Data\clean\`
folder, then click Refresh.

---

Built by **Isaac Agyapong** · [GitHub](https://github.com/Isaac-Agyapong)
