# Smartlead Unused Accounts Toolkit

Purpose: find inboxes added to Smartlead that are not connected to any ACTIVE campaign, export clean datasets, and keep a simple history of counts.

## What this gives you
- Active campaigns list
- Mapping of ACTIVE campaign to email accounts
- All accounts via internal 10k endpoint, paged by 10k
- Disconnected accounts via internal filters (isImapSuccess=false and isSmtpSuccess=false)
- Four exports you asked for:
  1) associated unique accounts
  2) non-associated unused accounts
  3) full list of ACTIVE campaigns with mapped accounts
  4) disconnected accounts inside the associated set
- Robust rate limiting and retries with exponential backoff
- Daily-run friendly folder structure under `runs/<UTC timestamp>`
- History of counts in `history.json` at the project root

## Setup
1. Create and activate a Python 3.10+ virtualenv.

Here’s how to set up and activate a Python 3.10+ virtual environment before running the toolkit. It works on Linux, macOS, and Windows.

## Setup: Create and Activate a Python 3.10+ Virtual Environment

This project requires **Python 3.10 or higher**. Follow the steps below to create and activate a virtual environment.

### 1. Check your Python version
Make sure Python 3.10+ is installed:
```bash
python3 --version
````

You should see something like:

```
Python 3.10.12
```

If not, install Python 3.10+ first.

---

### 2. Create a virtual environment

Run this in the project root directory (where `requirements.txt` is located):

**Linux / macOS**

```bash
python3 -m venv venv
```

**Windows (PowerShell)**

```powershell
python -m venv venv
```

This creates a folder named `venv` that contains an isolated Python environment.

---

### 3. Activate the virtual environment

**Linux / macOS**

```bash
source venv/bin/activate
```

**Windows (PowerShell)**

```powershell
.\venv\Scripts\Activate
```

Once activated, you should see `(venv)` at the start of your terminal prompt.

---

### 4. Install dependencies

With the virtual environment active, install project dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---
## 5. Run
`python run_all.py`

Outputs land in `runs/<timestamp>/` as CSV and JSON. A `summary.json` and `errors.csv` are included for convenience.

## Notes
- Rate limit defaults to 10 requests per 2 seconds.
- The internal endpoint is used for 10k paging. If Smartlead returns fewer than 10k, the loop stops.
- Disconnected is defined by the internal query `isImapSuccess=false & isSmtpSuccess=false` exactly as you requested. If you want "either fails" instead, adjust script_04 to pass only one of the flags or post-filter the results.

## Scheduling
Use cron or your scheduler to invoke `python run_all.py` daily. The toolkit is stateless except for `history.json`.



## Exported Files and Their Meaning

### `01_active_campaigns.csv`
- **What it is**: List of all campaigns in your Smartlead account that are currently marked as ACTIVE.
- **Why it matters**: Only accounts tied to these campaigns are considered “in use” for the purpose of this analysis.

---

### `02_campaign_account_mapping.csv`
- **What it is**: Full mapping of each ACTIVE campaign to the email accounts attached to it.
- **Why it matters**: Helps you see exactly which inboxes are being used by each campaign.

---

### `02_associated_unique_ids.json`
- **What it is**: Deduplicated list of account IDs connected to at least one ACTIVE campaign.
- **Why it matters**: This is the baseline set we compare against all accounts to find unused ones.

---

### `03_all_accounts_internal.csv`
- **What it is**: Complete list of **all email accounts** in your Smartlead organization, fetched 10,000 at a time from the internal endpoint.
- **Why it matters**: This is the universe of accounts you are paying for, whether they are used or not.

---

### `04_disconnected_accounts.csv`
- **What it is**: All accounts that failed both SMTP and IMAP checks (`isSmtpSuccess = false` and `isImapSuccess = false`).
- **Why it matters**: These inboxes cannot send or receive reliably. They should be fixed or decommissioned.

---

### `A_associated_unique.csv`
- **What it is**: Full details of all accounts currently attached to ACTIVE campaigns.
- **Why it matters**: Your *in-use inventory*. These are the accounts pulling their weight.

---

### `B_unused_accounts.csv`
- **What it is**: Full details of all accounts **not attached** to any ACTIVE campaign.
- **Why it matters**: Your *wasted inventory*. These inboxes are costing money or domain reputation without contributing to campaigns.

---

### `C_active_campaign_account_mapping.csv`
- **What it is**: Same as `02_campaign_account_mapping.csv`, included here for clarity as part of the final report bundle.
- **Why it matters**: Lets you tie back associated accounts to their campaign context.

---

### `D_disconnected_within_associated.csv`
- **What it is**: The overlap between accounts tied to ACTIVE campaigns and accounts that are disconnected (SMTP/IMAP both failing).
- **Why it matters**: These are the highest-risk inboxes. They are *supposed* to be sending in campaigns but are broken.

---

### `summary.json`
- **What it is**: Key counts from the run.
- **Why it matters**: Gives you a quick pulse check on your Smartlead account health without opening the CSVs.

---

## Example Summary Explained

```json
{
  "associated_unique_count": 8272,
  "all_accounts_count": 26802,
  "unused_accounts_count": 18530,
  "disconnected_within_associated_count": 990
}
