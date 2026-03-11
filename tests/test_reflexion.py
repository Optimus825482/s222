import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from tools import reflexion


class ReflexionTests(unittest.IsolatedAsyncioTestCase):
    def test_parse_evaluation_plain_json(self) -> None:
        payload = {
            "scores": {
                "accuracy": 4,
                "completeness": 4,
                "clarity": 5,
                "actionability": 4,
                "depth": 4,
            },
            "total": 21,
            "weaknesses": ["minor gaps"],
            "improvements": ["add examples"],
        }

        parsed = reflexion.parse_evaluation(json.dumps(payload))

        self.assertEqual(parsed, payload)

    def test_parse_evaluation_from_markdown_codefence(self) -> None:
        text = (
            "I evaluated the response below:\n"
            "```json\n"
            "{\n"
            '  "scores": {"accuracy": 3, "completeness": 3, "clarity": 3, "actionability": 3, "depth": 3},\n'
            '  "total": 15,\n'
            '  "weaknesses": ["too generic"],\n'
            '  "improvements": ["be specific"]\n'
            "}\n"
            "```"
        )

        parsed = reflexion.parse_evaluation(text)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["total"], 15)
        self.assertEqual(parsed["scores"]["accuracy"], 3)

    def test_parse_evaluation_from_prose_wrapped_json(self) -> None:
        text = (
            "Summary first. "
            "{\"scores\": {\"accuracy\": 2, \"completeness\": 2, \"clarity\": 2, "
            "\"actionability\": 2, \"depth\": 2}, \"total\": 10, "
            "\"weaknesses\": [\"missing details\"], \"improvements\": [\"add steps\"]} "
            "End."
        )

        parsed = reflexion.parse_evaluation(text)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["total"], 10)

    async def test_evaluate_and_improve_uses_call_llm_dict_content(self) -> None:
        evaluation_payload = {
            "scores": {
                "accuracy": 5,
                "completeness": 5,
                "clarity": 5,
                "actionability": 5,
                "depth": 5,
            },
            "total": 25,
            "weaknesses": [],
            "improvements": [],
        }

        agent = SimpleNamespace(
            role=SimpleNamespace(value="critic"),
            call_llm=AsyncMock(return_value={"content": json.dumps(evaluation_payload)}),
        )

        with (
            patch("config.REFLEXION_ENABLED", True),
            patch("config.REFLEXION_AGENTS", []),
            patch("config.REFLEXION_AUTO_IMPROVE", False),
            patch("tools.reflexion.save_reflection_result"),
            patch("tools.reflexion.save_reflection_insight"),
        ):
            final_response, evaluation = await reflexion.evaluate_and_improve(
                agent,
                question="What is observability?",
                response="Initial response",
            )

        self.assertEqual(final_response, "Initial response")
        self.assertEqual(evaluation, evaluation_payload)
        self.assertEqual(agent.call_llm.await_count, 1)

    async def test_evaluate_and_improve_fallback_on_invalid_payload(self) -> None:
        agent = SimpleNamespace(
            role=SimpleNamespace(value="critic"),
            call_llm=AsyncMock(return_value={"content": "not-json"}),
        )

        with (
            patch("config.REFLEXION_ENABLED", True),
            patch("config.REFLEXION_AGENTS", []),
            patch("config.REFLEXION_AUTO_IMPROVE", True),
            patch("tools.reflexion.save_reflection_result"),
            patch("tools.reflexion.save_reflection_insight"),
            self.assertLogs("tools.reflexion", level="WARNING") as logs,
        ):
            final_response, evaluation = await reflexion.evaluate_and_improve(
                agent,
                question="Q",
                response="R",
            )

        self.assertEqual(final_response, "R")
        self.assertTrue(evaluation["fallback_used"])
        self.assertIn("evaluation_parse_failed", evaluation["weaknesses"][0])
        self.assertTrue(any("parse/validation failed" in msg for msg in logs.output))
        self.assertEqual(agent.call_llm.await_count, 1)

    async def test_evaluate_and_improve_generates_improved_response(self) -> None:
        low_eval = {
            "scores": {
                "accuracy": 1,
                "completeness": 1,
                "clarity": 1,
                "actionability": 1,
                "depth": 1,
            },
            "total": 5,
            "weaknesses": ["too shallow"],
            "improvements": ["add concrete steps"],
        }

        agent = SimpleNamespace(
            role=SimpleNamespace(value="critic"),
            call_llm=AsyncMock(
                side_effect=[
                    {"content": json.dumps(low_eval)},
                    {"content": "Improved response with concrete steps."},
                ]
            ),
        )

        with (
            patch("config.REFLEXION_ENABLED", True),
            patch("config.REFLEXION_AGENTS", []),
            patch("config.REFLEXION_AUTO_IMPROVE", True),
            patch("tools.reflexion.save_reflection_result"),
            patch("tools.reflexion.save_reflection_insight"),
        ):
            final_response, evaluation = await reflexion.evaluate_and_improve(
                agent,
                question="How to deploy?",
                response="Bad response",
                threshold=3.5,
                max_iterations=1,
            )

        self.assertEqual(final_response, "Improved response with concrete steps.")
        self.assertEqual(evaluation, low_eval)
        self.assertEqual(agent.call_llm.await_count, 2)


if __name__ == "__main__":
    unittest.main()
