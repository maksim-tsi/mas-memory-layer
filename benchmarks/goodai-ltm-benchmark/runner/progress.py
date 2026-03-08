from collections import defaultdict
from collections.abc import Iterator
from typing import Any, Protocol

from dataset_interfaces.interface import TestExample
from reporting.results import TestResult
from utils.math import mean_std

tk: Any
ttk: Any

try:
    import tkinter as tk
    from tkinter import ttk

    _TK_AVAILABLE = True
except (ModuleNotFoundError, ImportError):  # pragma: no cover - headless environments
    tk = None
    ttk = None
    _TK_AVAILABLE = False


tqdm: Any

try:
    from tqdm import tqdm

    _TQDM_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    tqdm = None
    _TQDM_AVAILABLE = False


def blinker_gen() -> Iterator[str]:
    while True:
        yield from r"/-\|"


class ProgressDialogProtocol(Protocol):
    def notify_running(self, example: TestExample) -> None: ...

    def notify_message(self, token_count: int) -> None: ...

    def notify_result(self, result: TestResult) -> None: ...

    def update_stats(self) -> None: ...

    def close(self) -> None: ...


if _TK_AVAILABLE:

    class TkProgressDialog(tk.Tk):
        def __init__(self, num_tests: int, isolated: bool) -> None:
            super().__init__()
            self._num_tests = num_tests
            self._isolated = isolated
            self._memory_span: int | None = None
            self._at = 0
            self._test_info: dict[str, dict[str, int]] = {}
            self._scores: defaultdict[str, list[float]] = defaultdict(list)
            self._blinker = blinker_gen()

            self.title("GoodAI LTM Benchmark")

            self._label = tk.Label(self, text="Setting up...")
            self._label.pack(padx=20, pady=(20, 5))

            self._progressbar = ttk.Progressbar(
                self, orient="horizontal", length=200, mode="determinate"
            )
            self._progressbar.pack(padx=20, pady=5)
            self.update_idletasks()

        def notify_running(self, example: TestExample) -> None:
            self._at = max(self._at, example.start_token)
            self._memory_span = self._memory_span or example.dataset_generator.memory_span
            self._test_info[example.unique_id] = dict(
                start=example.start_token, span=self._memory_span
            )
            self.update_stats()

        def notify_message(self, token_count: int) -> None:
            self._at = token_count
            self.update_stats()

        def notify_result(self, result: TestResult) -> None:
            info = self._test_info[result.unique_id]
            info["span"] = self._at - info["start"]
            self._scores[result.dataset_name].append(result.score / result.max_score)
            self.update_stats()

        def update_stats(self) -> None:
            if len(self._test_info) == 0:
                return

            total_score = total_std = 0.0
            for scores in self._scores.values():
                score, std = mean_std(scores)
                total_score += score
                total_std += std
            self._label.config(
                text=f"{next(self._blinker)} Score: {total_score:.1f} ± {total_std:.1f}"
            )

            if self._isolated:
                progress = len(self._test_info) / self._num_tests
            else:
                assert self._memory_span is not None
                total = [info["span"] for info in self._test_info.values()]
                total += [self._memory_span] * (self._num_tests - len(total))
                progress = sum(
                    min(max(0, self._at - info["start"]), info["span"])
                    for info in self._test_info.values()
                )
                progress /= max(sum(total), 1)
            self._progressbar["value"] = int(100 * progress)
            self.update_idletasks()

        def close(self) -> None:
            self.destroy()
else:

    class HeadlessProgressDialog:  # pragma: no cover - headless fallback
        def __init__(self, num_tests: int, isolated: bool) -> None:
            self._num_tests = num_tests
            self._isolated = isolated
            self._memory_span: int | None = None
            self._at = 0
            self._test_info: dict[str, dict[str, int]] = {}
            self._scores: defaultdict[str, list[float]] = defaultdict(list)

        def notify_running(self, example: TestExample) -> None:
            self._at = max(self._at, example.start_token)
            self._memory_span = self._memory_span or example.dataset_generator.memory_span
            self._test_info[example.unique_id] = dict(
                start=example.start_token, span=self._memory_span
            )

        def notify_message(self, token_count: int) -> None:
            self._at = token_count

        def notify_result(self, result: TestResult) -> None:
            info = self._test_info[result.unique_id]
            info["span"] = self._at - info["start"]
            self._scores[result.dataset_name].append(result.score / result.max_score)

        def update_stats(self) -> None:
            return None

        def close(self) -> None:
            return None


class TqdmProgressDialog:  # pragma: no cover - optional dependency
    def __init__(self, num_tests: int, isolated: bool) -> None:
        if not _TQDM_AVAILABLE:
            raise RuntimeError("tqdm is not available.")
        self._num_tests = num_tests
        self._isolated = isolated
        self._memory_span: int | None = None
        self._at = 0
        self._test_info: dict[str, dict[str, int]] = {}
        self._scores: defaultdict[str, list[float]] = defaultdict(list)
        self._bar = tqdm(total=100, desc="Benchmark Progress", leave=True)

    def notify_running(self, example: TestExample) -> None:
        self._at = max(self._at, example.start_token)
        self._memory_span = self._memory_span or example.dataset_generator.memory_span
        self._test_info[example.unique_id] = dict(start=example.start_token, span=self._memory_span)
        self.update_stats()

    def notify_message(self, token_count: int) -> None:
        self._at = token_count
        self.update_stats()

    def notify_result(self, result: TestResult) -> None:
        info = self._test_info[result.unique_id]
        info["span"] = self._at - info["start"]
        self._scores[result.dataset_name].append(result.score / result.max_score)
        self.update_stats()

    def update_stats(self) -> None:
        if len(self._test_info) == 0:
            return
        if self._isolated:
            progress = len(self._test_info) / self._num_tests
        else:
            assert self._memory_span is not None
            total = [info["span"] for info in self._test_info.values()]
            total += [self._memory_span] * (self._num_tests - len(total))
            progress = sum(
                min(max(0, self._at - info["start"]), info["span"])
                for info in self._test_info.values()
            )
            progress /= max(sum(total), 1)
        target = int(100 * progress)
        self._bar.n = target
        self._bar.refresh()

    def close(self) -> None:
        self._bar.close()


def build_progress_dialog(mode: str, num_tests: int, isolated: bool) -> ProgressDialogProtocol:
    if mode == "tk":
        if _TK_AVAILABLE:
            return TkProgressDialog(num_tests, isolated)
        return HeadlessProgressDialog(num_tests, isolated)
    if mode == "tqdm":
        if _TQDM_AVAILABLE:
            return TqdmProgressDialog(num_tests, isolated)
        return HeadlessProgressDialog(num_tests, isolated)
    return HeadlessProgressDialog(num_tests, isolated)


ProgressDialog: type[ProgressDialogProtocol] = (
    TkProgressDialog if _TK_AVAILABLE else HeadlessProgressDialog
)
