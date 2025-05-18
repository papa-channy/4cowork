from pathlib import Path
from typing import List, Dict, Tuple
from simhash import Simhash
import libcst as cst
from functools import wraps

# ✅ 의미 없는 import 제거용 stopword
DEFAULT_IMPORT_STOPWORDS = {
    "os", "sys", "json", "yaml", "logging", "Path", "cfg", "dotenv", "load_dotenv",
    "getpass", "subprocess", "platform", "importlib", "inspect",    "pathlib",
    "re", "time", "datetime", "typing"
}

# ✅ 예외 방지용 데코레이터
def safe_method(fallback=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"[❌ fallback] {func.__name__} 예외 → {e}")
                return fallback if fallback is not None else []
        return wrapper
    return decorator

class StructuralGrouperV2:
    def __init__(self, file_paths: List[Path]):
        self.file_paths = file_paths
        self.signatures: Dict[str, Dict] = {}
        self.fingerprints: Dict[str, Simhash] = {}
        self.sim_matrix: Dict[Tuple[str, str], float] = {}

    # ✅ 구조 추출: def, class, import
    @safe_method(fallback={"symbols": [], "imports": []})
    def extract_signature(self, file: Path) -> Dict:
        code = file.read_text(encoding="utf-8", errors="ignore")
        module = cst.parse_module(code)

        symbols, imports = [], []

        class Visitor(cst.CSTVisitor):
            def visit_FunctionDef(self, node): symbols.append(node.name.value)
            def visit_ClassDef(self, node): symbols.append(node.name.value)
            def visit_Import(self, node):
                for n in node.names:
                    try:
                        name_obj = getattr(n, "name", None)
                        if hasattr(name_obj, "value"):
                            name_val = name_obj.value
                        elif isinstance(name_obj, str):
                            name_val = name_obj
                        else:
                            name_val = str(name_obj)
                        if isinstance(name_val, str):
                            imports.append(name_val)
                    except Exception as e:
                        print(f"[⚠️ import 추출 실패] {n} → {e}")

            def visit_ImportFrom(self, node):
                try:
                    if node.module:
                        name_obj = node.module
                        if hasattr(name_obj, "value"):
                            name_val = name_obj.value
                        elif hasattr(name_obj, "name") and hasattr(name_obj.name, "value"):
                            name_val = name_obj.name.value
                        elif isinstance(name_obj, str):
                            name_val = name_obj
                        else:
                            name_val = str(name_obj)
                        if isinstance(name_val, str):
                            imports.append(name_val)
                except Exception as e:
                    print(f"[⚠️ from import 추출 실패] {node} → {e}")

        module.visit(Visitor())
        return {"symbols": symbols, "imports": imports}

    # ✅ Simhash 계산 (기본 import는 정제)
    @safe_method(fallback=None)
    def build_fingerprint(self, sig: Dict) -> Simhash:
        filtered_imports = [imp for imp in sig["imports"] if imp not in DEFAULT_IMPORT_STOPWORDS]
        weighted_imports = filtered_imports + filtered_imports[:len(filtered_imports)//2]  # import 0.5 가중치
        features = sig["symbols"] + weighted_imports
        if not features:
            features = ["__empty__"]
        return Simhash(features)

    # ✅ 전체 유사도 매트릭스 계산
    def build_similarity_matrix(self):
        for f in self.file_paths:
            sig = self.extract_signature(f)
            self.signatures[str(f)] = sig
            self.fingerprints[str(f)] = self.build_fingerprint(sig)

        for i, f1 in enumerate(self.file_paths):
            for f2 in self.file_paths[i + 1:]:
                f1s, f2s = str(f1), str(f2)
                h1, h2 = self.fingerprints.get(f1s), self.fingerprints.get(f2s)
                if not h1 or not h2:
                    continue

                dist = h1.distance(h2)

                # ✅ 보정 항목 계산
                sig1 = self.signatures.get(f1s, {})
                sig1_imports = sig1.get("imports", [])
                f2_stem = Path(f2).stem.lower()
                import_hit = any(
                    imp.lower().split('.')[-1] == f2_stem
                    for imp in sig1.get("imports", [])
                )

                import_bonus = 5 if import_hit else 0
                same_folder_bonus = 8 if f1.parent == f2.parent else 0
                same_filename_bonus = 3 if f1.stem.lower() == f2.stem.lower() else 0

                score = dist - import_bonus - same_folder_bonus - same_filename_bonus

                self.sim_matrix[(f1s, f2s)] = score
                self.sim_matrix[(f2s, f1s)] = score

    # ✅ 특정 파일에 대해 연관 높은 top-N 반환
    def select_top_related(self, file: str, top_k: int = 3, distance_threshold: int = 40) -> List[str]:
        if not self.sim_matrix:
            self.build_similarity_matrix()
        related = [(f2, d) for (f1, f2), d in self.sim_matrix.items()
                   if f1 == file and d < distance_threshold]
        related.sort(key=lambda x: x[1])
        return [f for f, _ in related[:top_k]]

    # ✅ 전체 파일 그룹핑 수행
    def group_all_files(self, top_k: int = 3, distance_threshold: int = 40) -> Dict[str, List[str]]:
        if not self.sim_matrix:
            self.build_similarity_matrix()
        return {
            str(f): self.select_top_related(str(f), top_k=top_k, distance_threshold=distance_threshold)
            for f in self.file_paths
        }
