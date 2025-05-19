
from pathlib import Path
import time
import importlib.util
from typing import Callable


class FeatureRunner:
    def __init__(self, file_a: Path, file_b: Path):
        self.file_a = file_a
        self.file_b = file_b
        self.results = {}

        # 연결할 extractor 모듈들 (파일명, 클래스명) 쌍
        self.extractors = [
            ("extract_feature_1", "SymbolFeatureExtractor"),
            ("extract_feature_2", "PathFeatureExtractor"),
            ("extract_feature_3", "CodeStructureFeatureExtractor"),
            ("extract_feature_4", "SyntaxPatternFeatureExtractor"),
            ("extract_feature_5", "ExecutionFeatureExtractor")
        ]

    def _load_module(self, filename: str):
        spec = importlib.util.spec_from_file_location(
            filename, Path(f"./{filename}.py").resolve()
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def run_all(self):
        print(f"🚀 실행 시작: {self.file_a.name} vs {self.file_b.name}\n")
        total_start = time.time()

        for mod_name, class_name in self.extractors:
            print(f"[🔍] {mod_name}.py - {class_name}")
            module = self._load_module(mod_name)
            cls = getattr(module, class_name)
            instance = cls()

            for attr in dir(instance):
                if attr.startswith("_") or attr == "cache":
                    continue
                func = getattr(instance, attr)
                if callable(func):
                    result = func(self.file_a, self.file_b)
                    self.results[f"{mod_name}.{attr}"] = result

        total_end = time.time()
        print(f"\n✅ 전체 완료 (총 소요 시간: {total_end - total_start:.2f}s)")

    def get_results(self) -> dict:
        return self.results


# 예시 사용
if __name__ == "__main__":
    file1 = Path("sample1.py")
    file2 = Path("sample2.py")
    runner = FeatureRunner(file1, file2)
    runner.run_all()
    print(runner.get_results())
