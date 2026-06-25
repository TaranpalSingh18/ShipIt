import time
from datetime import datetime, timezone
from typing import Any


class PipelineTimer:
    """Logs UTC timestamps and elapsed seconds for each pipeline phase."""

    def __init__(self, label: str = "request"):
        self.label = label
        self._started_at = time.perf_counter()
        self._phase_started_at: float | None = None
        self._current_phase: str | None = None
        self.phases: list[dict[str, Any]] = []

    def start_phase(self, name: str) -> None:
        self._end_current_phase()
        self._current_phase = name
        self._phase_started_at = time.perf_counter()
        print(f"[TIMING {self._timestamp()}] START  {name}")

    def _end_current_phase(self) -> None:
        if self._phase_started_at is None or self._current_phase is None:
            return

        elapsed_s = time.perf_counter() - self._phase_started_at
        self.phases.append(
            {
                "phase": self._current_phase,
                "duration_s": round(elapsed_s, 2),
            }
        )
        print(
            f"[TIMING {self._timestamp()}] END    {self._current_phase} "
            f"({elapsed_s:.2f}s)"
        )
        self._phase_started_at = None
        self._current_phase = None

    def finish(self) -> dict[str, Any]:
        self._end_current_phase()
        total_s = time.perf_counter() - self._started_at
        summary = {
            "label": self.label,
            "total_s": round(total_s, 2),
            "phases": self.phases,
        }
        print(
            f"[TIMING {self._timestamp()}] TOTAL  {self.label} "
            f"({total_s:.2f}s)"
        )
        for entry in self.phases:
            pct = (entry["duration_s"] / total_s * 100) if total_s else 0
            print(
                f"  - {entry['phase']}: {entry['duration_s']}s ({pct:.0f}%)"
            )
        return summary

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
