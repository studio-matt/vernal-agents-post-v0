"""LLM orchestration harness for the portable content machine assets."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from .models import GenerationResult, PlannerOutput


class GeneratorHarness:
    """Wraps an injected callable responsible for executing the LLM call."""

    def __init__(self, invoke_llm: Callable[[str], str]) -> None:
        self.invoke_llm = invoke_llm

    def run(self, planner_output: PlannerOutput) -> GenerationResult:
        prompt = "\n\n".join(
            [
                "# STYLE CONFIG",
                planner_output.style_config_block,
                "# CADENCE AND LEXICON HINTS",
                str(planner_output.lexicon_hints),
                "# SCAFFOLD",
                planner_output.scaffold,
            ]
        )
        text = self.invoke_llm(prompt)
        token_count = len(text.split())
        prompt_id = str(uuid.uuid4())
        return GenerationResult(
            text=text,
            prompt_id=prompt_id,
            token_count=token_count,
            planner_metadata=planner_output.metadata,
        )
