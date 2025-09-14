import os
from typing import List, Dict, Any, Tuple
from common.logging_config import setup_logging
from common.http import HTTPClient
from common.export import export_csv, export_json
from common.utils import load_config

def _internal_headers(bearer: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {bearer}",
        "Accept": "application/json"
    }

def fetch_disconnected_accounts_internal(project_root: str, run_dir: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cfg = load_config(project_root)
    bearer = cfg["smartlead"]["internal_bearer_token"]
    base = cfg["smartlead"]["internal_email_accounts_base_url"].rstrip("/")
    chunk = int(cfg["smartlead"].get("internal_page_size", 10000))
    log = setup_logging(os.path.join(run_dir, "logs", "run.log"))
    http = HTTPClient(logger=log, max_calls_per_window=cfg["limits"]["max_calls"], window_seconds=cfg["limits"]["window_seconds"])

    all_bad: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    offset = 0
    page_num = 0
    while True:
        url = f"{base}/get-total-email-accounts"
        params = {
            "offset": offset,
            "limit": chunk,
            "isImapSuccess": "false",
            "isSmtpSuccess": "false"
        }
        try:
            payload = http.get_json(url, headers=_internal_headers(bearer), params=params)
            data = payload.get("data", {}) if isinstance(payload, dict) else {}
            page = data.get("email_accounts") or []
            if not isinstance(page, list):
                raise RuntimeError("Unexpected internal disconnected accounts payload")
            all_bad.extend(page)
            log.info(f"Fetched disconnected accounts page {page_num} with {len(page)} rows (offset {offset})")
            if len(page) < chunk:
                break
            offset += chunk
            page_num += 1
        except Exception as e:
            log.error(f"Internal disconnected fetch failed at offset {offset}: {e}")
            errors.append({"endpoint": "internal_disconnected", "offset": offset, "error": str(e)})
            break

    # de-duplicate by id
    dedup = {}
    for a in all_bad:
        aid = a.get("id")
        if aid is not None:
            dedup[aid] = a
    all_bad = list(dedup.values())

    export_json(os.path.join(run_dir, "04_disconnected_accounts.json"), all_bad)
    export_csv(os.path.join(run_dir, "04_disconnected_accounts.csv"), all_bad)
    export_json(os.path.join(run_dir, "04_disconnected_errors.json"), errors)
    export_csv(os.path.join(run_dir, "04_disconnected_errors.csv"), errors)
    log.info(f"Total disconnected accounts fetched: {len(all_bad)}")
    return all_bad, errors

if __name__ == "__main__":
    from common.utils import make_run_dir
    project_root = os.path.dirname(os.path.dirname(__file__))
    run_dir = make_run_dir(project_root)
    fetch_disconnected_accounts_internal(project_root, run_dir)