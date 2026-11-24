from __future__ import annotations

from .. import knowledge
from ..llm import LLM


class Agent:
    """A team member: a role prompt + the shared knowledge base + the LLM."""

    role: str = ""

    def __init__(self, llm: LLM):
        self.llm = llm

    @property
    def system(self) -> str:
        return (
            f"{self.role.strip()}\n\n"
            "You work on a one-person marketing team. Follow the knowledge files below "
            "exactly: they are the owner's offer, audience, voice and rules. If a fact "
            "is not in them, do not invent it.\n\n"
            f"{knowledge.load()}"
        )
