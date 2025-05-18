import subprocess, yaml, statistics
from pathlib import Path
from collections import defaultdict

USER_CONFIG_PATH = Path("config/user_config.yml")

def get_changed_files() -> list[str]:
    """
    git status 기반으로 변경된 파일 중
    - user_config.yml에서 지정한 확장자만 허용
    - 숨김 디렉토리 및 캐시/가상환경 관련 폴더 제거
    - 실제로 존재하지 않는 파일은 제거
    """
    with USER_CONFIG_PATH.open(encoding="utf-8") as f:
        user_cfg = yaml.safe_load(f)
    allowed_exts = set(user_cfg.get("change detection", {}).get("provider", []))

    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()

    changed = []
    for line in lines:
        if not line.strip():
            continue
        status, path = line[:2].strip(), line[3:].strip()
        if status not in {"M", "A", "??"}:
            continue
        if not any(path.endswith(ext) for ext in allowed_exts):
            continue

        p = Path(path)
        parts = p.parts

        if any(part.startswith(".") for part in parts):
            continue
        if any(part in {
            "__pycache__", ".ipynb_checkpoints", ".mypy_cache",
            ".pytest_cache", "build", "dist", "venv"
        } for part in parts):
            continue
        if not p.exists():  # 🔥 존재하지 않는 파일 제거
            continue

        changed.append(str(p))
    return changed


def basic_filter(files: list[str]) -> list[str]:
    """
    확장자 기준 .py만 추출 → PyCG 등 분석용
    """
    return [f for f in files if f.endswith(".py")]


def git_tool_filter(files: list[str]) -> tuple[list[str], dict[str, float]]:
    """
    각 파일별 점수 계산 후 기준 이상 파일 추출
    점수 기준:
    - 함수 수 × 0.1
    - 변경 줄 수 비중 × 0.05
    - 커밋 수 비중 × 0.02
    - 최근 7일 커밋 여부 +0.1
    - 메인 브랜치 작업 여부 +0.1
    """
    score_map = defaultdict(float)
    total_diff_lines = 0
    file_diff_lines = {}
    struct_counts = {}  # file → {"def": int, "class": int, "from": int}
    recent_commit_count = {}
    author_counts = {}
    all_struct_def = []
    all_struct_class = []
    all_struct_from = []

    # 🔹 구조 파싱 (def/class/from 구 count)
    for f in files:
        try:
            text = Path(f).read_text(encoding="utf-8", errors="ignore")
            d = text.count("def ")
            c = text.count("class ")
            fr = text.count("from ")
            struct_counts[f] = {"def": d, "class": c, "from": fr}
            all_struct_def.append(d)
            all_struct_class.append(c)
            all_struct_from.append(fr)
        except:
            struct_counts[f] = {"def": 0, "class": 0, "from": 0}

    # 중간값 계산
    def_median = statistics.median(all_struct_def) if all_struct_def else 0
    class_median = statistics.median(all_struct_class) if all_struct_class else 0
    from_median = statistics.median(all_struct_from) if all_struct_from else 0

    # 🔹 git diff 줄 수 계산
    result = subprocess.run(["git", "diff", "--numstat"] + files, capture_output=True, text=True)
    for line in result.stdout.strip().splitlines():
        try:
            added, removed, fname = line.split("\t")
            total = int(added) + int(removed)
            file_diff_lines[fname] = total
            total_diff_lines += total
        except:
            continue

    # 🔹 최근 커밋 수 (5일 기준)
    for f in files:
        result = subprocess.run(["git", "log", "--since=5.days", "--pretty=format:%s", "--", f], capture_output=True, text=True)
        commits = result.stdout.strip().splitlines()
        recent_commit_count[f] = len(commits)

    # 🔹 작성자 수
    all_author_counts = []
    for f in files:
        result = subprocess.run(["git", "log", "--format=%an", "--", f], capture_output=True, text=True)
        authors = set(result.stdout.strip().splitlines())
        count = len(authors)
        author_counts[f] = count
        all_author_counts.append(count)

    author_avg = statistics.mean(all_author_counts) if all_author_counts else 0

    # 🔹 점수 계산
    selected = []
    for f in files:
        score = 0.0
        counts = struct_counts.get(f, {})
        over_count = sum([
            counts.get("def", 0) > def_median,
            counts.get("class", 0) > class_median,
            counts.get("from", 0) > from_median
        ])
        if over_count == 3:
            score += 1.0
        elif over_count == 2:
            score += 0.7
        elif over_count == 1:
            score += 0.4

        score += recent_commit_count.get(f, 0) * 0.1

        fname_key = Path(f).as_posix()
        if total_diff_lines > 0:
            score += (file_diff_lines.get(fname_key, 0) / total_diff_lines) * 1

        if author_counts.get(f, 0) > author_avg:
            score += 0.2

        score = round(score, 4)
        score_map[f] = score
        if score >= 0.4:
            selected.append(f)

    return selected, dict(score_map)
