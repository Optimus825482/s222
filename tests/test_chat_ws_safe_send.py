import inspect
import unittest

from backend.routes import chat_ws


class ChatWSSafeSendRegressionTests(unittest.TestCase):
    def test_safe_ws_send_logs_retry_and_exhaustion_with_counter(self) -> None:
        source = inspect.getsource(chat_ws.ws_chat)
        self.assertIn('"ws.send.failed.retrying"', source)
        self.assertIn('"ws.send.failed.exhausted"', source)
        self.assertIn('"ws_send_failures_total"', source)
        self.assertIn('ws.state.ws_send_failures', source)

    def test_safe_ws_send_enriches_event_context_from_payload(self) -> None:
        source = inspect.getsource(chat_ws.ws_chat)
        self.assertIn('"type": data.get("type")', source)
        self.assertIn('"event": data.get("event")', source)
        self.assertIn('**(event_context or {})', source)

    def test_run_level_telemetry_is_emitted_for_required_events(self) -> None:
        source = inspect.getsource(chat_ws.ws_chat)
        self.assertIn('event="run.start"', source)
        self.assertIn('event="run.progress"', source)
        self.assertIn('event="run.result"', source)
        self.assertIn('event="run.error"', source)
        self.assertIn('event="run.post_task_meeting"', source)
        self.assertIn('event="run.final_report"', source)

    def test_run_telemetry_masks_user_id(self) -> None:
        source = inspect.getsource(chat_ws.ws_chat)
        self.assertIn('"user_id_masked": _mask_user_id(effective_user_id)', source)


if __name__ == "__main__":
    unittest.main()
