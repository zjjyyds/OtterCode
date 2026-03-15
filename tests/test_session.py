from __future__ import annotations

import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ottercode.core.session import SessionStore, SessionStoreError


class SessionStoreTests(unittest.TestCase):
    def test_save_and_load_round_trip(self) -> None:
        with TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "sessions")
            session_id = "sess_test_roundtrip"
            messages = [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
            ]

            path = store.save(session_id, messages)
            loaded = store.load(session_id)

            self.assertTrue(path.exists())
            self.assertEqual(messages, loaded)

    def test_load_missing_session_raises(self) -> None:
        with TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "sessions")
            with self.assertRaises(SessionStoreError):
                store.load("sess_missing")

    def test_list_recent_returns_latest_first(self) -> None:
        with TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "sessions")
            store.save("sess_old", [{"role": "user", "content": "older prompt"}])
            time.sleep(0.01)
            store.save("sess_new", [{"role": "user", "content": "newer prompt"}])

            recent = store.list_recent(limit=2)

            self.assertEqual([item.session_id for item in recent], ["sess_new", "sess_old"])
            self.assertEqual(recent[0].preview, "newer prompt")


if __name__ == "__main__":
    unittest.main()
