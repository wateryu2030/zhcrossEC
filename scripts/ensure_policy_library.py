#!/usr/bin/env python3
"""
自动化执行：确保政策扩展库存在且达到千条以上。
- 若 data/legal_policies_expanded.json 不存在则自动生成
- 校验种子+扩展合计 >= 1000
- 供 run.sh / 部署前 调用，避免首请求才触发生成
"""
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        from agents.policy_legal import get_full_policy_library
        lib = get_full_policy_library()
        n = len(lib)
        if n < 1000:
            print(f"WARN: policy library has {n} items (expected 1000+)", file=sys.stderr)
            return 1
        print(f"OK: policy library {n} items (1000+)")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
