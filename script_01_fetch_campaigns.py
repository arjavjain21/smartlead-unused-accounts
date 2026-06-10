import os
from typing import List, Dict, Any
from common.logging_config import setup_logging
from common.http import HTTPClient
from common.export import export_csv, export_json
from common.utils import load_config

def fetch_active_campaigns(project_root: str, run_dir: str) -> List[Dict[str, Any]]:
    cfg = load_config(project_root)
    api_key = cfg["smartlead"]["api_key"]
    base = cfg["smartlead"]["campaigns_base_url"].rstrip("/")
    log = setup_logging(os.path.join(run_dir, "logs", "run.log"))
    http = HTTPClient(logger=log, max_calls_per_window=cfg["limits"]["max_calls"], window_seconds=cfg["limits"]["window_seconds"])

    url = f"{base}/"
    params = {"api_key": api_key}
    log.info("Fetching campaigns")
    data = http.get_json(url, params=params)
    if not isinstance(data, list):
        raise RuntimeError("Unexpected campaigns payload, expected a list")

    active = [c for c in data if str(c.get("status")).upper() == "ACTIVE"]
    out_json = os.path.join(run_dir, "01_active_campaigns.json")
    out_csv = os.path.join(run_dir, "01_active_campaigns.csv")
    export_json(out_json, active)
    export_csv(out_csv, active)
    log.info(f"Active campaigns: {len(active)} written to {out_json}")
    return active

if __name__ == "__main__":
    from common.utils import make_run_dir
    project_root = os.path.dirname(os.path.dirname(__file__))
    run_dir = make_run_dir(project_root)
    fetch_active_campaigns(project_root, run_dir)