import os
from typing import Dict, Any, List, Set
from common.logging_config import setup_logging
from common.http import HTTPClient
from common.export import export_csv, export_json
from common.utils import load_config

def fetch_accounts_per_campaign(project_root: str, run_dir: str, active_campaigns: List[Dict[str, Any]]):
    cfg = load_config(project_root)
    api_key = cfg["smartlead"]["api_key"]
    base = cfg["smartlead"]["campaigns_base_url"].rstrip("/")
    log = setup_logging(os.path.join(run_dir, "logs", "run.log"))
    http = HTTPClient(logger=log, max_calls_per_window=cfg["limits"]["max_calls"], window_seconds=cfg["limits"]["window_seconds"])

    mapping_rows: List[Dict[str, Any]] = []
    assoc_ids: Set[int] = set()
    errors: List[Dict[str, Any]] = []

    for camp in active_campaigns:
        cid = camp["id"]
        cname = camp.get("name")
        url = f"{base}/{cid}/email-accounts"
        params = {"api_key": api_key}
        try:
            accounts = http.get_json(url, params=params)
            if not isinstance(accounts, list):
                raise RuntimeError("Unexpected email-accounts payload, expected a list")
            for acc in accounts:
                # Attach campaign metadata
                row = {"campaign_id": cid, "campaign_name": cname}
                if isinstance(acc, dict):
                    row.update(acc)
                    if "id" in acc:
                        try:
                            assoc_ids.add(int(acc["id"]))
                        except Exception:
                            pass
                mapping_rows.append(row)
        except Exception as e:
            log.error(f"Failed fetching accounts for campaign {cid}: {e}")
            errors.append({"endpoint": "campaign-email-accounts", "campaign_id": cid, "error": str(e)})

    # Exports
    export_json(os.path.join(run_dir, "02_campaign_account_mapping.json"), mapping_rows)
    export_csv(os.path.join(run_dir, "02_campaign_account_mapping.csv"), mapping_rows)
    export_json(os.path.join(run_dir, "02_associated_unique_ids.json"), sorted(list(assoc_ids)))
    export_json(os.path.join(run_dir, "02_errors.json"), errors)
    export_csv(os.path.join(run_dir, "02_errors.csv"), errors)

    return mapping_rows, assoc_ids, errors

if __name__ == "__main__":
    from common.utils import make_run_dir
    from script_01_fetch_campaigns import fetch_active_campaigns
    project_root = os.path.dirname(os.path.dirname(__file__))
    run_dir = make_run_dir(project_root)
    active = fetch_active_campaigns(project_root, run_dir)
    fetch_accounts_per_campaign(project_root, run_dir, active)