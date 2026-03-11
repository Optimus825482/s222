import unittest
from unittest.mock import patch

from tools import workflow_engine


class WorkflowEngineRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_step_failures_abort_workflow(self) -> None:
        workflow = workflow_engine.Workflow(
            workflow_id="wf-parallel-failure",
            name="parallel failure",
            description="parallel branch failures should abort the workflow",
            steps=[
                workflow_engine.WorkflowStep(
                    step_id="fanout",
                    step_type="parallel",
                    parallel_steps=["ok", "boom"],
                    on_error="abort",
                ),
                workflow_engine.WorkflowStep(
                    step_id="ok",
                    step_type="tool_call",
                    tool_name="noop",
                ),
                workflow_engine.WorkflowStep(
                    step_id="boom",
                    step_type="tool_call",
                    tool_name="noop",
                ),
            ],
        )

        async def fake_execute_step(step, variables, thread):
            if step.step_id == "boom":
                raise RuntimeError("kaboom")
            return f"result:{step.step_id}"

        with (
            patch.object(
                workflow_engine, "_execute_step", side_effect=fake_execute_step
            ),
            patch.object(workflow_engine, "save_workflow_result") as save_result,
        ):
            result = await workflow_engine.execute_workflow(workflow)

        self.assertEqual(result.status, "failed")
        self.assertIn("Parallel step 'boom' failed", result.error or "")
        save_result.assert_called_once()

    async def test_condition_loops_fail_fast(self) -> None:
        workflow = workflow_engine.Workflow(
            workflow_id="wf-loop",
            name="condition loop",
            description="condition steps should not be able to loop forever",
            steps=[
                workflow_engine.WorkflowStep(
                    step_id="loop",
                    step_type="condition",
                    condition={
                        "field": "flag",
                        "operator": "eq",
                        "value": "yes",
                        "then_step": "loop",
                        "else_step": "loop",
                    },
                    on_error="abort",
                )
            ],
            variables={"flag": "yes"},
        )

        with patch.object(workflow_engine, "save_workflow_result") as save_result:
            result = await workflow_engine.execute_workflow(workflow)

        self.assertEqual(result.status, "failed")
        self.assertIn("Possible infinite loop detected", result.error or "")
        save_result.assert_called_once()

    async def test_parallel_children_run_only_once(self) -> None:
        workflow = workflow_engine.Workflow(
            workflow_id="wf-parallel-once",
            name="parallel once",
            description="parallel children should not execute twice in linear flow",
            steps=[
                workflow_engine.WorkflowStep(
                    step_id="fanout",
                    step_type="parallel",
                    parallel_steps=["ok", "also_ok"],
                    on_error="abort",
                ),
                workflow_engine.WorkflowStep(
                    step_id="ok",
                    step_type="tool_call",
                    tool_name="noop",
                ),
                workflow_engine.WorkflowStep(
                    step_id="also_ok",
                    step_type="tool_call",
                    tool_name="noop",
                ),
                workflow_engine.WorkflowStep(
                    step_id="final",
                    step_type="tool_call",
                    tool_name="noop",
                ),
            ],
        )

        call_counts: dict[str, int] = {}

        async def fake_execute_step(step, variables, thread):
            call_counts[step.step_id] = call_counts.get(step.step_id, 0) + 1
            return f"result:{step.step_id}"

        with (
            patch.object(
                workflow_engine, "_execute_step", side_effect=fake_execute_step
            ),
            patch.object(workflow_engine, "save_workflow_result"),
        ):
            result = await workflow_engine.execute_workflow(workflow)

        self.assertEqual(result.status, "completed")
        self.assertEqual(call_counts["ok"], 1)
        self.assertEqual(call_counts["also_ok"], 1)
        self.assertEqual(call_counts["final"], 1)


if __name__ == "__main__":
    unittest.main()
