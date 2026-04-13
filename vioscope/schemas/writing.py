from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field  # type: ignore[import-not-found]


class JournalTemplate(str, Enum):
    NEURIPS = "neurips"
    CVPR = "cvpr"
    MICCAI = "miccai"
    NATURE = "nature"

    @property
    def output_format(self) -> str:
        return "tex" if self in {self.NEURIPS, self.CVPR, self.MICCAI} else "md"


class OutlineSection(BaseModel):
    name: str
    summary: str
    citations: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PaperOutline(BaseModel):
    template: JournalTemplate
    sections: List[OutlineSection]

    model_config = ConfigDict(extra="forbid")


class DraftSection(BaseModel):
    name: str
    content: str
    template: JournalTemplate
    citations: List[str] = Field(default_factory=list)
    section_order: int | None = None

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "DraftSection",
    "JournalTemplate",
    "OutlineSection",
    "PaperOutline",
]
