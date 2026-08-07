"""Parse unittest -v console output into structured results (no PASS fabrication)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Status = Literal["passed", "failed", "error", "skipped", "unexpected"]

_LINE_RE = re.compile(
    r"^(?P<name>test_\S+)\s+\((?P<cls>[^)]+)\)\s+\.\.\.\s+(?P<status>\S+)\s*$"
)
_RAN_RE = re.compile(r"^Ran\s+(?P<n>\d+)\s+tests?\s+in\s+(?P<sec>[0-9.]+)s")
_FAIL_SUMMARY_RE = re.compile(
    r"^FAILED\s+\((?P<body>[^)]*)\)\s*$"
)
_OK_SUMMARY_RE = re.compile(r"^OK\b")


@dataclass
class CaseResult:
    name: str
    class_name: str
    status: Status
    message: str = ""


@dataclass
class HarnessRunResult:
    cases: list[CaseResult] = field(default_factory=list)
    tests_run: int | None = None
    duration_seconds: float | None = None
    summary_line: str = ""
    raw_ok: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases": [asdict(c) for c in self.cases],
            "tests_run": self.tests_run,
            "duration_seconds": self.duration_seconds,
            "summary_line": self.summary_line,
            "raw_ok": self.raw_ok,
            "passed": sum(1 for c in self.cases if c.status == "passed"),
            "failed": sum(1 for c in self.cases if c.status == "failed"),
            "error": sum(1 for c in self.cases if c.status == "error"),
            "skipped": sum(1 for c in self.cases if c.status == "skipped"),
        }


def _map_status(token: str) -> Status:
    t = token.lower().rstrip(".")
    if t in {"ok", "passed", "pass"}:
        return "passed"
    if t in {"fail", "failed", "failure"}:
        return "failed"
    if t in {"error", "errors"}:
        return "error"
    if t in {"skip", "skipped"}:
        return "skipped"
    return "unexpected"


def parse_unittest_output(text: str) -> HarnessRunResult:
    result = HarnessRunResult()
    for line in text.splitlines():
        m = _LINE_RE.match(line.strip())
        if m:
            result.cases.append(
                CaseResult(
                    name=m.group("name"),
                    class_name=m.group("cls"),
                    status=_map_status(m.group("status")),
                )
            )
            continue
        ran = _RAN_RE.match(line.strip())
        if ran:
            result.tests_run = int(ran.group("n"))
            result.duration_seconds = float(ran.group("sec"))
            continue
        if _OK_SUMMARY_RE.match(line.strip()):
            result.summary_line = line.strip()
            result.raw_ok = True
            continue
        fail = _FAIL_SUMMARY_RE.match(line.strip())
        if fail:
            result.summary_line = line.strip()
            result.raw_ok = False
    if result.raw_ok is None and result.cases:
        result.raw_ok = all(c.status == "passed" for c in result.cases)
    return result
