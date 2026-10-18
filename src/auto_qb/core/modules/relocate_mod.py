"""RelocateModule: 整组迁移(A/C 别名)模块 —— P1 只立段认领与开关面, 引擎随 P2 起落地

计划 26-10-18-1604 §04:
- P1(本文件当前形态)只做配置面接线: sections() 认领 relocate 顶层段, 满足段认领完备
  守阵(test_modules_p6: 每个配置顶层段必须有主, 否则落「未认领段 WARN + 全量重建兜底」);
  apply 按段相等短路, 段变化只缓存生效配置 —— enabled=false(缺省)时行为为零(黄金法则 2)。
- P2 起逐期长出真实行为: 别名单元 plan() 纯函数/只读预检接口(relocate_units.py)、
  迁移状态机与 precheck-add 三分流(本文件), 与 grouping_mod 的物理位置 resolver 联动。
  本文件 P1 的缓存字段与 apply 回执即那时的最小骨架, 不留双份实现。
"""
import logging
from typing import Optional

from ..module import AppContext, ApplyResult, BaseModule

logger = logging.getLogger(__name__)


class RelocateModule(BaseModule):
    """整组迁移模块: 认领 relocate 段; P1 无引擎无副作用(配置面先行, 计划 §04 P1)

    !start/stop 在 P1 是显式无操作: 功能未接线前, 即使 relocate.enabled=true 也不能
    凭空建任务/建链接 —— 发出任何动作的那个版本(P3 执行体)才配拥有副作用。
    """

    name = "relocate"

    def __init__(self) -> None:
        self._ctx: Optional[AppContext] = None
        self._conf = None  # 生效的 RelocateConfig(P2 引擎消费; P1 仅缓存)

    def sections(self) -> tuple[str, ...]:
        return ("relocate", )

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        """P1: 只记录上下文与初始配置, 不建任务不建链接(dry_run 同样零副作用)"""
        self._ctx = ctx
        self._conf = ctx.config.relocate

    def stop(self) -> None:
        return None  # P1 无运行期资源可停

    def apply(self, old, new) -> ApplyResult:
        """段相等短路(统一挂载口径); 段变化 = 换对象即生效(P1 仅缓存, 引擎见 P2/P3)

        getattr 兜底与 TrafficSnapshotModule.apply 同口径: 测试替身(SimpleNamespace)
        只钉自己关心的段, 缺段按「未变化」处理, 不让无关测试连带红。
        """
        if getattr(old, "relocate", None) == getattr(new, "relocate", None):
            return ApplyResult(self.name)
        self._conf = getattr(new, "relocate", None)
        return ApplyResult(self.name, "reloaded", "relocate 段已更新(P1 仅缓存生效配置, 引擎随 P2 落地)")

    def subscribe(self, phases) -> None:
        return None  # P1 不订阅任何相位
