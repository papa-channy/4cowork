
from pathlib import Path
from functools import wraps
import subprocess
import time
import re


def measure_time_and_log(func):
    @wraps(func)
    def wrapper(self, file_a: Path, file_b: Path) -> float:
        start = time.time()
        result = func(self, file_a, file_b)
        end = time.time()
        print(f"[✔] {func.__name__:<35} → {result:.4f}  (Time: {end - start:.2f}s)")
        return result
    return wrapper


class ExecutionFeatureExtractor:
    def __init__(self, timeout: float = 1.0):
        self.timeout = timeout

    def _run_and_trace(self, file: Path) -> dict:
        try:
            result = subprocess.run(
                ["python", str(file)],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return {"success": True, "stderr": result.stderr}
        except subprocess.CalledProcessError as e:
            return {"success": False, "stderr": e.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "stderr": "TimeoutError"}
        except Exception as e:
            return {"success": False, "stderr": str(e)}

    def _last_trace_line(self, stderr: str) -> str:
        lines = stderr.strip().splitlines()
        return lines[-1].strip() if lines else ""

    def _error_type(self, stderr: str) -> str:
        match = re.search(r"(?<=\n)[\w]+Error(?=[:\s])", stderr)
        return match.group(0) if match else "UnknownError"

    @measure_time_and_log
    def error_type_overlap_score(self, file_a: Path, file_b: Path) -> float:
        err_a = self._error_type(self._run_and_trace(file_a)["stderr"])
        err_b = self._error_type(self._run_and_trace(file_b)["stderr"])
        return float(err_a == err_b)

    @measure_time_and_log
    def traceback_lastline_sim(self, file_a: Path, file_b: Path) -> float:
        line_a = self._last_trace_line(self._run_and_trace(file_a)["stderr"])
        line_b = self._last_trace_line(self._run_and_trace(file_b)["stderr"])
        return 1.0 if line_a == line_b else 0.0

    @measure_time_and_log
    def traceback_module_name_match(self, file_a: Path, file_b: Path) -> float:
        a = self._last_trace_line(self._run_and_trace(file_a)["stderr"])
        b = self._last_trace_line(self._run_and_trace(file_b)["stderr"])
        extract = lambda txt: re.findall(r"\b\w+\b", txt)
        tokens_a = set(extract(a))
        tokens_b = set(extract(b))
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b) if tokens_a and tokens_b else 0.0

    @measure_time_and_log
    def failed_execution_signal(self, file_a: Path, file_b: Path) -> float:
        a_fail = not self._run_and_trace(file_a)["success"]
        b_fail = not self._run_and_trace(file_b)["success"]
        return float(a_fail == b_fail)

    @measure_time_and_log
    def error_line_depth_ratio(self, file_a: Path, file_b: Path) -> float:
        def depth(stderr: str):
            return stderr.count("File \"")  # stacktrace 깊이
        a_depth = depth(self._run_and_trace(file_a)["stderr"])
        b_depth = depth(self._run_and_trace(file_b)["stderr"])
        return abs(a_depth - b_depth) / max(a_depth, b_depth) if max(a_depth, b_depth) else 0.0
