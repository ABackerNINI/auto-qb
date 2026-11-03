"""RM08 附加轮(读侧): /api/sites/missing groups 分组字段 —— 缺失站点合并 WebUI 读侧 3 条。

验证面对准计划 plans/26-11-04-0140-plan-real-rm08-addendum-missing-merge.html §03 与功能计划
plans/26-11-03-2337-plan-missing-site-tracker-merge.html(M3/M4 已入库): groups 分组契约
(RM08-10)· 负向空场 + 已配置域不粘合(RM08-11, L3 红验)· 三分支自适应引导数据前提(RM08-12)。

造场(复用 RM10 附加轮配方, tests-real/rm10_notify/test_rm10_export_merge.py build_scene):
副实例(空库草稿本, bypass_local_auth 空凭据直连 —— 产品配置零 token 落盘, D2)造 paused 假种子
(lib/torrent.build_stream + real-fake 标签, 409 删旧重加 §2.9), 逐枚 /torrents/addTrackers
追加设计 announce。announce 全部互异 127.x IP 字面量 + 死端口 :1(RM10 实测:
extract_tracker_hostnames 取 urlparse().hostname 不含端口, 同 IP 异端口塌缩成一域, 故用互异
IP), 零 DNS 零外连; 种子全程 paused 不 announce。

读侧驱动 = dev.webui 安全模式(规程 §2.4): 每条起一份关自动任务的最小配置产品进程连副实例,
只发 GET /api/sites/missing, 零写侧操作; 断言全部落在端点载荷上。

跑法: `uv run pytest tests-real/rm08_webui_read/test_rm08_missing_groups.py -q --no-cov`
(同目录 conftest 串行锁自动生效)。收尾: real.seed.rm --all + real.seed.clean 清自造种子与
.work 残留。
"""
from __future__ import annotations

import contextlib
import sys
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import test_rm08_webui_read as base  # noqa: E402 —— 复用同片基座(product/清场/造种/web 客户端)
from lib import app, instances, torrent  # noqa: E402
from auto_qb.infra.utils import extract_tracker_hostnames  # noqa: E402

HR_SHAPE = {
    "required_seeding_time": "3D",
    "required_share_ratio": 0,
    "extra_seeding_time": "12H",
    "condition": "80%",
}

# 共现设计(与 RM10 同款): A=[7,12] B=[12,13] C=[14] ⇒ 合并组 {7,12,13}(传递闭包) + 单元素 {14}
H_A, H_B, H_C, H_D = "127.0.0.7", "127.0.0.12", "127.0.0.13", "127.0.0.14"
SCENE_MERGE = [
    ("rm08grp-a.bin", [H_A, H_B]),
    ("rm08grp-b.bin", [H_B, H_C]),
    ("rm08grp-c.bin", [H_D]),
]
CONFIGURED_KEY = "rm08grp_invalid"  # 测试配置已配条目: 与全部 announce 域零命中(保缺失面成立)
CONFIGURED_DOMAIN = "rm08grp.invalid"


# ---------------------------------------------------------------- 基座(配置/产品进程/造场)


GRP_CONFIG_TEMPLATE = """\
config:
    schema_version: 5
    qbittorrent:
        host: 127.0.0.1
        port: {qb_port}
        username: ""
        password: ""
        api_key: ""
    data_dir: "{data_dir}"
    main_tick: 2S
    sync_interval: 1.5S
    interval: 86400S
    max_tasks_per_tick: 20
    remove_similar_tags: false
    skip_checking_tag: zSkipChecked
    add_episode_tags:
        enabled: false
    delete_tags: []
    hr:
        add_tag: ""
        add_category: ""
        overwrite_category: false
        add_tag_for_satisfied: ""
        add_category_for_satisfied: ""
        overwrite_category_for_satisfied: false
    log:
        level: INFO
    grouping:
        enabled: false
        missing_tag: ""
        check_missing_files: false
    web:
        enabled: true
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
    trackers:
{trackers_block}    notify:
        enabled: false
"""


def tracker_entry_block(key: str, domain: str) -> str:
    """trackers 段单条目 YAML(8 空格起; RM10 EXPORT_CONFIG_TEMPLATE 同款字段形状)。"""
    return (
        f"        {key}:\n"
        f"            domains:\n"
        f"                - {domain}\n"
        f"            tags:\n"
        f"                - Rm08Grp\n"
        f"            upload_speed_limit: 0KiB/s\n"
        f"            download_speed_limit: 0KiB/s\n"
        f"            hr:\n"
        f"                required_seeding_time: 3D\n"
        f"                required_share_ratio: 0\n"
        f"                extra_seeding_time: 12H\n"
        f"                condition: 80%\n"
    )


def write_grp_cfg(case: Path, trackers_block: str) -> tuple[Path, int]:
    """生成 dev.webui 同款最小配置 + trackers 段: 指**副实例**空凭据(bypass_local_auth, §2.5.2)。

    自带断言: 不指主实例 / api_key 为空(token 落盘红线) / schema_version: 5(§2.7)。
    """
    cfg = case / "config.yml"
    web_port = app.free_port()
    cfg.write_text(
        GRP_CONFIG_TEMPLATE.format(
            qb_port=instances.SECONDARY,
            data_dir=(case / "data").as_posix(),
            web_port=web_port,
            trackers_block=trackers_block,
        ),
        encoding="utf-8",
    )
    text = cfg.read_text(encoding="utf-8")
    assert f"port: {instances.SECONDARY}" in text, f"配置没指向副实例(空凭据草稿本): {cfg}"
    assert f"port: {instances.PRIMARY}" not in text, f"配置指向了主实例(需 token 落盘), 拒跑: {cfg}"
    assert 'api_key: ""' in text, f"api_key 非空 —— token 落盘红线: {cfg}"
    assert "schema_version: 5" in text, f"配置缺 schema_version: 5(会触发迁移改写), 拒跑: {cfg}"
    return cfg, web_port


@contextlib.contextmanager
def product_case_grp(name: str, trackers_block: str):
    """起一份 dev.webui 安全模式产品进程(trackers 段可注入), 收尾必杀进程树(基座同款)。"""
    case = base.case_dir(name)
    cfg, port = write_grp_cfg(case, trackers_block)
    proc = app.AppProc(base._popen_auto_qb(cfg), case, cfg)
    try:
        assert proc.wait_web(), f"产品 WEB 未启动: 日志尾部 {proc.log()[-400:]!r}"
        base.web_ready(port)
        yield case, port, proc
    finally:
        base.kill_tree(proc)


def add_trackers(qb, ih: str, urls: list[str]) -> None:
    """给已加种子追加 announce(qB 原生 /torrents/addTrackers; hash 单数, urls 换行分隔, RM10 同款)。"""
    body = urllib.parse.urlencode({"hash": ih, "urls": "\n".join(urls)}).encode()
    qb._call("/torrents/addTrackers", body, "application/x-www-form-urlencoded")


def build_scene(case_name: str, specs: list[tuple[str, list[str]]]) -> tuple[Path, object, dict]:
    """造场: paused 假种子 + 设计 announce + 校验 tracker 视图可见。返回 (case 目录, qb, {名: infohash})。"""
    d = base.case_dir(case_name)
    qb = instances.make(instances.SECONDARY)
    base.rm_all_fakes(qb)  # 开跑先清场(含上轮半途失败的残留; 各片自清是幂等口径)
    savepath = d / "seeds"
    savepath.mkdir(parents=True, exist_ok=True)
    seeds: dict = {}
    try:
        for name, hosts in specs:
            urls = [f"http://{h}:1/announce" for h in hosts]
            raw, ih = torrent.build_stream(name, 256 * 1024, "random", f"rm08grp-{name}", urls[0])
            base._add_retry(qb, raw, str(savepath), ih, paused=True)
            base.settle(qb, ih)
            if len(urls) > 1:
                add_trackers(qb, ih, urls[1:])
            seeds[name] = ih
        for name, hosts in specs:
            ih = seeds[name]
            want = set(hosts)
            base.wait_until(
                lambda ih=ih, want=want: want <= extract_tracker_hostnames(qb.trackers(ih)),
                15,
                f"{name} 的 announce 未在 tracker 视图出现: want={sorted(want)}",
            )
    except BaseException:
        base.rm_all_fakes(qb)  # 造场半途失败也自清, 不留残留
        raise
    return d, qb, seeds


def assert_entry_shape(entry: dict, domains: list) -> None:
    """条目形态单点: domains/空标签(IP 形态已知正确行为)/限速占位/hr 示例段(与 sites 同源)。"""
    assert entry["domains"] == domains, f"entry.domains 应 {domains}, 实际 {entry['domains']}"
    assert entry["tags"] == [""], f"IP 形态默认标签应为空串(已知正确行为), 实际 {entry['tags']!r}"
    assert entry["upload_speed_limit"] == "0KiB/s" and entry["download_speed_limit"] == "0KiB/s", \
        f"限速占位应为 UNLIMITED_SPEED, 实际 {entry}"
    assert entry["hr"] == HR_SHAPE, f"hr 示例段漂移: {entry['hr']}"


def must_be_red(fn, desc: str) -> None:
    """红验自证: fn() 必须 AssertionError, 不红即红验失败(RM10-13 同款口径)。"""
    try:
        fn()
    except AssertionError:
        return
    raise AssertionError(f"红验失败: {desc} 的故意错位断言没有红")


def _wrong_expect_site(sm: dict, dom: str) -> None:
    assert any(s["domain"] == dom for s in sm["sites"]), f"{dom} 应在 sites(故意错位)"


def _wrong_expect_glued(groups: list, p: str, q: str) -> None:
    assert any({p, q} <= set(g["domains"]) for g in groups), f"{p}/{q} 应同组(故意错位)"


# ================================================================ RM08-10


def test_rm08_10_groups_contract():
    """[RM08-10] groups 分组契约: 共现传递闭包 + 单元素组 + 组名顺延不与 sites 撞

    前置: 副实例(56590)在线且空库(除本轮自造); dev.webui 产品连副实例(trackers 段配
      rm08grp.invalid 不命中域); 3 枚 paused 假种子按 SCENE_MERGE 共现设计。
    副作用: 副实例加 3 枚 real-fake 假种子(全程 paused); 写 .work/rm08/rm08_10/ 临时目录;
      只读 GET /api/sites/missing。
    回滚: 删自造种子(连数据) + 产品进程 taskkill /F /T + 临时目录随 case_dir 清场。
    失败判据: sites 原形破坏(逐域名条目缺失/改名/entry 漂移) / 合并组未闭包(3 元素组缺失或
      拆散) / 组名与 sites 撞名或未按 taken 序列顺延 / 组 entry.domains != 组内全域名 sorted /
      IP 形态标签非空串 / hr·限速示例段与 sites 条目不同源。
    """
    d, qb, seeds = build_scene("rm08_10", SCENE_MERGE)
    try:
        assert len(qb.torrents()) == 3, f"副实例应为恰 3 枚种子(设计场), 实际 {len(qb.torrents())}"
        with product_case_grp("rm08_10", tracker_entry_block(CONFIGURED_KEY, CONFIGURED_DOMAIN)) as (
            case, port, _proc
        ):
            sm = base.web_req(port, "GET", "/api/sites/missing")
            assert sm["torrents"] == 3 and sm["domains"] == 4, \
                f"计数漂移: torrents={sm['torrents']} domains={sm['domains']}"

            # sites 原形: 逐域名 name/domain/entry
            sites = {s["domain"]: s for s in sm["sites"]}
            assert set(sites) == {H_A, H_B, H_C, H_D}, f"sites 域名集漂移: {sorted(sites)}"
            for dom, s in sites.items():
                assert s["name"] == dom.replace(".", "_"), f"site 名漂移: {dom} -> {s['name']}"
                assert_entry_shape(s["entry"], [dom])

            # groups: 合并组(传递闭包)在前 + 单元素组在后, 组间 sorted
            groups = sm["groups"]
            assert [g["domains"] for g in groups] == [[H_B, H_C, H_A], [H_D]], \
                f"groups 分组漂移: {[g['domains'] for g in groups]}"
            names = {g["name"] for g in groups}
            assert names == {"127_0_0_7_1", "127_0_0_14_1"}, \
                f"组名漂移(应代表域名派生 + taken 序列顺延): {names}"
            assert not names & {s["name"] for s in sm["sites"]}, "组名与 sites 撞名(taken 序列失守)"
            for g in groups:
                assert_entry_shape(g["entry"], g["domains"])
                rep = min(g["domains"], key=lambda x: (len(x), x))
                assert g["name"].startswith(rep.replace(".", "_")), \
                    f"组名应自代表域名(组内最短)派生: {g['name']}"
            base.metric(f"RM08-10 sites={len(sm['sites'])} groups={len(groups)} "
                        f"合并组={groups[0]['domains']} 组名={sorted(names)}")
    finally:
        base.rm_all_fakes(qb)


# ================================================================ RM08-11


def test_rm08_11_negative_empty_and_no_glue():
    """[RM08-11] 负向对照(L3): 空场 sites/groups 双空数组 + 已配置域不粘合两缺失域

    前置: 副实例在线空库。腿① trackers 配 ["127.0.0"](双向包含匹配覆盖全部 127.0.0.x announce
      域) + RM08-10 同款场景; 腿② trackers 配 X=127.0.1.5, 场景种A=[X,127.0.0.21]
      种B=[X,127.0.0.22](P/Q 缺失且从不同现)。
    副作用: 副实例两腿各加 3/2 枚 real-fake 假种子(全程 paused); 两份产品进程先后起停;
      只读 GET。
    回滚: 各腿删自造种子(连数据) + 产品进程 taskkill /F /T + 临时目录清场。
    失败判据: 空场 sites/groups 出现 null/缺键/非 list(向后兼容破) / 空场计数失真 /
      腿② 出现同时含 P 与 Q 的组(已配置域参与粘合, D1 语义破) / 任一红验故意错位断言不红。
    """
    # 腿① 空场: 配置已覆盖全部 announce 域名
    _d1, qb1, _seeds1 = build_scene("rm08_11a", SCENE_MERGE)
    try:
        with product_case_grp("rm08_11a", tracker_entry_block("rm08_cover", "127.0.0")) as (
            case, port, _proc
        ):
            sm = base.web_req(port, "GET", "/api/sites/missing")
            assert isinstance(sm["sites"], list) and sm["sites"] == [], \
                f"空场 sites 应为空数组(不是 null/缺键): {sm['sites']!r}"
            assert isinstance(sm["groups"], list) and sm["groups"] == [], \
                f"空场 groups 应为空数组(不是 null/缺键): {sm.get('groups')!r}"
            assert sm["torrents"] == 3 and sm["domains"] == 4, \
                f"空场计数失真: torrents={sm['torrents']} domains={sm['domains']}"
            must_be_red(lambda: _wrong_expect_site(sm, H_A), "空场(设计域应在 sites)")
            base.metric("RM08-11① 空场 sites=[] groups=[] torrents=3 domains=4")
    finally:
        base.rm_all_fakes(qb1)

    # 腿② 不粘合: X 已配置, P/Q 缺失且从不同现(D1 拍板语义的真机验证)
    P, Q, X = "127.0.0.21", "127.0.0.22", "127.0.1.5"
    _d2, qb2, _seeds2 = build_scene("rm08_11b", [
        ("rm08grp-pa.bin", [X, P]),
        ("rm08grp-pb.bin", [X, Q]),
    ])
    try:
        with product_case_grp("rm08_11b", tracker_entry_block("rm08_glue", X)) as (
            case, port, _proc
        ):
            sm = base.web_req(port, "GET", "/api/sites/missing")
            assert sm["torrents"] == 2 and sm["domains"] == 3, \
                f"腿②计数漂移: torrents={sm['torrents']} domains={sm['domains']}"
            assert {s["domain"] for s in sm["sites"]} == {P, Q}, \
                f"缺失面应恰 P/Q(X 已配置不进 sites): {sm['sites']}"
            groups = sm["groups"]
            assert sorted(g["domains"] for g in groups) == [[P], [Q]], \
                f"P/Q 应各自成组: {sorted(g['domains'] for g in groups)}"
            glued = [g for g in groups if {P, Q} <= set(g["domains"])]
            assert not glued, f"红验命中: 已配置域 X 把 P/Q 粘合了: {glued} —— D1 语义破"
            must_be_red(lambda: _wrong_expect_glued(groups, P, Q), "不粘合(P/Q 应同组)")
            base.metric(f"RM08-11② 不粘合 groups={sorted(g['domains'] for g in groups)}")
    finally:
        base.rm_all_fakes(qb2)


# ================================================================ RM08-12


def test_rm08_12_adaptive_gate_premise():
    """[RM08-12] 三分支自适应引导数据面前提: 全单组/多组两形态在端点载荷上可判

    前置: 副实例在线空库; dev.webui 产品连副实例(trackers 配 rm08grp.invalid);
      2 枚 paused 假种子 S1=[127.0.0.31] S2=[127.0.0.32](全单组形态)。
    副作用: 副实例加 2 枚 real-fake 假种子(全程 paused); S1 经 /torrents/addTrackers 追加
      127.0.0.32 变共现场(真写 qB 种子 tracker 表, 收尾随种子删除); 只读 GET 两次;
      两形态各起一份产品进程(实测: 产品 store 对 tracker 列表惰性缓存且只在产品自身
      tracker 写操作时失效 —— record.py:269-276 / qbapi.py:261-268, 绕产品直改 qB 对
      在跑进程不可见, 故形态二必须起新进程拿新 store, 见切片 §03 事实回写)。
    回滚: 删自造种子(连数据) + 产品进程 taskkill /F /T + 临时目录清场。
    失败判据: 全单组退化失守(组数 != sites 数 / 逐组与逐 site 一一对应破 / 组名未顺延) /
      共现后无 ≥2 域名组 / 两形态的「存在 ≥2 域名组」闸门在载荷上不可区分(数据前提破,
      前端需第二次请求才能判定)。三钮框观感与交互本身归用户 L0 目视(挂账, 本条只断数据前提)。
    """
    S1, S2 = "127.0.0.31", "127.0.0.32"
    d, qb, seeds = build_scene("rm08_12", [("rm08grp-s1.bin", [S1]), ("rm08grp-s2.bin", [S2])])
    try:
        # 形态一: 全单组
        with product_case_grp("rm08_12a", tracker_entry_block(CONFIGURED_KEY, CONFIGURED_DOMAIN)) as (
            case, port, _proc
        ):
            sm1 = base.web_req(port, "GET", "/api/sites/missing")
            groups1 = sm1["groups"]
            sites1 = {s["domain"]: s for s in sm1["sites"]}
            assert set(sites1) == {S1, S2} and sm1["torrents"] == 2 and sm1["domains"] == 2, \
                f"形态一场漂移: {sm1.get('torrents')}/{sm1.get('domains')}/{sorted(sites1)}"
            assert len(groups1) == 2 and all(len(g["domains"]) == 1 for g in groups1), \
                f"应全单组: {groups1}"
            assert len(groups1) == len(sm1["sites"]), "全单组退化: 组数应等于 sites 数"
            by_dom1 = {g["domains"][0]: g for g in groups1}
            for dom, s in sites1.items():
                g = by_dom1[dom]
                assert g["entry"] == s["entry"], \
                    f"全单组退化: 组 entry 应与 site entry 一一对应: {dom}"
                assert g["name"] == s["name"] + "_1", \
                    f"组名应沿同一 taken 序列顺延(_1 后缀): {g['name']} vs {s['name']}"
            assert any(len(g["domains"]) >= 2 for g in groups1) is False, "形态一闸门应判假"
            base.metric("RM08-12 全单组 groups=2 单元素闸门=False 名顺延=ok")

        # 形态二: S1 追加 S2 的域 → 共现 → 2 域名组; 新起一份产品进程(旧进程 store 的
        # tracker 惰性缓存对绕产品的 qB 直改不可见, 见 docstring 副作用注)
        add_trackers(qb, seeds["rm08grp-s1.bin"], [f"http://{S2}:1/announce"])
        base.wait_until(
            lambda: {S1, S2} <= extract_tracker_hostnames(qb.trackers(seeds["rm08grp-s1.bin"])),
            15,
            "S1 追加域未在 tracker 视图出现",
        )
        with product_case_grp("rm08_12b", tracker_entry_block(CONFIGURED_KEY, CONFIGURED_DOMAIN)) as (
            case, port, _proc
        ):
            sm2 = base.web_req(port, "GET", "/api/sites/missing")
            groups2 = sm2["groups"]
            fat = [g for g in groups2 if len(g["domains"]) >= 2]
            assert len(fat) == 1 and sorted(fat[0]["domains"]) == [S1, S2], \
                f"共现后应恰一组 2 域名: {groups2}"
            assert any(len(g["domains"]) >= 2 for g in groups2) is True, "形态二闸门应判真"
            assert {s["domain"] for s in sm2["sites"]} == {S1, S2}, "sites 原形应在共现后保持"
            base.metric(f"RM08-12 共现组={fat[0]['domains']} 闸门=True")
    finally:
        base.rm_all_fakes(qb)
