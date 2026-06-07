from typing import Any, Dict, Optional

SMTP_STATUS_KEYS = ("is_smtp_success", "isSmtpSuccess", "smtp_success")
IMAP_STATUS_KEYS = ("is_imap_success", "isImapSuccess", "imap_success")


def is_false(value: Any) -> bool:
    if isinstance(value, bool):
        return value is False
    if value is None:
        return False
    return str(value).strip().lower() in {"false", "0", "no", "n"}


def first_present(account: Dict[str, Any], keys) -> Optional[Any]:
    for key in keys:
        if key in account:
            return account.get(key)
    return None


def is_disconnected_account(account: Dict[str, Any]) -> bool:
    """Disconnected means both SMTP and IMAP success flags are explicitly false."""
    smtp_value = first_present(account, SMTP_STATUS_KEYS)
    imap_value = first_present(account, IMAP_STATUS_KEYS)
    return is_false(smtp_value) and is_false(imap_value)
