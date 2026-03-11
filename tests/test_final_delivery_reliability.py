import inspect
import unittest

from backend.routes import chat_ws, messaging


class FinalDeliveryReliabilityTests(unittest.TestCase):
    def test_ws_delivery_event_id_uses_run_and_event_type(self) -> None:
        event_id = messaging._build_ws_delivery_event_id("run-123", "final_report")
        self.assertEqual(event_id, "run-123:final_report")

    def test_ws_delivery_event_id_falls_back_for_empty_values(self) -> None:
        event_id = messaging._build_ws_delivery_event_id("", "")
        self.assertEqual(event_id, "unknown_run:unknown_event")

    def test_ws_chat_uses_deterministic_event_id_for_final_report_and_post_task_meeting(self) -> None:
        source = inspect.getsource(chat_ws.ws_chat)
        self.assertIn('_build_ws_delivery_event_id(', source)
        self.assertIn('"final_report"', source)
        self.assertIn('"post_task_meeting"', source)
        self.assertIn('idempotency_key=final_report_event_id', source)
        self.assertIn('idempotency_key=post_task_event_id', source)


if __name__ == "__main__":
    unittest.main()
