
from pathlib import Path
from functools import wraps
import time
import re
from collections import Counter


def measure_time_and_log(func):
    @wraps(func)
    def wrapper(self, file_a: Path, file_b: Path) -> float:
        start = time.time()
        result = func(self, file_a, file_b)
        end = time.time()
        print(f"[✔] {func.__name__:<30} → {result:.4f}  (Time: {end - start:.2f}s)")
        return result
    return wrapper


class SyntaxPatternFeatureExtractor:
    def __init__(self):
        self.keywords = [
            "def", "class", "if", "else", "elif", "for", "while", "try", "except", "with",
            "return", "import", "from", "as", "pass", "break", "continue", "yield", "await"
        ]

    def _read_text(self, file: Path) -> str:
        return file.read_text(encoding="utf-8", errors="ignore")

    def _count_keyword_freq(self, text: str) -> Counter:
        words = re.findall(r"\b[a-zA-Z_]+\b", text)
        return Counter(w for w in words if w in self.keywords)

    def _cosine_sim(self, freq_a: Counter, freq_b: Counter) -> float:
        all_keys = set(freq_a) | set(freq_b)
        dot = sum(freq_a[k] * freq_b[k] for k in all_keys)
        norm_a = sum(v**2 for v in freq_a.values())**0.5
        norm_b = sum(v**2 for v in freq_b.values())**0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    @measure_time_and_log
    def try_except_ratio(self, file_a: Path, file_b: Path) -> float:
        def ratio(text: str):
            total = text.count("try") + text.count("except")
            lines = len(text.splitlines())
            return total / lines if lines else 0
        a = self._read_text(file_a)
        b = self._read_text(file_b)
        return abs(ratio(a) - ratio(b))

    @measure_time_and_log
    def has_f_string(self, file_a: Path, file_b: Path) -> float:
        def fstring_flag(text: str):
            return any(re.search(r'f"[^"]*"', text) or re.search(r"f'[^']*'", text))
        return float(fstring_flag(self._read_text(file_a)) != fstring_flag(self._read_text(file_b)))

    @measure_time_and_log
    def keyword_token_vector_sim(self, file_a: Path, file_b: Path) -> float:
        text_a = self._read_text(file_a)
        text_b = self._read_text(file_b)
        freq_a = self._count_keyword_freq(text_a)
        freq_b = self._count_keyword_freq(text_b)
        return self._cosine_sim(freq_a, freq_b)
