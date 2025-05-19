
from pathlib import Path
from typing import List
from functools import wraps
from simhash import Simhash
import libcst as cst
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


class SymbolFeatureExtractor:
    def __init__(self):
        self.cache = {}

    def extract_symbols(self, file: Path) -> dict:
        if file in self.cache:
            return self.cache[file]

        code = file.read_text(encoding="utf-8", errors="ignore")
        module = cst.parse_module(code)

        symbols = {"def": [], "class": [], "import": []}

        class Visitor(cst.CSTVisitor):
            def visit_FunctionDef(self, node):
                symbols["def"].append(node.name.value)

            def visit_ClassDef(self, node):
                symbols["class"].append(node.name.value)

            def visit_Import(self, node):
                for n in node.names:
                    name = getattr(n.evaluated_name, "value", None)
                    if not name and hasattr(n.name, "value"):
                        name = n.name.value
                    elif not name:
                        name = str(n.name)
                    if isinstance(name, str):
                        symbols["import"].append(name)

            def visit_ImportFrom(self, node):
                if node.module:
                    mod = getattr(node.module, "attr", None) or getattr(node.module, "value", None)
                    if isinstance(mod, str):
                        symbols["import"].append(mod)
                    elif hasattr(mod, "__str__"):
                        symbols["import"].append(str(mod))

        module.visit(Visitor())
        self.cache[file] = symbols
        return symbols

    def _simhash_distance(self, list1: List[str], list2: List[str]) -> float:
        return Simhash(list1).distance(Simhash(list2))

    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        return len(set1 & set2) / len(set1 | set2)

    @measure_time_and_log
    def def_simhash_distance(self, file_a: Path, file_b: Path) -> float:
        s1 = self.extract_symbols(file_a)["def"]
        s2 = self.extract_symbols(file_b)["def"]
        return self._simhash_distance(s1, s2)

    @measure_time_and_log
    def class_simhash_distance(self, file_a: Path, file_b: Path) -> float:
        s1 = self.extract_symbols(file_a)["class"]
        s2 = self.extract_symbols(file_b)["class"]
        return self._simhash_distance(s1, s2)

    @measure_time_and_log
    def import_simhash_distance(self, file_a: Path, file_b: Path) -> float:
        s1 = self.extract_symbols(file_a)["import"]
        s2 = self.extract_symbols(file_b)["import"]
        return self._simhash_distance(s1, s2)

    @measure_time_and_log
    def def_jaccard(self, file_a: Path, file_b: Path) -> float:
        s1 = set(self.extract_symbols(file_a)["def"])
        s2 = set(self.extract_symbols(file_b)["def"])
        return self._jaccard_similarity(s1, s2)

    @measure_time_and_log
    def class_jaccard(self, file_a: Path, file_b: Path) -> float:
        s1 = set(self.extract_symbols(file_a)["class"])
        s2 = set(self.extract_symbols(file_b)["class"])
        return self._jaccard_similarity(s1, s2)

    @measure_time_and_log
    def import_jaccard(self, file_a: Path, file_b: Path) -> float:
        s1 = set(self.extract_symbols(file_a)["import"])
        s2 = set(self.extract_symbols(file_b)["import"])
        return self._jaccard_similarity(s1, s2)
