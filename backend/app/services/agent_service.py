"""
services/agent_service.py – Multi-step AI agent that plans + executes tasks.

The agent uses the AI to produce a JSON plan, then dispatches each step to the
appropriate service (file ops, terminal, code gen, chat).
"""

from __future__ import annotations
import json
import re
from typing import List, Optional

from app.services.ai_service import ai_service
from app.services.file_service import file_service
from app.services.terminal_service import terminal_service
from app.models.schemas import AgentStep
from app.utils.logger import get_logger

logger = get_logger("agent_service")


class AgentService:
    """Autonomous multi-step agent engine."""

    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        workspace_path: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict:
        """
        1. Ask AI to produce a JSON plan.
        2. Execute each step.
        3. Return structured result.
        """
        logger.info("Agent received task: %s", task[:80])

        # ── Step 1: Get plan from AI ──────────────────────────────
        plan_json = await ai_service.plan_task(task=task, context=context, model=model)
        steps_data = self._parse_plan(plan_json)

        completed_steps: List[AgentStep] = []
        overall_success = True

        # ── Step 2: Execute each step ─────────────────────────────
        for i, step in enumerate(steps_data, 1):
            action = step.get("action", "unknown")
            description = step.get("description", "")
            result, success = await self._dispatch(action, description, workspace_path, model)

            completed_steps.append(AgentStep(
                step=i,
                action=action,
                result=result,
                success=success,
            ))

            if not success:
                overall_success = False
                logger.warning("Agent step %d failed: %s", i, result)
                # Continue anyway so the user sees what happened

        # ── Step 3: Build final summary ───────────────────────────
        summary_prompt = (
            f"The agent executed the following task:\n{task}\n\n"
            f"Steps completed:\n"
            + "\n".join(
                f"{s.step}. [{s.action}] {'✅' if s.success else '❌'} – {s.result[:200]}"
                for s in completed_steps
            )
            + "\n\nProvide a short, clear summary of what was accomplished."
        )

        final_result = await ai_service.chat(
            message=summary_prompt,
            history=[],
            model=model,
        )

        return {
            "task": task,
            "steps": [s.model_dump() for s in completed_steps],
            "final_result": final_result,
            "success": overall_success,
        }

    # ─────────────────────────────────────────────────────────────
    #  Plan parsing
    # ─────────────────────────────────────────────────────────────
    def _parse_plan(self, raw: str) -> List[dict]:
        """Extract a list-of-steps from the AI's raw text output."""
        # Try to pull JSON out of a markdown code block first
        match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
        if match:
            raw = match.group(1)

        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "steps" in data:
                return data["steps"]
        except json.JSONDecodeError:
            pass

        # Fallback: treat the whole thing as a single "chat" step
        logger.warning("Could not parse plan as JSON, falling back to single step.")
        return [{"action": "chat", "description": raw}]

    # ─────────────────────────────────────────────────────────────
    #  Step dispatcher
    # ─────────────────────────────────────────────────────────────
    async def _dispatch(
        self,
        action: str,
        description: str,
        workspace_path: Optional[str],
        model: Optional[str],
    ) -> tuple[str, bool]:
        """Route a plan step to the correct service and return (result, success)."""
        action_lower = action.lower()

        try:
            # ── Run terminal command ───────────────────────────────
            if action_lower in {"run_command", "terminal", "execute", "install"}:
                stdout, stderr, rc = await terminal_service.run(
                    command=description,
                    cwd=workspace_path,
                )
                output = stdout or stderr
                return output[:500], rc == 0

            # ── Generate code ─────────────────────────────────────
            elif action_lower in {"generate_code", "write_code", "create_code"}:
                code = await ai_service.generate_code(
                    prompt=description,
                    model=model,
                )
                return code[:500], True

            # ── Read file ─────────────────────────────────────────
            elif action_lower in {"read_file", "read"}:
                content = file_service.read(description)
                return content[:500], True

            # ── Write/create file ─────────────────────────────────
            elif action_lower in {"write_file", "create_file", "write", "create"}:
                # Expect description format: "path::content"
                if "::" in description:
                    path, content = description.split("::", 1)
                    file_service.write(path.strip(), content.strip())
                    return f"File written: {path.strip()}", True
                return "Invalid write_file format. Expected 'path::content'", False

            # ── Chat / analyse ─────────────────────────────────────
            else:
                response = await ai_service.chat(
                    message=description,
                    history=[],
                    model=model,
                )
                return response[:500], True

        except Exception as exc:
            logger.error("Agent step dispatch error: %s", exc)
            return str(exc), False


# Module-level singleton
agent_service = AgentService()
