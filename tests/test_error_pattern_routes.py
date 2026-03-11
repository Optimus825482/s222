import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.routes import learning_hub, monitoring


class ErrorPatternRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_monitoring_routes_accept_string_pattern_ids(self) -> None:
        fake_analyzer = type(
            "FakeAnalyzer",
            (),
            {
                "resolve_pattern": lambda self, pattern_id, notes="": {
                    "id": pattern_id,
                    "status": "resolved",
                    "notes": notes,
                },
                "suppress_pattern": lambda self, pattern_id: {
                    "id": pattern_id,
                    "status": "suppressed",
                },
            },
        )()

        with patch.object(monitoring, "_error_analyzer", fake_analyzer):
            resolved = await monitoring.resolve_error_pattern(
                "pattern-text-id",
                monitoring.ResolvePatternRequest(resolution_notes="fixed"),
                user={"user_id": "u1"},
            )
            suppressed = await monitoring.suppress_error_pattern(
                "pattern-text-id",
                user={"user_id": "u1"},
            )

        self.assertTrue(resolved["resolved"])
        self.assertEqual(resolved["pattern_id"], "pattern-text-id")
        self.assertTrue(suppressed["suppressed"])
        self.assertEqual(suppressed["pattern_id"], "pattern-text-id")

    async def test_monitoring_routes_raise_404_on_error_dict(self) -> None:
        fake_analyzer = type(
            "FakeAnalyzer",
            (),
            {
                "resolve_pattern": lambda self, pattern_id, notes="": {
                    "error": "missing"
                },
                "suppress_pattern": lambda self, pattern_id: {"error": "missing"},
            },
        )()

        with patch.object(monitoring, "_error_analyzer", fake_analyzer):
            with self.assertRaises(HTTPException) as resolve_error:
                await monitoring.resolve_error_pattern(
                    "missing",
                    monitoring.ResolvePatternRequest(resolution_notes="fixed"),
                    user={"user_id": "u1"},
                )
            with self.assertRaises(HTTPException) as suppress_error:
                await monitoring.suppress_error_pattern(
                    "missing",
                    user={"user_id": "u1"},
                )

        self.assertEqual(resolve_error.exception.status_code, 404)
        self.assertEqual(suppress_error.exception.status_code, 404)

    async def test_learning_hub_resolve_raises_404_on_error_dict(self) -> None:
        fake_analyzer = type(
            "FakeAnalyzer",
            (),
            {"resolve_pattern": lambda self, pattern_id: {"error": "missing"}},
        )()

        with patch.object(
            learning_hub, "_get_error_analyzer", return_value=fake_analyzer
        ):
            with self.assertRaises(HTTPException) as resolve_error:
                await learning_hub.resolve_error_pattern(
                    "missing",
                    user={"user_id": "u1"},
                )

        self.assertEqual(resolve_error.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
