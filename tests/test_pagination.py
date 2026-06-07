import unittest

from common.pagination import fetch_email_accounts_pages, resolve_page_size
from common.account_status import is_disconnected_account


class FakeHTTP:
    def __init__(self, total_accounts, repeat_from_offset=None):
        self.total_accounts = total_accounts
        self.repeat_from_offset = repeat_from_offset
        self.calls = []

    def get_json(self, url, headers=None, params=None):
        self.calls.append(dict(params or {}))
        offset = int(params.get("offset", 0))
        limit = int(params.get("limit", 500))
        read_offset = 0 if self.repeat_from_offset is not None and offset >= self.repeat_from_offset else offset
        rows = [
            {"id": account_id, "from_email": f"user{account_id}@example.com"}
            for account_id in range(read_offset, min(read_offset + limit, self.total_accounts))
        ]
        return {"data": {"email_accounts": rows, "total_count": self.total_accounts}}


class FakeLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass


class PaginationTests(unittest.TestCase):
    def test_fetches_past_seventy_three_full_pages_until_empty_page(self):
        http = FakeHTTP(total_accounts=36_500)

        accounts, diagnostics = fetch_email_accounts_pages(
            http=http,
            url="https://example.test/email-account/get-all",
            headers={},
            page_size=500,
            logger=FakeLogger(),
            endpoint_name="test_all_accounts",
        )

        self.assertEqual(len(accounts), 36_500)
        self.assertEqual(diagnostics.pages_fetched, 73)
        self.assertEqual(len(http.calls), 74)
        self.assertEqual(http.calls[-1]["offset"], 36_500)
        self.assertTrue(diagnostics.empty_page_reached)
        self.assertTrue(diagnostics.pagination_complete)

    def test_clamps_page_size_to_smartlead_limit(self):
        requested, effective, clamped = resolve_page_size(10_000, FakeLogger())

        self.assertEqual(requested, 10_000)
        self.assertEqual(effective, 500)
        self.assertTrue(clamped)

    def test_repeated_page_raises_instead_of_exporting_partial_data(self):
        http = FakeHTTP(total_accounts=36_000, repeat_from_offset=10_000)

        with self.assertRaisesRegex(RuntimeError, "pagination repeated at offset 10000"):
            fetch_email_accounts_pages(
                http=http,
                url="https://example.test/email-account/get-all",
                headers={},
                page_size=500,
                logger=FakeLogger(),
                endpoint_name="test_all_accounts",
            )

    def test_disconnected_filter_requires_both_smtp_and_imap_false(self):
        self.assertTrue(is_disconnected_account({"is_smtp_success": False, "is_imap_success": False}))
        self.assertTrue(is_disconnected_account({"isSmtpSuccess": "false", "isImapSuccess": "false"}))
        self.assertFalse(is_disconnected_account({"is_smtp_success": True, "is_imap_success": False}))
        self.assertFalse(is_disconnected_account({"is_smtp_success": False}))


if __name__ == "__main__":
    unittest.main()
