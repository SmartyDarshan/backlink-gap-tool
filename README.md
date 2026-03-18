# Backlink Gap Tool

A simple Streamlit app for comparing your backlink domains against competitor backlink domains.

## What it does

- Upload your backlink export from Ahrefs or Google Sheets
- Upload one or more competitor backlink exports
- Map the correct columns in the UI
- Normalize domains to root domains
- Find the domains competitors have but you do not
- Export a final Excel report with:
  - uncovered domains
  - DR
  - competitor name(s)
  - competitor count per domain

## Best use case

This is useful for SEO and outreach teams that want a quick backlink gap report without manually cleaning sheets every time.

## Input formats supported

- CSV
- XLSX
- XLS

## Recommended columns

### Your file
Use any column that contains:
- referring domain
- root domain
- URL

### Competitor files
Use:
- a domain or URL column
- a DR or Domain Rating column if available

## How to run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the app

```bash
streamlit run app.py
```

## Output sheets

### Summary
Quick totals for your domains, competitor domains, and uncovered domains.

### Uncovered Domains
Final actionable list with:
- Domain
- DR
- Competitor
- Linked Competitor Count

### All Competitor Domains
Merged and cleaned list of competitor domains.

### Your Domains Cleaned
Cleaned version of your uploaded domains for validation.

## Tips for your team

- Keep one file per competitor if possible
- Use exports that include Domain Rating
- If the wrong column is auto-selected, change it in the dropdown
- The app removes common prefixes like `www.` and converts URLs to root domains

## Suggested next version

If you want, this can be upgraded later with:
- a Google Sheets connector
- bulk competitor tagging
- auto-column detection for Ahrefs exports
- filters by language, country, link type, or traffic
- priority scoring using DR + competitor count
