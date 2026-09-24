"""test_hr_events 测试计划: HR 四类事件的通知文案单点(计划 §11 M4)

## 测试计划(每个测试函数一条)
- test_each_event_has_a_distinct_tag: 四类事件各有标签前缀 —— 用户能在日志里 grep 出「登录失效」这一类
- test_login_text_gives_the_action: 登录失效文案必须给出**动作**(去浏览器登录该站点), 不能只说失败
- test_login_note_is_short_and_tagged: 落站点文件 refresh.reason 的短句也带标签(报告/视图 notes 读它)
- test_fuse_texts_carry_counts_and_deadline: 熔断两类文案分别给出「还差几次」与冷却时刻
- test_page_changed_text_explains_consequence: 改版文案说明后果(不产生新放行)与要人工核对的东西
- test_channel_silent_lists_affected_sites: 通道静默是端点级事件 ⇒ 文案必须列出受影响站点
- test_site_list_order_is_stable: 站点清单顺序稳定(否则同一状态看着像两件事)
"""
import time

from auto_qb.hr import events


def test_each_event_has_a_distinct_tag():
    """四类事件各有标签前缀 —— 用户能在日志里 grep 出「登录失效」这一类"""
    tags = {
        name: events.prefix(name)
        for name in (events.EVENT_LOGIN, events.EVENT_FUSE, events.EVENT_PARSE, events.EVENT_SILENCE)
    }
    assert tags == {
        events.EVENT_LOGIN: "[HR 登录失效]",
        events.EVENT_FUSE: "[HR 熔断]",
        events.EVENT_PARSE: "[HR 页面改版]",
        events.EVENT_SILENCE: "[HR 通道静默]",
    }
    assert len(set(tags.values())) == 4, "四类事件的标签必须互不相同(否则 grep 分不开)"


def test_login_text_gives_the_action():
    """登录失效文案必须给出**动作**(去浏览器登录该站点), 不能只说失败"""
    text = events.login_expired("BTSchool", "命中登录页(档位 A 第 1 页)")
    assert text.startswith("[HR 登录失效]")
    assert "BTSchool" in text
    assert "登录 BTSchool" in text, "文案里必须直接说「去登录哪个站点」"
    assert "命中登录页" in text, "原始原因要保留(排障要看它)"


def test_login_note_is_short_and_tagged():
    """落站点文件 refresh.reason 的短句也带标签(报告/视图 notes 读它)"""
    note = events.login_expired_note("BTSchool", "命中登录页")
    assert note.startswith("[HR 登录失效]")
    assert "本轮未发起刷新" in note, "不能谎称「刷新了」(刷新根本没发生) —— 这是与 completeness 的分界"
    assert len(note) < 200, "站点文件里存的是给人看的短句"


def test_fuse_texts_carry_counts_and_deadline():
    """熔断两类文案分别给出「还差几次」与冷却时刻"""
    failed = events.fetch_failed("BTSchool", 2, 3, "超时")
    assert failed.startswith("[HR 熔断]")
    assert "取数失败(2 次, 距熔断还差 1 次)" in failed

    until = 1_700_000_000.0
    opened = events.fuse_opened("BTSchool", until, "超时")
    assert opened.startswith("[HR 熔断]")
    assert "连续失败达阈值" in opened
    assert f"冷却至 {time.strftime('%m-%d %H:%M:%S', time.localtime(until))}" in opened, "要给绝对时刻(相对时间要心算)"


def test_page_changed_text_explains_consequence():
    """改版文案说明后果(不产生新放行)与要人工核对的东西"""
    text = events.page_changed("BTSchool", "partial", "档位 A 第 1 页未找到 HR 表(疑似改版)")
    assert text.startswith("[HR 页面改版]")
    assert "不产生新放行" in text, "后果要写清楚 —— 否则用户不知道要不要紧张"
    assert "核对站点 HR 页" in text, "要给动作"


def test_channel_silent_lists_affected_sites():
    """通道静默是端点级事件 ⇒ 文案必须列出受影响站点"""
    text = events.channel_silent(3.5, "上次联系后", ("alpha", "beta"))
    assert text.startswith("[HR 通道静默]")
    assert "3.5h" in text
    assert "受影响站点: alpha, beta" in text, "端点级事件要说清谁的取数在被影响"


def test_site_list_order_is_stable():
    """站点清单顺序稳定(否则同一状态看着像两件事)"""
    assert events.summarize_sites(["b", "a", "c"]) == "a, b, c"
    assert events.summarize_sites([]) == ""
