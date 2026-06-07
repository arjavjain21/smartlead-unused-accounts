import os
from typing import Dict, Any, List, Set, Optional
from common.logging_config import setup_logging
from common.export import export_csv, export_json
from common.utils import update_history

def compute_and_export(project_root: str, run_dir: str,
                       all_accounts: List[Dict[str, Any]],
                       mapping_rows: List[Dict[str, Any]],
                       associated_ids: Set[int],
                       disconnected_accounts: List[Dict[str, Any]],
                       diagnostics: Optional[Dict[str, Any]] = None):
    log = setup_logging(os.path.join(run_dir, "logs", "run.log"))
    diagnostics = diagnostics or {}
    all_accounts_diag = diagnostics.get("all_accounts", {})
    if all_accounts_diag and not all_accounts_diag.get("pagination_complete", False):
        raise RuntimeError("All-accounts pagination did not complete; refusing to compute partial outputs")

    # Build id -> account dict for quick lookups
    all_by_id: Dict[int, Dict[str, Any]] = {}
    for a in all_accounts:
        aid = a.get("id")
        if aid is not None:
            all_by_id[int(aid)] = a

    # Associated unique accounts: restrict to those that actually exist in all accounts
    assoc_existing_ids = [aid for aid in associated_ids if aid in all_by_id]
    missing_associated_ids = sorted(aid for aid in associated_ids if aid not in all_by_id)
    if missing_associated_ids:
        log.warning(
            "Found %s associated account IDs that were not present in the all-accounts inventory",
            len(missing_associated_ids),
        )
    associated_unique = [all_by_id[aid] for aid in sorted(assoc_existing_ids)]

    # Unused: in all accounts but not in associated
    assoc_id_set = set(assoc_existing_ids)
    unused_ids = [aid for aid in all_by_id.keys() if aid not in assoc_id_set]
    unused_accounts = [all_by_id[aid] for aid in sorted(unused_ids)]

    # Disconnected within associated unique
    bad_ids = set()
    for b in disconnected_accounts:
        bid = b.get("id")
        if bid is not None:
            bad_ids.add(int(bid))
    disconnected_associated = [all_by_id[aid] for aid in sorted(assoc_id_set.intersection(bad_ids)) if aid in all_by_id]

    # Export four requested datasets
    export_json(os.path.join(run_dir, "A_associated_unique.json"), associated_unique)
    export_csv(os.path.join(run_dir, "A_associated_unique.csv"), associated_unique)

    export_json(os.path.join(run_dir, "B_unused_accounts.json"), unused_accounts)
    export_csv(os.path.join(run_dir, "B_unused_accounts.csv"), unused_accounts)

    export_json(os.path.join(run_dir, "C_active_campaign_account_mapping.json"), mapping_rows)
    export_csv(os.path.join(run_dir, "C_active_campaign_account_mapping.csv"), mapping_rows)

    export_json(os.path.join(run_dir, "D_disconnected_within_associated.json"), disconnected_associated)
    export_csv(os.path.join(run_dir, "D_disconnected_within_associated.csv"), disconnected_associated)

    # Summary
    summary = {
        "associated_unique_count": len(associated_unique),
        "all_accounts_count": len(all_accounts),
        "unused_accounts_count": len(unused_accounts),
        "disconnected_within_associated_count": len(disconnected_associated),
        "associated_ids_missing_from_all_accounts_count": len(missing_associated_ids),
        "fetch_diagnostics": diagnostics,
    }
    export_json(os.path.join(run_dir, "summary.json"), summary)

    # Update history at project root
    history_entry = {"run_dir": run_dir, **summary}
    update_history(project_root, history_entry)
    log.info(f"Summary: {summary}")
    return summary