"""test_hr_events 测试计划: HR 事件文案单点(events.py)与日志出口(log.py)

本文件是 hr 首轮变异审计(issue 26-10-10-1108-test-hr-mutation-runtime-worker)为
`events.py` / `log.py` 补的守阵 —— 这两个模块此前**没有任何专属池文件**(池里只有间接消费方),
故整片文案/分层分支落进 `survived`。守阵口径: 断言**语义锚点**(标签前缀 / 站点名 / 动作引导 /
证据分支), 而非逐字节抄全文 —— 措辞可演进, 锚点不可丢。

## 测试计划(每个测试函数一条)
- test_prefix_known_event_uses_label: 已登记事件 -> `[HR <中文标签>]`
- test_prefix_unregistered_event_falls_back_to_raw: 未登记事件 -> `[HR <原值>]`(不是 `[HR None]`)
- test_login_expired_message_action_and_site: 登录失效告警带标签前缀 + 站点名 + 「去浏览器登录」动作
- test_login_expired_note_short_sentence: 写进 wave.notes 的短句带同一标签前缀与站点名
- test_page_changed_message_prefix_and_action: 页面改版文案带 `[HR 页面改版]` 前缀
- test_order_broken_message_text: 排序失效文案 = 标签 + 详情 + 强制早停 + 改版核对引导
- test_counter_mismatch_streak_tail_only_when_over_one: `(已连续 N 波)` 只在 streak>1 时出现(0/1 都不出现)
- test_counter_mismatch_message_anchors: 计数对不平文案 = 标签 + 实抓/声明行数 + `--hr-once` 走查引导
- test_lane_persistent_failure_message_anchors: 连续多波失效文案带标签前缀与走查引导
- test_retention_violation_message_text: 流转守恒不达标文案带标签 + 两侧百分比 + 观察期引导
- test_zero_listing_message_text: 零行波文案带标签 + 确认戳失效说明
- test_channel_silent_evidence_branches: 三种证据(rejected/web_active/none)各自的动作文案齐全
- test_channel_silent_sites_join_and_empty_placeholder: 受影响站点按 ", " 拼接; 空集回落占位串
- test_channel_silent_note_tail_appended_only_when_present: note 只在非空时以空格拼接(空/缺省不留尾巴)
- test_emit_sets_domain_and_silent_flags: 出口挂上归属层与档位(默认可见; 已知事件 -> 其层; 未登记 -> 空层)
"""
import logging

from auto_qb.hr import events
from auto_qb.hr import log as hr_log
from auto_qb.infra.logging import DOMAIN_ATTR, SILENT_ATTR

# ---------- events: prefix / domain ----------


def test_prefix_known_event_uses_label():
    assert events.prefix(events.EVENT_LOGIN) == "[HR 登录失效]"
    assert events.prefix(events.EVENT_PARSE) == "[HR 页面改版]"
    assert events.prefix(events.EVENT_SILENCE) == "[HR 通道静默]"
    assert events.prefix(events.EVENT_CHANNEL) == "[HR 通道不可用]"


def test_prefix_unregistered_event_falls_back_to_raw():
    """未登记事件原样回填 —— 缺省值绝不能是 None(否则日志里出现 `[HR None]`)"""
    assert events.prefix("自定义事件") == "[HR 自定义事件]"
    assert "None" not in events.prefix("未登记")


# ---------- events: 各类文案 ----------


def test_login_expired_message_action_and_site():
    msg = events.login_expired("pt.example.com", "页面是登录页")
    assert msg.startswith("[HR 登录失效]")
    assert "pt.example.com" in msg
    assert "请在该浏览器里登录" in msg
    assert "页面是登录页" in msg


def test_login_expired_note_short_sentence():
    msg = events.login_expired_note("pt.example.com", "详情")
    assert msg.startswith("[HR 登录失效]")
    assert "本波未继续" in msg and "pt.example.com" in msg and "详情" in msg


def test_page_changed_message_prefix_and_action():
    msg = events.page_changed("pt.example.com", "表头缺失", "无 HR 编号列")
    assert msg.startswith("[HR 页面改版]")
    assert "表头缺失" in msg and "无 HR 编号列" in msg
    assert "请核对站点 HR 页是否改版" in msg


def test_order_broken_message_text():
    msg = events.order_broken("pt.example.com", "行序逆序")
    assert msg.startswith("[HR 页面改版]")
    assert "排序假设不成立(行序逆序)" in msg
    assert "该档强制早停" in msg
    assert msg.endswith("(失效点之前数据有效) —— 请核对 HR 页是否改版"), msg


def test_counter_mismatch_streak_tail_only_when_over_one():
    """streak 尾注阈值: 0 与 1 都不出现, >=2 才点名(与 ERROR 升级信号呼应)"""
    base = events.counter_mismatch("pt.example.com", "A", 5, 6)
    assert "计数对不平: 实抓 5 行" in base  # 无尾注时冒号紧接「实抓」
    assert "(已连续" not in base

    one = events.counter_mismatch("pt.example.com", "A", 5, 6, streak=1)
    assert "(已连续" not in one

    two = events.counter_mismatch("pt.example.com", "A", 5, 6, streak=2)
    assert "(已连续 2 波)" in two

    three = events.counter_mismatch("pt.example.com", "A", 5, 6, streak=3)
    assert "(已连续 3 波)" in three


def test_counter_mismatch_message_anchors():
    msg = events.counter_mismatch("pt.example.com", "A", 5, 6, streak=2)
    assert msg.startswith("[HR 页面改版]")
    assert "实抓 5 行" in msg and "站点声明 6 行" in msg
    assert msg.endswith("若持续对不平, 可能是计数口径校准错误而非站点改版 —— 请跑 --hr-once 走查核对, "
                        "或摘除该站点的计数覆写恢复现状"), msg


def test_lane_persistent_failure_message_anchors():
    msg = events.lane_persistent_failure("pt.example.com", "A", 3, "表头缺失")
    assert msg.startswith("[HR 页面改版]")
    assert "档位 A 已连续 3 波失效" in msg and "表头缺失" in msg
    assert msg.endswith("疑似改版 —— 建议跑 --hr-once 走查核对页面结构(期间该档维持原状态, 命中照常)"), msg


def test_retention_violation_message_text():
    msg = events.retention_violation("pt.example.com", 0.5)
    assert msg.startswith("[HR 页面改版]")
    assert "50%" in msg  # 实算留存率
    assert "70%" in msg  # 下限(LANE_RETENTION_MIN * 100)
    assert msg.endswith("失踪个体维持管束走观察期"), msg


def test_zero_listing_message_text():
    msg = events.zero_listing("pt.example.com")
    assert msg.startswith("[HR 页面改版]")
    assert "清单为 0" in msg
    assert msg.endswith("清单再现非零行时确认戳自动失效"), msg


# ---------- events: channel_silent ----------


def test_channel_silent_evidence_branches():
    rejected = events.channel_silent(2.0, "上次联系后", ["b", "a"], evidence="rejected")
    assert rejected.startswith("[HR 通道静默]")
    assert "2.0h" in rejected and "上次联系后" in rejected
    assert (
        "| 扩展**在联系但被拒**(401/403) ⇒ 请核对 hr_check.channel.token 与 origin 白名单"
        "(这是配置态问题, 不是浏览器没开)" in rejected
    ), rejected

    web = events.channel_silent(1.0, "启动以来", ["a"], evidence="web_active")
    assert ("| **有人在看 WebUI, 但端点未收到任何联系** ⇒ 扩展可能被停用 / 卸载 / 未启用, "
            "或跨机隧道与网络不通" in web), web

    none = events.channel_silent(1.0, "启动以来", ["a"])
    assert ("| 端点未收到任何联系: 浏览器可能未运行, **或** 扩展未启用 / 未安装"
            "(二者后端不可分辨, 请自行核对)" in none), none


def test_channel_silent_sites_join_and_empty_placeholder():
    joined = events.channel_silent(1.0, "启动以来", ["b", "a"], evidence="rejected")
    assert "受影响站点: b, a" in joined, "站点清单按 ', ' 拼接(顺序由调用方定)"
    empty = events.channel_silent(1.0, "启动以来", [])
    assert "(无启用中的站点)" in empty
    assert "XX" not in empty


def test_channel_silent_note_tail_appended_only_when_present():
    no_note = events.channel_silent(1.0, "启动以来", ["a"], evidence="none")
    assert "XXXX" not in no_note, "缺省 note 不得留残迹"
    noted = events.channel_silent(1.0, "启动以来", ["a"], note="备注", evidence="none")
    assert noted.endswith("备注") and "None" not in noted
    blank = events.channel_silent(1.0, "启动以来", ["a"], note="", evidence="none")
    assert "XXXX" not in blank
    assert not blank.endswith(" "), "空 note 不该拼出一个尾空格"


# ---------- log.emit ----------


def test_emit_sets_domain_and_silent_flags():
    """出口把归属层与档位挂到 record 上: 已知事件 -> 其层; 未登记 -> 空层; 默认可见"""
    records = []

    class _Collect(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("auto_qb.test.hr.emit")
    logger.handlers = [_Collect()]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    hr_log.emit(logger, logging.WARNING, "hello", event=events.EVENT_PARSE)
    hr_log.emit(logger, logging.INFO, "world", event=events.EVENT_LOGIN, silent=True)
    hr_log.emit(logger, logging.INFO, "plain")

    assert getattr(records[0], DOMAIN_ATTR) == events.DOMAIN_SITE
    assert getattr(records[0], SILENT_ATTR) is False, "默认不静默(可见)"
    assert getattr(records[1], DOMAIN_ATTR) == events.DOMAIN_ACCOUNT
    assert getattr(records[1], SILENT_ATTR) is True
    assert getattr(records[2], DOMAIN_ATTR) == "", "未登记事件 = 不分层"
