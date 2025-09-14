import os
from common.utils import make_run_dir, load_config
from common.logging_config import setup_logging
from script_01_fetch_campaigns import fetch_active_campaigns
from script_02_fetch_campaign_accounts import fetch_accounts_per_campaign
from script_03_fetch_all_accounts_internal import fetch_all_accounts_internal
from script_04_fetch_disconnected_internal import fetch_disconnected_accounts_internal
from script_05_compute_unused import compute_and_export

def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    run_dir = make_run_dir(project_root)
    log = setup_logging(os.path.join(run_dir, "logs", "run.log"))

    cfg = load_config(project_root)
    log.info("Starting Smartlead Unused Accounts run")
    log.info(f"Run directory: {run_dir}")

    # Step 1
    active_campaigns = fetch_active_campaigns(project_root, run_dir)

    # Step 2
    mapping_rows, associated_ids, errors2 = fetch_accounts_per_campaign(project_root, run_dir, active_campaigns)

    # Step 3
    all_accounts, errors3 = fetch_all_accounts_internal(project_root, run_dir)

    # Step 4a: disconnected accounts using internal filter
    disconnected_accounts, errors4 = fetch_disconnected_accounts_internal(project_root, run_dir)

    # Step 4b: compute unused and exports
    summary = compute_and_export(project_root, run_dir, all_accounts, mapping_rows, associated_ids, disconnected_accounts)

    # Collect errors summary
    errors_summary = {
        "errors_campaign_account_mapping": len(errors2),
        "errors_all_accounts": len(errors3),
        "errors_disconnected": len(errors4),
    }
    from common.export import export_json, export_csv
    err_rows = []
    for e in errors2:
        err_rows.append({"phase": "campaign_account_mapping", **e})
    for e in errors3:
        err_rows.append({"phase": "all_accounts_internal", **e})
    for e in errors4:
        err_rows.append({"phase": "disconnected_internal", **e})
    export_json(os.path.join(run_dir, "errors.json"), err_rows)
    export_csv(os.path.join(run_dir, "errors.csv"), err_rows)

    log.info(f"Completed run. Summary: {summary}. Errors: {errors_summary}")
    print("Run directory:", run_dir)
    print("Summary:", summary)
    print("Errors:", errors_summary)

if __name__ == "__main__":
    main()