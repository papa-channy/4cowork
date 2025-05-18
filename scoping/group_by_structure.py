from pathlib import Path
from typing import List, Dict, Tuple
from simhash import Simhash
import libcst as cst
from functools import wraps
from collections import defaultdict

# --------------------
# 🎯 데코레이터: 실패 방지 fallback 지원
# --------------------
def safe_method(fallback=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"[❌ 실패 복구] {func.__name__} 예외 발생 → fallback 적용됨: {e}")
                return fallback if fallback is not None else []
        return wrapper
    return decorator

# --------------------
# 🧠 구조 분석 클래스
# --------------------
class StructuralGrouper:
    def __init__(self, file_paths: List[Path]):
        self.file_paths = file_paths
        self.signatures = {}  # file → {symbols, imports}
        self.fingerprints = {}  # file → Simhash
        self.sim_matrix = {}  # (file1, file2) → distance

    # 1️⃣ 파일에서 def, class, import 추출
    @safe_method(fallback={"symbols": [], "imports": []})
    def extract_signature(self, file: Path) -> Dict:
        code = file.read_text(encoding="utf-8", errors="ignore")
        module = cst.parse_module(code)

        symbols = []
        imports = []

        class Visitor(cst.CSTVisitor):
            def visit_FunctionDef(self, node): 
                symbols.append(node.name.value)

            def visit_ClassDef(self, node): 
                symbols.append(node.name.value)

            def visit_Import(self, node):
                for n in node.names:
                    try:
                        # 1. evaluated_name → string
                        name = getattr(n.evaluated_name, "value", None)
                        # 2. fallback: name.value or str fallback
                        if not name and hasattr(n.name, "value"):
                            name = n.name.value
                        elif not name:
                            name = str(n.name)
                        if isinstance(name, str):
                            imports.append(name)
                    except Exception as e:
                        print(f"[⚠️ import 추출 실패] {n} → {e}")

            def visit_ImportFrom(self, node):
                try:
                    if node.module:
                        mod = getattr(node.module, "attr", None) or getattr(node.module, "value", None)
                        if isinstance(mod, str):
                            imports.append(mod)
                        elif hasattr(mod, "__str__"):
                            imports.append(str(mod))
                except Exception as e:
                    print(f"[⚠️ from import 추출 실패] {node} → {e}")

        module.visit(Visitor())
        return {"symbols": symbols, "imports": imports}


    # 2️⃣ symbol + import → Simhash 생성
    @safe_method(fallback=None)
    def build_fingerprint(self, sig: Dict) -> Simhash:
        features = sig["symbols"] + sig["imports"]
        return Simhash(features)

    # 3️⃣ 거리 계산
    def compute_distance(self, h1: Simhash, h2: Simhash) -> int:
        return h1.distance(h2)

    # 4️⃣ 전체 거리 매트릭스 계산
    def build_similarity_matrix(self):
        for f in self.file_paths:
            sig = self.extract_signature(f)
            self.signatures[str(f)] = sig
            self.fingerprints[str(f)] = self.build_fingerprint(sig)

        for i, f1 in enumerate(self.file_paths):
            for f2 in self.file_paths[i + 1:]:
                h1 = self.fingerprints.get(str(f1))
                h2 = self.fingerprints.get(str(f2))
                if h1 and h2:
                    d = self.compute_distance(h1, h2)
                    self.sim_matrix[(str(f1), str(f2))] = d
                    self.sim_matrix[(str(f2), str(f1))] = d  # 양방향 저장

    # 5️⃣ 특정 파일에 대해 연관도 높은 top-N 파일 선택
    def select_top_related(self, file: str, top_k: int = 3) -> List[str]:
        if not self.sim_matrix:
            self.build_similarity_matrix()

        related = [(f2, d) for (f1, f2), d in self.sim_matrix.items() if f1 == file]
        related.sort(key=lambda x: x[1])  # 거리 오름차순
        return [f for f, _ in related[:top_k]]

    # 6️⃣ 전체 그룹핑 결과 반환
    def group_all_files(self, top_k: int = 3) -> Dict[str, List[str]]:
        if not self.sim_matrix:
            self.build_similarity_matrix()

        groups = {}
        for f in map(str, self.file_paths):
            top_related = self.select_top_related(f, top_k=top_k)
            groups[f] = top_related
        return groups
