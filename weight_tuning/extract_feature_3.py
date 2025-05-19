
from pathlib import Path
from functools import wraps
import time


def measure_time_and_log(func):
    @wraps(func)
    def wrapper(self, file_a: Path, file_b: Path) -> float:
        start = time.time()
        result = func(self, file_a, file_b)
        end = time.time()
        print(f"[✔] {func.__name__:<30} → {result:.4f}  (Time: {end - start:.2f}s)")
        return result
    return wrapper


class CodeStructureFeatureExtractor:
    def __init__(self):
        pass

    def _count_lines(self, file: Path) -> dict:
        text = file.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        non_blank_lines = [line for line in lines if line.strip()]
        blank_lines = [line for line in lines if not line.strip()]
        indent_levels = [len(line) - len(line.lstrip(" ")) for line in non_blank_lines if line.strip()]
        docstrings = [line for line in non_blank_lines if line.strip().startswith('"""') or line.strip().startswith("'''")]

        return {
            "total": len(lines),
            "non_blank": len(non_blank_lines),
            "blank": len(blank_lines),
            "avg_len": sum(len(line) for line in lines) / len(lines) if lines else 0,
            "max_indent": max(indent_levels) if indent_levels else 0,
            "docstring": len(docstrings)
        }

    @measure_time_and_log
    def def_class_count_diff(self, file_a: Path, file_b: Path) -> float:
        a = file_a.read_text(encoding="utf-8", errors="ignore")
        b = file_b.read_text(encoding="utf-8", errors="ignore")
        count_a = a.count("def ") + a.count("class ")
        count_b = b.count("def ") + b.count("class ")
        return abs(count_a - count_b)

    @measure_time_and_log
    def line_length_ratio(self, file_a: Path, file_b: Path) -> float:
        a_lines = self._count_lines(file_a)["total"]
        b_lines = self._count_lines(file_b)["total"]
        return abs(a_lines - b_lines) / max(a_lines, b_lines) if max(a_lines, b_lines) else 0.0

    @measure_time_and_log
    def blank_line_ratio_diff(self, file_a: Path, file_b: Path) -> float:
        a = self._count_lines(file_a)
        b = self._count_lines(file_b)
        a_ratio = a["blank"] / a["total"] if a["total"] else 0
        b_ratio = b["blank"] / b["total"] if b["total"] else 0
        return abs(a_ratio - b_ratio)

    @measure_time_and_log
    def max_indent_level_diff(self, file_a: Path, file_b: Path) -> float:
        a = self._count_lines(file_a)["max_indent"]
        b = self._count_lines(file_b)["max_indent"]
        return abs(a - b)

    @measure_time_and_log
    def docstring_comment_ratio(self, file_a: Path, file_b: Path) -> float:
        a = self._count_lines(file_a)
        b = self._count_lines(file_b)
        a_ratio = a["docstring"] / a["total"] if a["total"] else 0
        b_ratio = b["docstring"] / b["total"] if b["total"] else 0
        return abs(a_ratio - b_ratio)
