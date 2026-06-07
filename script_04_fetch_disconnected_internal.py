import os
from typing import List, Dict, Any, Tuple, Optional
from common.logging_config import setup_logging
from common.http import HTTPClient
from common.export import export_csv, export_json
from common.utils import load_config
from common.pagination import DEFAULT_EMAIL_ACCOUNTS_PAGE_SIZE, PaginationError, fetch_email_accounts_pages
from common.account_status import is_disconnected_account


def _internal_headers(bearer: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {bearer}",
        "Accept": "application/json"
    }


def fetch_disconnected_accounts_internal(
    project_root: str,
    run_dir: str,
    all_accounts: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    cfg = load_config(project_root)
    log = setup_logging(os.path.join(run_dir, "logs", "run.log"))
    errors: List[Dict[str, Any]] = []

    if all_accounts is not None:
        all_bad = [a for a in all_accounts if isinstance(a, dict) and is_disconnected_account(a)]
        diagnostics = {
            "source": "local_filter_from_all_accounts",
            "all_accounts_input_count": len(all_accounts),
            "disconnected_accounts_count": len(all_bad),
            "pagination_complete": True,
        }
        log.info(f"Derived disconnected accounts locally from all accounts: {len(all_bad)}")
    else:
        bearer = cfg["smartlead"]["internal_bearer_token"]
        base = cfg["smartlead"]["internal_email_accounts_base_url"].rstrip("/")
        page_size = int(
            cfg["smartlead"].get("email_accounts_page_size", DEFAULT_EMAIL_ACCOUNTS_PAGE_SIZE)
        )
        endpoint_path = cfg["smartlead"].get("email_accounts_endpoint_path", "get-total-email-accounts").strip("/")
        http = HTTPClient(logger=log, max_calls_per_window=cfg["limits"]["max_calls"], window_seconds=cfg["limits"]["window_seconds"])
        url = f"{base}/{endpoint_path}"
        try:
            fetched_bad, pagination = fetch_email_accounts_pages(
                http=http,
                url=url,
                headers=_internal_headers(bearer),
                page_size=page_size,
                logger=log,
                base_params={"isImapSuccess": "false", "isSmtpSuccess": "false"},
                endpoint_name="internal_disconnected",
            )
            diagnostics = pagination.to_dict()
        except PaginationError as e:
            diagnostics = e.diagnostics.to_dict()
            log.error(f"Internal disconnected fetch failed: {e}")
            errors.append({"endpoint": "internal_disconnected", "offset": diagnostics.get("final_offset", 0), "error": str(e)})
            export_json(os.path.join(run_dir, "04_disconnected_diagnostics.json"), diagnostics)
            export_json(os.path.join(run_dir, "04_disconnected_errors.json"), errors)
            export_csv(os.path.join(run_dir, "04_disconnected_errors.csv"), errors)
            raise
        except Exception as e:
            log.error(f"Internal disconnected fetch failed: {e}")
            errors.append({"endpoint": "internal_disconnected", "offset": 0, "error": str(e)})
            export_json(os.path.join(run_dir, "04_disconnected_errors.json"), errors)
            export_csv(os.path.join(run_dir, "04_disconnected_errors.csv"), errors)
            raise

        dedup = {}
        for a in fetched_bad:
            aid = a.get("id")
            if aid is not None:
                dedup[aid] = a
        all_bad = list(dedup.values())
        diagnostics["deduped_accounts_count"] = len(all_bad)

    export_json(os.path.join(run_dir, "04_disconnected_accounts.json"), all_bad)
    export_csv(os.path.join(run_dir, "04_disconnected_accounts.csv"), all_bad)
    export_json(os.path.join(run_dir, "04_disconnected_diagnostics.json"), diagnostics)
    export_json(os.path.join(run_dir, "04_disconnected_errors.json"), errors)
    export_csv(os.path.join(run_dir, "04_disconnected_errors.csv"), errors)
    log.info(f"Total disconnected accounts fetched: {len(all_bad)}")
    return all_bad, errors, diagnostics


if __name__ == "__main__":
    from common.utils import make_run_dir
    project_root = os.path.dirname(os.path.abspath(__file__))
    run_dir = make_run_dir(project_root)
    fetch_disconnected_accounts_internal(project_root, run_dir)
