"""Thin wrapper around the Claude API used by every agent.

Two call shapes:
  * structured(): returns a validated Pydantic object (Creative, Leads, Analytics...)
  * research():   free-text answer with live web search (Research team)
"""

from __future__ import annotations

from typing import TypeVar

import anthropic
from pydantic import BaseModel

from . import config

T = TypeVar("T", bound=BaseModel)

# Server-side refusal fallback: if a request is declined by a safety classifier,
# the API re-runs it on a suitable fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}


class AgentRefused(RuntimeError):
    pass


class LLM:
    def __init__(self, client: anthropic.Anthropic | None = None, model: str | None = None):
        self.client = client or anthropic.Anthropic()
        self.model = model or config.MODEL

    def structured(
        self,
        system: str,
        prompt: str,
        schema: type[T],
        effort: str = "medium",
        max_tokens: int = 16000,
    ) -> T:
        resp = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
            output_config={"effort": effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if resp.stop_reason == "refusal":
            raise AgentRefused(_refusal_text(resp))
        if resp.stop_reason == "max_tokens" or resp.parsed_output is None:
            raise RuntimeError(f"agent output incomplete (stop_reason={resp.stop_reason})")
        return resp.parsed_output

    def research(self, system: str, prompt: str, effort: str = "medium") -> str:
        """Answer with live web search. Handles pause_turn for long searches."""
        messages: list = [{"role": "user", "content": prompt}]
        for _ in range(5):
            with self.client.beta.messages.stream(
                model=self.model,
                max_tokens=32000,
                system=system,
                messages=messages,
                tools=[WEB_SEARCH_TOOL],
                output_config={"effort": effort},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            ) as stream:
                resp = stream.get_final_message()
            if resp.stop_reason == "refusal":
                raise AgentRefused(_refusal_text(resp))
            if resp.stop_reason == "pause_turn":
                # Server paused a long web-search turn; send it back to continue.
                messages.append({"role": "assistant", "content": resp.content})
                continue
            return "\n".join(b.text for b in resp.content if b.type == "text").strip()
        raise RuntimeError("research did not finish after 5 continuations")


def _refusal_text(resp) -> str:
    details = getattr(resp, "stop_details", None)
    if details:
        return f"request declined ({details.category}): {details.explanation}"
    return "request declined"
