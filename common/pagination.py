from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

MAX_EMAIL_ACCOUNTS_PAGE_SIZE = 500
DEFAULT_EMAIL_ACCOUNTS_PAGE_SIZE = 500

TOTAL_KEYS = (
    "total",
    "total_count",
    "count",
    "totalEmailAccounts",
    "total_email_accounts",
    "total_email_account_count",
)


class PaginationError(RuntimeError):
    def __init__(self, message: str, diagnostics: "PaginationDiagnostics"):
        super().__init__(message)
        self.diagnostics = diagnostics


@dataclass
class PaginationDiagnostics:
    endpoint: str
    requested_page_size: int
    effective_page_size: int
    pages_fetched: int = 0
    rows_fetched: int = 0
    unique_ids: int = 0
    duplicate_ids: int = 0
    empty_page_reached: bool = False
    partial_page_reached: bool = False
    repeated_page_detected: bool = False
    expected_total_count: Optional[int] = None
    final_offset: int = 0
    filters: Dict[str, Any] = field(default_factory=dict)
    limit_clamped: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "requested_page_size": self.requested_page_size,
            "effective_page_size": self.effective_page_size,
            "pages_fetched": self.pages_fetched,
            "rows_fetched": self.rows_fetched,
            "unique_ids": self.unique_ids,
            "duplicate_ids": self.duplicate_ids,
            "empty_page_reached": self.empty_page_reached,
            "partial_page_reached": self.partial_page_reached,
            "repeated_page_detected": self.repeated_page_detected,
            "expected_total_count": self.expected_total_count,
            "final_offset": self.final_offset,
            "filters": self.filters,
            "limit_clamped": self.limit_clamped,
            "pagination_complete": self.pagination_complete,
        }

    @property
    def pagination_complete(self) -> bool:
        if self.repeated_page_detected:
            return False
        if self.expected_total_count is not None and self.unique_ids < self.expected_total_count:
            return False
        return self.empty_page_reached or self.partial_page_reached


def resolve_page_size(configured_size: Any, logger=None) -> Tuple[int, int, bool]:
    """Return (requested, effective, clamped) for Smartlead email-account pages."""
    requested = int(configured_size or DEFAULT_EMAIL_ACCOUNTS_PAGE_SIZE)
    if requested <= 0:
        raise ValueError("Email accounts page size must be greater than zero")
    effective = min(requested, MAX_EMAIL_ACCOUNTS_PAGE_SIZE)
    clamped = requested != effective
    if clamped and logger is not None:
        logger.warning(
            "Configured email accounts page size %s exceeds Smartlead's max %s; using %s",
            requested,
            MAX_EMAIL_ACCOUNTS_PAGE_SIZE,
            effective,
        )
    return requested, effective, clamped


def extract_email_accounts_page(payload: Any) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Extract a Smartlead email-account page and optional total from common payload shapes."""
    total = None
    data = payload.get("data", {}) if isinstance(payload, dict) else {}

    for container in (payload, data):
        if isinstance(container, dict):
            for key in TOTAL_KEYS:
                value = container.get(key)
                if value is not None:
                    try:
                        total = int(value)
                        break
                    except (TypeError, ValueError):
                        pass
            if total is not None:
                break

    page: Any = []
    if isinstance(data, dict):
        page = data.get("email_accounts") or data.get("accounts") or data.get("items") or []
    elif isinstance(data, list):
        page = data
    elif isinstance(payload, list):
        page = payload
    elif isinstance(payload, dict):
        page = payload.get("email_accounts") or payload.get("accounts") or payload.get("items") or []

    if not isinstance(page, list):
        raise RuntimeError("Unexpected email accounts payload: expected a list of accounts")
    return page, total


def fetch_email_accounts_pages(
    *,
    http,
    url: str,
    headers: Dict[str, str],
    page_size: int,
    logger,
    base_params: Optional[Dict[str, Any]] = None,
    endpoint_name: str = "email_accounts",
) -> Tuple[List[Dict[str, Any]], PaginationDiagnostics]:
    """Fetch email-account pages until Smartlead returns an empty or partial page.

    There is deliberately no max-pages guard: large workspaces should continue past 73
    pages and only stop when the API stops returning new account content. A repeated
    page is treated as an error instead of a successful stop so capped/broken
    pagination cannot silently produce partial outputs.
    """
    requested, effective, clamped = resolve_page_size(page_size, logger)
    params_without_paging = dict(base_params or {})
    diagnostics = PaginationDiagnostics(
        endpoint=endpoint_name,
        requested_page_size=requested,
        effective_page_size=effective,
        filters={k: v for k, v in params_without_paging.items() if k not in {"offset", "limit"}},
        limit_clamped=clamped,
    )

    accounts: List[Dict[str, Any]] = []
    seen_ids: Set[Any] = set()
    offset = 0

    while True:
        params = {**params_without_paging, "offset": offset, "limit": effective}
        payload = http.get_json(url, headers=headers, params=params)
        page, total = extract_email_accounts_page(payload)
        if total is not None:
            diagnostics.expected_total_count = total

        page_len = len(page)
        if page_len == 0:
            diagnostics.empty_page_reached = True
            diagnostics.final_offset = offset
            logger.info("Fetched %s empty page at offset %s; pagination complete", endpoint_name, offset)
            break

        current_ids = [a.get("id") for a in page if isinstance(a, dict) and a.get("id") is not None]
        current_id_set = set(current_ids)
        new_ids = current_id_set - seen_ids
        if current_id_set and not new_ids:
            diagnostics.repeated_page_detected = True
            diagnostics.final_offset = offset
            raise PaginationError(
                f"{endpoint_name} pagination repeated at offset {offset} after "
                f"{len(seen_ids)} unique accounts; refusing to export partial data",
                diagnostics,
            )

        accounts.extend(page)
        diagnostics.pages_fetched += 1
        diagnostics.rows_fetched += page_len
        duplicate_count = len(current_ids) - len(new_ids)
        diagnostics.duplicate_ids += max(0, duplicate_count)
        seen_ids.update(current_id_set)
        diagnostics.unique_ids = len(seen_ids)
        diagnostics.final_offset = offset + page_len

        logger.info(
            "Fetched %s page %s with %s rows (offset %s, unique_ids %s)",
            endpoint_name,
            diagnostics.pages_fetched - 1,
            page_len,
            offset,
            diagnostics.unique_ids,
        )

        if page_len < effective:
            diagnostics.partial_page_reached = True
            break

        offset += page_len

    if diagnostics.expected_total_count is not None and diagnostics.unique_ids < diagnostics.expected_total_count:
        raise PaginationError(
            f"{endpoint_name} fetched {diagnostics.unique_ids} unique accounts but API reported "
            f"{diagnostics.expected_total_count}; refusing to export partial data",
            diagnostics,
        )

    return accounts, diagnostics
