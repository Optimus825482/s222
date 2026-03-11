import unittest

from backend.routes import messaging


class MessagingRoutesIsolationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        messaging._AGENT_MESSAGES.clear()
        messaging._AUTONOMOUS_CONVERSATIONS.clear()
        messaging._POST_TASK_MEETINGS.clear()
        messaging._AUTO_CHAT_CONFIG.clear()
        messaging._AUTO_CHAT_CONFIG[messaging._SYSTEM_USER_ID] = (
            messaging._default_auto_chat_config()
        )
        messaging._auto_chat_running = False
        messaging._auto_chat_task = None

    async def test_agent_messages_are_scoped_to_current_user(self) -> None:
        alice = {"user_id": "alice"}
        bob = {"user_id": "bob"}

        await messaging.send_agent_message("orchestrator", "critic", "alice-msg", alice)
        await messaging.send_agent_message("critic", "orchestrator", "bob-msg", bob)

        alice_messages = await messaging.get_agent_messages(user=alice)
        bob_messages = await messaging.get_agent_messages(user=bob)

        self.assertEqual(alice_messages["total"], 1)
        self.assertEqual(bob_messages["total"], 1)
        self.assertEqual(alice_messages["messages"][0]["content"], "alice-msg")
        self.assertEqual(bob_messages["messages"][0]["content"], "bob-msg")

    async def test_autonomous_config_is_scoped_per_user(self) -> None:
        alice = {"user_id": "alice"}
        bob = {"user_id": "bob"}

        await messaging.update_auto_chat_config(
            messaging.AutoChatConfigRequest(enabled=False, topics=["alice-only"]),
            user=alice,
        )

        alice_config = await messaging.get_auto_chat_config(user=alice)
        bob_config = await messaging.get_auto_chat_config(user=bob)

        self.assertFalse(alice_config["config"]["enabled"])
        self.assertEqual(alice_config["config"]["topics"], ["alice-only"])
        self.assertTrue(bob_config["config"]["enabled"])
        self.assertNotEqual(bob_config["config"]["topics"], ["alice-only"])

    async def test_autonomous_conversations_and_meetings_are_scoped(self) -> None:
        alice = {"user_id": "alice"}
        bob = {"user_id": "bob"}

        await messaging.trigger_autonomous_chat(user=alice)
        await messaging.trigger_post_task_meeting(task_summary="alice-task", user=alice)

        alice_conversations = await messaging.get_autonomous_conversations(user=alice)
        bob_conversations = await messaging.get_autonomous_conversations(user=bob)
        alice_meetings = await messaging.get_post_task_meetings(user=alice)
        bob_meetings = await messaging.get_post_task_meetings(user=bob)

        self.assertEqual(alice_conversations["total"], 1)
        self.assertEqual(bob_conversations["total"], 0)
        self.assertEqual(alice_meetings["total"], 1)
        self.assertEqual(bob_meetings["total"], 0)

    async def test_post_task_auto_chat_uses_explicit_user_scope(self) -> None:
        alice = {"user_id": "alice"}
        await messaging.update_auto_chat_config(
            messaging.AutoChatConfigRequest(topics=["alice-configured-topic"]),
            user=alice,
        )

        result = messaging.trigger_post_task_auto_chat(
            task_summary="alice-summary",
            user_id="alice",
        )

        self.assertIsNotNone(result)
        alice_conversations = await messaging.get_autonomous_conversations(user=alice)
        alice_meetings = await messaging.get_post_task_meetings(user=alice)

        self.assertEqual(alice_conversations["total"], 1)
        self.assertEqual(alice_meetings["total"], 1)
        self.assertEqual(
            alice_conversations["conversations"][0]["user_id"],
            "alice",
        )


if __name__ == "__main__":
    unittest.main()
