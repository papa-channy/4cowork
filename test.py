from pathlib import Path
from scoping.first_scope import get_changed_files, basic_filter, git_tool_filter
from scoping.group_by_structure import StructuralGrouperV2
from scoping.first_scope import get_all_py_files_in_repo

def main():
    print("🧠 구조 기반 파일 그룹핑 시작...\n")

    # 전체 .py 파일 = 연관 후보
    all_py_files = get_all_py_files_in_repo()

    # 변경된 파일 + 중요도 높은 중심 파일 선정
    changed_files = get_changed_files()
    py_changed = basic_filter(changed_files)
    selected_files, score_map = git_tool_filter(py_changed)

    print(f"🔍 변경된 파일 수: {len(py_changed)}")
    print(f"✅ 그룹핑 중심 파일 수: {len(selected_files)}")

    # ✅ 구조 기반 그룹핑
    grouper = StructuralGrouperV2([Path(f) for f in all_py_files])
    groups = {
        f: grouper.select_top_related(f, top_k=3, distance_threshold=40)
        for f in selected_files
    }

    # 결과 출력
    for center, related in groups.items():
        print(f"\n📁 중심 파일: {center}")
        if not related:
            print("   └ (연관 파일 없음)")
        for r in related:
            print(f"   └ 연관: {r}")

if __name__ == "__main__":
    main()
