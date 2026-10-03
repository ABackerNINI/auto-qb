"""重写配置键面基线 tests/fixtures/config_key_surface.txt(键面守卫报红后的处置入口)

生成器单点在 tests/test_config_key_surface.py(build_config_key_surface), 本脚本只负责
加载调用与写盘 —— 键面展开逻辑有两份必然漂移。守卫报红的分流口径(脚本也按它自检):
- 消失键且版本未抬 = 破坏性变更未走升级流程, **拒绝重生成**, 先抬 CURRENT_VERSIONS["config"]
  并在 config/migrations.py 注册迁移;
- 纯新增 = 非破坏(versioning.py 口径刻意不造版本), 直接重生成。
收尾无论哪种现场都要回写 memory-bank/config-reference/keys.md。
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


def _load_guard_module():
    """按路径加载守卫测试模块(生成器/基线读写的单点所在; pytest 不在场也能 import)"""
    spec = importlib.util.spec_from_file_location(
        "test_config_key_surface", REPO / "tests" / "test_config_key_surface.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    guard = _load_guard_module()
    if guard.BASELINE_PATH.exists():
        old_version, old_keys = guard._parse_baseline(guard.BASELINE_PATH.read_text(encoding="utf-8"))
    else:
        old_version, old_keys = 0, set()  # 首次生成: 视为空基线, 全量记新增
    current = guard.build_config_key_surface()
    version = guard.CURRENT_VERSIONS["config"]
    added = sorted(current - old_keys)
    removed = sorted(old_keys - current)
    if removed and version == old_version:
        print("[FAIL] 键面出现消失键但 config 版本未抬 —— 破坏性变更未走升级流程, 拒绝重生成基线")
        print("  消失的键:", " ".join(removed))
        print("  处置: 抬 CURRENT_VERSIONS['config'] + config/migrations.py 注册迁移 + 迁移回归测试后重跑本命令")
        return 1
    guard.BASELINE_PATH.write_text(guard.render_baseline(version, current), encoding="utf-8", newline="\n")
    print(f"[ok] 基线已重写: v{old_version} -> v{version}, {len(old_keys)} -> {len(current)} 键")
    if added:
        print("  新增:", " ".join(added))
    if removed:
        print("  消失:", " ".join(removed))
    if not added and not removed:
        print("  键面无变化(仅版本行/格式刷新)")
    print("  收尾提醒: 回写 memory-bank/config-reference/keys.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
