import os
from typing import List, Dict, Any, Tuple
from common.logging_config import setup_logging
from common.http import HTTPClient
from common.export import export_csv, export_json
from common.utils import load_config
from common.pagination import (
    DEFAULT_EMAIL_ACCOUNTS_PAGE_SIZE,
    PaginationError,
    fetch_email_accounts_pages,
)

def _internal_headers(bearer: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {bearer}",
        "Accept": "application/json"
    }

def fetch_all_accounts_internal(project_root: str, run_dir: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    cfg = load_config(project_root)
    bearer = cfg["smartlead"]["internal_bearer_token"]
    base = cfg["smartlead"]["internal_email_accounts_base_url"].rstrip("/")
    page_size = int(
        cfg["smartlead"].get("email_accounts_page_size", DEFAULT_EMAIL_ACCOUNTS_PAGE_SIZE)
    )
    endpoint_path = cfg["smartlead"].get("email_accounts_endpoint_path", "get-total-email-accounts").strip("/")
    log = setup_logging(os.path.join(run_dir, "logs", "run.log"))
    http = HTTPClient(logger=log, max_calls_per_window=cfg["limits"]["max_calls"], window_seconds=cfg["limits"]["window_seconds"])

    errors: List[Dict[str, Any]] = []
    diagnostics: Dict[str, Any] = {}
    url = f"{base}/{endpoint_path}"
    try:
        fetched_accounts, pagination = fetch_email_accounts_pages(
            http=http,
            url=url,
            headers=_internal_headers(bearer),
            page_size=page_size,
            logger=log,
            endpoint_name="internal_all_accounts",
        )
        diagnostics = pagination.to_dict()
    except PaginationError as e:
        diagnostics = e.diagnostics.to_dict()
        log.error(f"Internal accounts fetch failed: {e}")
        errors.append({"endpoint": "internal_all_accounts", "offset": diagnostics.get("final_offset", 0), "error": str(e)})
        export_json(os.path.join(run_dir, "03_all_accounts_diagnostics.json"), diagnostics)
        export_json(os.path.join(run_dir, "03_all_accounts_errors.json"), errors)
        export_csv(os.path.join(run_dir, "03_all_accounts_errors.csv"), errors)
        raise
    except Exception as e:
        log.error(f"Internal accounts fetch failed: {e}")
        errors.append({"endpoint": "internal_all_accounts", "offset": diagnostics.get("final_offset", 0), "error": str(e)})
        export_json(os.path.join(run_dir, "03_all_accounts_diagnostics.json"), diagnostics)
        export_json(os.path.join(run_dir, "03_all_accounts_errors.json"), errors)
        export_csv(os.path.join(run_dir, "03_all_accounts_errors.csv"), errors)
        raise

    # de-duplicate by id
    dedup = {}
    for a in fetched_accounts:
        aid = a.get("id")
        if aid is not None:
            dedup[aid] = a
    all_accounts = list(dedup.values())
    diagnostics["deduped_accounts_count"] = len(all_accounts)

    export_json(os.path.join(run_dir, "03_all_accounts_internal.json"), all_accounts)
    export_csv(os.path.join(run_dir, "03_all_accounts_internal.csv"), all_accounts)
    export_json(os.path.join(run_dir, "03_all_accounts_diagnostics.json"), diagnostics)
    export_json(os.path.join(run_dir, "03_all_accounts_errors.json"), errors)
    export_csv(os.path.join(run_dir, "03_all_accounts_errors.csv"), errors)
    log.info(f"Total unique accounts fetched: {len(all_accounts)}")
    return all_accounts, errors, diagnostics

if __name__ == "__main__":
    from common.utils import make_run_dir
    project_root = os.path.dirname(os.path.abspath(__file__))
    run_dir = make_run_dir(project_root)
    fetch_all_accounts_internal(project_root, run_dir)
