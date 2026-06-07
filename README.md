# Smartlead Unused Accounts Toolkit

Purpose: find inboxes added to Smartlead that are not connected to any ACTIVE campaign, export clean datasets, and keep a simple history of counts.

## What this gives you
- Active campaigns list.
- Mapping of ACTIVE campaigns to email accounts.
- Complete email-account inventory fetched with Smartlead's 500-row page size.
- Pagination that keeps going past 73 pages and only stops when Smartlead returns an empty page or a partial final page.
- Hard failure instead of partial exports if the API repeats a page or reports a total greater than the unique accounts fetched.
- Disconnected accounts derived from the complete all-account inventory when SMTP and IMAP success flags are both false.
- Four final exports:
  1. associated unique accounts,
  2. non-associated unused accounts,
  3. full list of ACTIVE campaigns with mapped accounts,
  4. disconnected accounts inside the associated set.
- Rate limiting and retries with increasing exponential backoff.
- Daily-run friendly folder structure under `runs/<UTC timestamp>`.
- History of counts in `history.json` at the project root.

## Setup

This project requires **Python 3.10 or higher**.

### 1. Create and activate a virtual environment

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Smartlead access

Copy `config.example.json` to `config.json` and fill in your credentials.

Important settings:

- `email_accounts_page_size`: defaults to `500`, which is Smartlead's max page size for the email-account inventory endpoint. Values above 500 are clamped to 500 and logged.
- `limits.max_calls` / `limits.window_seconds`: default example is `800` calls per `60` seconds.
- `email_accounts_endpoint_path`: defaults to `get-total-email-accounts` for the existing Smartlead email-account base URL.

## Run

```bash
python run_all.py
```

Outputs land in `runs/<timestamp>/` as CSV and JSON. A `summary.json`, diagnostics JSON files, and error CSV/JSON files are included for convenience.

## Pagination behavior

The all-accounts fetch is not capped at 10k accounts or at 73 pages. It requests pages with `limit=500`, advances by the number of rows actually returned, and continues until one of these completion signals appears:

1. Smartlead returns an empty page.
2. Smartlead returns a partial page with fewer than 500 accounts.

The run also records Smartlead total-count metadata when the API provides it. The run fails instead of exporting partial results if Smartlead repeats a page or reports a total count higher than the unique accounts fetched.

## Exported files and their meaning

### `01_active_campaigns.csv`
- List of all campaigns in your Smartlead account currently marked as ACTIVE.
- Only accounts tied to these campaigns are considered “in use” for this analysis.

### `02_campaign_account_mapping.csv`
- Full mapping of each ACTIVE campaign to the email accounts attached to it.
- Helps you see exactly which inboxes are being used by each campaign.

### `02_associated_unique_ids.json`
- Deduplicated list of account IDs connected to at least one ACTIVE campaign.
- This is the baseline set compared against all accounts to find unused inboxes.

### `03_all_accounts_internal.csv`
- Complete list of all email accounts fetched in 500-row pages.
- This is the universe of accounts you are paying for, whether they are used or not.

### `03_all_accounts_diagnostics.json`
- Fetch diagnostics including page size, pages fetched, rows fetched, unique IDs, total count if Smartlead provides one, and pagination completion status.

### `04_disconnected_accounts.csv`
- Accounts where both SMTP and IMAP success flags are explicitly false.
- These inboxes cannot send or receive reliably and should be fixed or decommissioned.

### `04_disconnected_diagnostics.json`
- Shows whether disconnected accounts were derived locally from the complete all-account inventory or fetched with filtered pagination.

### `A_associated_unique.csv`
- Full details of all accounts currently attached to ACTIVE campaigns.
- This is your in-use inventory.

### `B_unused_accounts.csv`
- Full details of all accounts not attached to any ACTIVE campaign.
- This is your wasted inventory.

### `C_active_campaign_account_mapping.csv`
- Same as `02_campaign_account_mapping.csv`, included as part of the final report bundle.

### `D_disconnected_within_associated.csv`
- The overlap between accounts tied to ACTIVE campaigns and accounts that are disconnected.
- These are highest-risk inboxes because they are supposed to be sending in campaigns but are broken.

### `summary.json`
- Key counts plus fetch diagnostics, including whether pagination completed successfully.

## Scheduling

Use cron or your scheduler to invoke `python run_all.py` daily. The toolkit is stateless except for `history.json`.
