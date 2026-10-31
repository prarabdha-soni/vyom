"""Structured, PHI-safe logging and per-decision telemetry (A0).

One JSON object per line, one event per decision-stage, correlated by a
correlation_id that threads ingest → System One → deterministic routing →
System Two → queue.

Hard rules (binding prompt, non-negotiable 8 and A0):
- Never log patient data or full article text. Every payload is passed
  through ``redact`` first: free-text keys are dropped and long strings are
  truncated to a hash prefix so nothing quotable survives in the log.
- Cost telemetry marks unavailable values as ``None`` — it never fabricates
  token counts or costs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

LOGGER_NAME = "vyom.events"

#: Keys whose values must never reach a log line, whatever their length.
REDACTED_KEYS = frozenset(
    {
        "abstract",
        "answers",
        "api_key",
        "authorization",
        "citation",
        "cited_passages",
        "clinical_note",
        "corrections",
        "discharge_summary",
        "draft_narrative",
        "event_verbatim",
        "full_text",
        "medical_record_text",
        "normalized_state",
        "override_patch",
        "patient",
        "password",
        "rationale_note",
        "raw",
        "raw_payload",
        "secret",
        "source_text",
        "token",
    }
)

MAX_STRING_LENGTH = 120
_REDACTED = "[REDACTED]"
_HASH_ONLY = re.compile(r"^[0-9a-f]{16}$")


def redact(value: Any, *, key_hint: str | None = None) -> Any:
    """Return a log-safe copy of ``value``.

    - Dicts keyed on anything in :data:`REDACTED_KEYS` drop the value entirely.
    - Long strings collapse to a short sha-256 prefix so joins across events
      stay possible without storing content.
    """
    if key_hint is not None and key_hint.lower() in REDACTED_KEYS:
        return _REDACTED
    if isinstance(value, dict):
        return {str(key): redact(item, key_hint=str(key)) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        # Lists of content (answers, citations) are collapsed to a count.
        return {"count": len(value)}
    if isinstance(value, str):
        if len(value) <= MAX_STRING_LENGTH:
            return value
        return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _REDACTED


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
        }
        event = getattr(record, "event_fields", None)
        if isinstance(event, dict):
            payload.update(event)
        else:
            payload["message"] = record.getMessage()
        return json.dumps(payload, ensure_ascii=False, default=str)


def get_event_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if not any(isinstance(h, logging.StreamHandler) and getattr(h, "_vyom_json", False) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonLineFormatter())
        handler._vyom_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def emit_event(
    event: str,
    *,
    correlation_id: str | None = None,
    level: int = logging.INFO,
    **fields: Any,
) -> dict[str, Any]:
    """Emit exactly one structured JSON log event; returns the emitted fields."""
    payload: dict[str, Any] = {"event": event}
    if correlation_id:
        payload["correlation_id"] = correlation_id
    payload.update(redact(fields))
    get_event_logger().info("", extra={"event_fields": payload})
    return payload


@contextmanager
def timed_stage(
    stage: str,
    *,
    correlation_id: str | None = None,
    **fields: Any,
) -> Iterator[dict[str, Any]]:
    """Time a pipeline stage and emit start/end/error events."""
    started = time.perf_counter()
    summary: dict[str, Any] = {"stage": stage, "status": "ok"}
    summary.update(redact(fields))
    try:
        yield summary
    except Exception as error:  # noqa: BLE001 - logged then re-raised unchanged
        summary["status"] = "error"
        summary["error_type"] = type(error).__name__
        summary["duration_ms"] = (time.perf_counter() - started) * 1000
        emit_event(f"{stage}_failed", correlation_id=correlation_id, level=logging.ERROR, **summary)
        raise
    summary["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
    emit_event(f"{stage}_completed", correlation_id=correlation_id, **summary)


# ---------------------------------------------------------------------------
# Percentiles used by the load harness and the /ops latency readout.
# ---------------------------------------------------------------------------

def percentile(values: list[float], quantile: float) -> float | None:
    """Nearest-rank percentile. Returns None for empty input (never invents 0)."""
    if not values:
        return None
    ordered = sorted(values)
    if quantile <= 0:
        return float(ordered[0])
    if quantile >= 1:
        return float(ordered[-1])
    index = max(0, min(len(ordered) - 1, int(round(quantile * (len(ordered) - 1)))))
    return float(ordered[index])


def latency_summary(values: list[float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "p50_ms": percentile(values, 0.50),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "max_ms": max(values) if values else None,
    }
