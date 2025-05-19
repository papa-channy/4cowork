
from pathlib import Path
from typing import List
from functools import wraps
import time
import os


def measure_time_and_log(func):
    @wraps(func)
    def wrapper(self, file_a: Path, file_b: Path) -> float:
        start = time.time()
        result = func(self, file_a, file_b)
        end = time.time()
        print(f"[✔] {func.__name__:<30} → {result:.4f}  (Time: {end - start:.2f}s)")
        return result
    return wrapper


class PathFeatureExtractor:
    def __init__(self):
        pass

    def _jaccard(self, set1: set, set2: set) -> float:
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        return len(set1 & set2) / len(set1 | set2)

    def _tokenize_filename(self, name: str) -> set:
        return set(name.lower().replace("-", "_").split("_"))

    def _path_parts(self, file: Path) -> List[str]:
        return [p for p in file.parts if p not in {"", ".", ".."}]

    @measure_time_and_log
    def filename_semantic_jaccard(self, file_a: Path, file_b: Path) -> float:
        tokens_a = self._tokenize_filename(file_a.stem)
        tokens_b = self._tokenize_filename(file_b.stem)
        return self._jaccard(tokens_a, tokens_b)

    @measure_time_and_log
    def name_edit_distance(self, file_a: Path, file_b: Path) -> float:
        from difflib import SequenceMatcher
        name1 = file_a.name
        name2 = file_b.name
        sim = SequenceMatcher(None, name1, name2).ratio()
        return 1.0 - sim  # 거리로 반환

    @measure_time_and_log
    def path_depth_overlap(self, file_a: Path, file_b: Path) -> float:
        parts_a = self._path_parts(file_a.parent)
        parts_b = self._path_parts(file_b.parent)
        min_len = min(len(parts_a), len(parts_b))
        overlap = sum(1 for i in range(min_len) if parts_a[i] == parts_b[i])
        return overlap / max(len(parts_a), len(parts_b)) if parts_a and parts_b else 0.0

    @measure_time_and_log
    def folder_prefix_match(self, file_a: Path, file_b: Path) -> float:
        return float(file_a.parent.name == file_b.parent.name)

    @measure_time_and_log
    def module_level_overlap(self, file_a: Path, file_b: Path) -> float:
        levels_a = set(self._path_parts(file_a.parent))
        levels_b = set(self._path_parts(file_b.parent))
        return self._jaccard(levels_a, levels_b)
