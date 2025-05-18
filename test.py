from pathlib import Path
from scoping.first_scope import get_changed_files, basic_filter, git_tool_filter
from scoping.group_by_structure import StructuralGrouper

def main():
    print("🧠 구조 기반 파일 그룹핑 시작...\n")

    # 1️⃣ 변경된 파일 감지 및 스코어 필터링
    changed_files = get_changed_files()
    py_files = basic_filter(changed_files)
    selected_files, score_map = git_tool_filter(py_files)

    print(f"🔍 변경된 파일 수: {len(py_files)}")
    print(f"✅ 그룹핑 대상 파일 수 (선별됨): {len(selected_files)}")

    # 2️⃣ Path 객체로 변환
    selected_paths = [Path(f) for f in selected_files]

    # 3️⃣ Simhash + LibCST 기반 그룹핑
    grouper = StructuralGrouper(selected_paths)
    groups = grouper.group_all_files(top_k=3)

    # 4️⃣ 출력
    for main_file, related in groups.items():
        print(f"\n📁 중심 파일: {main_file}")
        for r in related:
            print(f"   └ 연관: {r}")

if __name__ == "__main__":
    main()
