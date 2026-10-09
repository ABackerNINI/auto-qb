"""HR 日志出口单点: 把「归属层」与「输出档位」挂到 record 上, 由出口收放(计划 26-10-09-0821 §03.4)。

为什么必须有这一层:
- **层** (`hr_domain`) 由**事件**推出(`events.DOMAINS`) —— 调用点只选事件, 于是「通道层事件被贴上
  站点层标签」在代码上**不可表达**; 而不是让每个 `logger.warning` 调用点手写 `extra`(漏一处就漂移)。
- **档位** (`hr_silent`) 是该记录的**归属方**对「这一支是否只进后端 log」的陈述(「预期离线」静默 /
  「WebUI 活跃但扩展未联系」可见)。出口只读不算 —— 产生点描述归属, 出口自己声明收哪一档;
  这正是被否掉的 `extra={"web_silent": True}` 补丁路线的问题所在: 那个写法让产生点必须知道**出口是谁**。

未打标的记录 = 未分层 / 可见 ⇒ 出口按原行为处理(向后兼容; 且漏打标的后果是"多报"而非"漏报")。

出口侧读取器(`is_record_suppressed`)在 `infra/logging.py` —— 键必须被 webui / notify / hr 三侧共用,
放 infra 不成环(依赖方向 hr → infra)。
"""
import logging

from ..infra.logging import DOMAIN_ATTR, SILENT_ATTR
from . import events


def emit(logger: logging.Logger, level: int, message: str, *, event: str = "", silent: bool = False) -> None:
    """HR 侧日志出口: 挂上层与档位后交给 logger

    :param logger: 目标 logger(通常是模块级 `logging.getLogger(__name__)`)
    :param level: 日志级别(级别仍由**调用点**决定 —— 层只影响出口收放, 不改级别)
    :param message: 文案(自 `events.*` 产出)
    :param event: `events.EVENT_*` 之一; 决定归属层(未登记 = 不分层)
    :param silent: True = 只进后端 log(不进前端错误历史 / 不弹通知)
    """
    logger.log(level, message, extra={DOMAIN_ATTR: events.domain_of(event), SILENT_ATTR: bool(silent)})


__all__ = ["emit"]
