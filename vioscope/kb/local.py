from __future__ import annotations

import hashlib
import math
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml  # type: ignore[import-untyped]
from agno.knowledge.embedder.base import Embedder
from pydantic import BaseModel, ConfigDict, Field

from vioscope.core.safe_path import safe_path

DEFAULT_KB_ROOT = Path.home() / ".vioscope" / "kb"
ALLOWED_RECORD_TYPES = ("sessions", "literature", "hypotheses", "papers")


class KBRecord(BaseModel):
    record_id: str
    record_type: str
    session_id: str
    content_snippet: str
    source_path: str
    source_record_ids: list[str] = Field(default_factory=list)
    created_at: str | None = None
    research_question: str | None = None

    model_config = ConfigDict(extra="forbid")


@dataclass
class _HashEmbedder(Embedder):
    dimensions: int | None = 32
    enable_batch: bool = False
    batch_size: int = 100

    def get_embedding(self, text: str) -> list[float]:
        dimensions = self.dimensions or 32
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [
            ((digest[index % len(digest)] / 255.0) * 2.0) - 1.0 for index in range(dimensions)
        ]
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]

    def get_embedding_and_usage(self, text: str) -> tuple[list[float], dict[str, int]]:
        return self.get_embedding(text), {"tokens": len(text.split())}

    async def async_get_embedding(self, text: str) -> list[float]:
        return self.get_embedding(text)

    async def async_get_embedding_and_usage(self, text: str) -> tuple[list[float], dict[str, int]]:
        return self.get_embedding_and_usage(text)


class LocalKB:
    def __init__(self, root_dir: Path | str | None = None) -> None:
        self.root_dir = self._resolve_root_dir(root_dir)
        self._knowledge_fingerprint: str | None = None
        self._knowledge_filter: tuple[str, ...] | None = None
        self._knowledge: Any | None = None

    def write_record(
        self,
        record_type: str,
        session_id: str,
        content: str,
        frontmatter: dict[str, Any],
        extension: str = "md",
    ) -> Path:
        normalized_type = self._normalize_record_type(record_type)
        normalized_extension = extension.lstrip(".")
        record_dir = self._record_dir(normalized_type)
        record_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        filename = f"{timestamp}_{session_id}_{normalized_type}.{normalized_extension}"
        target_path = safe_path(record_dir, filename)
        metadata = {
            "type": normalized_type,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **frontmatter,
        }
        payload = f"---\n{yaml.safe_dump(metadata, sort_keys=False).strip()}\n---\n{content}"
        target_path.write_text(payload, encoding="utf-8")
        self._invalidate_knowledge_cache()
        return target_path

    def read_record(self, record_type: str, record_id: str) -> str:
        record_path = self._resolve_record_path(record_type, record_id)
        _frontmatter, content = self._read_frontmatter(record_path)
        return content

    def list_records(self, record_type: str | None = None) -> list[dict[str, Any]]:
        record_types = (
            [self._normalize_record_type(record_type)]
            if record_type
            else list(ALLOWED_RECORD_TYPES)
        )
        records: list[dict[str, Any]] = []
        for current_type in record_types:
            record_dir = self._record_dir(current_type)
            if not record_dir.exists():
                continue
            for path in sorted(record_dir.iterdir()):
                if not path.is_file():
                    continue
                frontmatter, content = self._read_frontmatter(path)
                record = {
                    "record_id": path.stem,
                    "record_type": current_type,
                    "source_path": str(path),
                    "content": content,
                    **frontmatter,
                }
                records.append(record)
        records.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return records

    def get_knowledge_base(self, record_types: tuple[str, ...] | None = None) -> Any:
        requested_types = tuple(record_types) if record_types else tuple(ALLOWED_RECORD_TYPES)
        records = self.list_records()
        filtered_records = [
            record for record in records if record["record_type"] in requested_types
        ]
        fingerprint = self._records_fingerprint(filtered_records)
        if (
            self._knowledge is not None
            and self._knowledge_fingerprint == fingerprint
            and self._knowledge_filter == requested_types
        ):
            return self._knowledge

        try:
            from agno.knowledge import Knowledge
            from agno.vectordb.lancedb import LanceDb
        except ImportError as exc:
            raise RuntimeError(
                "LanceDB knowledge support is unavailable. Install lancedb."
            ) from exc

        index_dir = safe_path(self.root_dir, ".lancedb")
        if index_dir.exists():
            shutil.rmtree(index_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        knowledge = Knowledge(
            name="VioScope KB",
            vector_db=LanceDb(
                uri=str(index_dir),
                table_name="kb_records",
                embedder=_HashEmbedder(),
            ),
            max_results=10,
        )
        for record in filtered_records:
            knowledge.insert(
                name=record["record_id"],
                text_content=self._render_search_document(record),
                metadata={
                    "record_id": record["record_id"],
                    "record_type": record["record_type"],
                    "session_id": record.get("session_id", ""),
                    "source_path": record["source_path"],
                    "source_record_ids": record.get("source_record_ids", []),
                    "created_at": record.get("created_at"),
                    "research_question": record.get("research_question"),
                },
                upsert=True,
            )

        self._knowledge = knowledge
        self._knowledge_fingerprint = fingerprint
        self._knowledge_filter = requested_types
        return knowledge

    def search(
        self,
        query: str,
        limit: int = 5,
        record_types: tuple[str, ...] | None = None,
    ) -> list[KBRecord]:
        requested_types = tuple(record_types) if record_types else tuple(ALLOWED_RECORD_TYPES)
        if os.getenv("VIOSCOPE_ENABLE_LANCEDB") == "1":
            try:
                knowledge = self.get_knowledge_base(requested_types)
                documents = knowledge.search(query=query, max_results=limit)
                return [self._document_to_record(document) for document in documents]
            except RuntimeError:
                pass
        return self._fallback_search(query=query, limit=limit, record_types=requested_types)

    def _fallback_search(
        self,
        *,
        query: str,
        limit: int,
        record_types: tuple[str, ...],
    ) -> list[KBRecord]:
        query_embedding = _HashEmbedder().get_embedding(query)
        ranked_records: list[tuple[float, dict[str, Any]]] = []
        for record in self.list_records():
            if record["record_type"] not in record_types:
                continue
            record_embedding = _HashEmbedder().get_embedding(self._render_search_document(record))
            score = sum(a * b for a, b in zip(query_embedding, record_embedding))
            if query.lower() in self._render_search_document(record).lower():
                score += 1.0
            ranked_records.append((score, record))
        ranked_records = [item for item in ranked_records if item[0] > 0.0]
        ranked_records.sort(key=lambda item: item[0], reverse=True)
        return [self._record_to_kb_record(record) for _, record in ranked_records[:limit]]

    def _document_to_record(self, document: Any) -> KBRecord:
        metadata = getattr(document, "meta_data", {}) or {}
        content = getattr(document, "content", "") or ""
        return KBRecord(
            record_id=str(metadata.get("record_id") or getattr(document, "name", "") or ""),
            record_type=str(metadata.get("record_type") or "unknown"),
            session_id=str(metadata.get("session_id") or ""),
            content_snippet=content[:240],
            source_path=str(metadata.get("source_path") or ""),
            source_record_ids=list(metadata.get("source_record_ids") or []),
            created_at=(
                str(metadata.get("created_at")) if metadata.get("created_at") is not None else None
            ),
            research_question=(
                str(metadata.get("research_question"))
                if metadata.get("research_question") is not None
                else None
            ),
        )

    def _record_to_kb_record(self, record: dict[str, Any]) -> KBRecord:
        source_record_ids = record.get("source_record_ids", [])
        if not isinstance(source_record_ids, list):
            source_record_ids = []
        return KBRecord(
            record_id=str(record["record_id"]),
            record_type=str(record["record_type"]),
            session_id=str(record.get("session_id", "")),
            content_snippet=str(record.get("content", ""))[:240],
            source_path=str(record["source_path"]),
            source_record_ids=[str(item) for item in source_record_ids],
            created_at=(
                str(record.get("created_at")) if record.get("created_at") is not None else None
            ),
            research_question=(
                str(record.get("research_question"))
                if record.get("research_question") is not None
                else None
            ),
        )

    def _render_search_document(self, record: dict[str, Any]) -> str:
        header_lines = [
            f"record_type: {record['record_type']}",
            f"session_id: {record.get('session_id', '')}",
            f"research_question: {record.get('research_question', '')}",
        ]
        source_record_ids = record.get("source_record_ids", [])
        if isinstance(source_record_ids, list) and source_record_ids:
            header_lines.append(
                f"source_record_ids: {', '.join(str(item) for item in source_record_ids)}"
            )
        content = str(record.get("content", "")).strip()
        return "\n".join(header_lines + ["", content]).strip()

    def _records_fingerprint(self, records: Iterable[dict[str, Any]]) -> str:
        payload = [
            f"{record['record_id']}:{record['record_type']}:{record.get('created_at','')}:{record['source_path']}"
            for record in records
        ]
        joined = "\n".join(sorted(payload))
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def _resolve_record_path(self, record_type: str, record_id: str) -> Path:
        normalized_type = self._normalize_record_type(record_type)
        record_dir = self._record_dir(normalized_type)
        for path in record_dir.glob("*"):
            if path.is_file() and path.stem == record_id:
                return path
        raise FileNotFoundError(f"KB record '{record_id}' not found in '{normalized_type}'.")

    def _record_dir(self, record_type: str) -> Path:
        normalized_type = self._normalize_record_type(record_type)
        return safe_path(self.root_dir, normalized_type)

    def _normalize_record_type(self, record_type: str | None) -> str:
        normalized = (record_type or "").strip().lower()
        if normalized not in ALLOWED_RECORD_TYPES:
            raise ValueError(
                f"Unsupported record type '{record_type}'. Allowed: {', '.join(ALLOWED_RECORD_TYPES)}"
            )
        return normalized

    def _read_frontmatter(self, path: Path) -> tuple[dict[str, Any], str]:
        raw = path.read_text(encoding="utf-8")
        if not raw.startswith("---\n"):
            return {}, raw
        parts = raw.split("\n---\n", 1)
        if len(parts) != 2:
            return {}, raw
        frontmatter_raw = parts[0][4:]
        content = parts[1]
        frontmatter = yaml.safe_load(frontmatter_raw) or {}
        if not isinstance(frontmatter, dict):
            return {}, content
        return frontmatter, content

    def _resolve_root_dir(self, root_dir: Path | str | None) -> Path:
        candidate = Path(root_dir) if root_dir is not None else DEFAULT_KB_ROOT
        base_dir = candidate.parent if candidate.is_absolute() else Path.cwd()
        return safe_path(base_dir, candidate)

    def _invalidate_knowledge_cache(self) -> None:
        self._knowledge = None
        self._knowledge_fingerprint = None
        self._knowledge_filter = None


__all__ = ["ALLOWED_RECORD_TYPES", "DEFAULT_KB_ROOT", "KBRecord", "LocalKB"]
