"""RM10 附加轮(导出面): 缺失站点导出/导入 tracker 合并 —— CLI --export-yaml 真机 4 条。

验证面对准计划 plans/26-11-04-0115-plan-real-rm10-addendum-missing-merge.html §04 与功能计划
plans/26-11-03-2337-plan-missing-site-tracker-merge.html §03/§04(M1/M2 已入库):
only_missing 合并正向 + dry-run 零写(RM10-11)· 追加模式合并(RM10-12)·
--split-trackers 配合校验红验 + split/合并键面对照(RM10-13, L3)· 双跑幂等(RM10-14)。

造法(计划 §03.3): 副实例(空库草稿本, bypass_local_auth 空凭据直连 —— 导出配置零 token 落盘)
造 3 枚 L1 假种子(lib/torrent.build_stream + add_torrent paused + real-fake 标签, RM05 同款
409 删旧重加), 逐枚 POST /torrents/addTrackers 追加设计 announce。共现设计:
A=[127.0.0.7, 127.0.0.12] / B=[127.0.0.12, 127.0.0.13] / C=[127.0.0.14]
⇒ 期望合并组 {127.0.0.7, 127.0.0.12, 127.0.0.13}(跨种子传递闭包, 代表=最短 127.0.0.7)
+ 单元素组 {127.0.0.14}。
announce 全部 127.x IP 字面量 + 死端口 :1: _hosts_of 取 urlparse().hostname 不含端口
(同 IP 异端口会塌缩成一个域名, 故用互异 IP), 零 DNS、零外连; 种子全程 paused 不 announce。

断言面按设计域定界(scoped): 设计域每个域名恰出现在一个条目, 实例里他方种子残链不进断言集。
IP 形态 gen_default_tag 返回空标签是已知正确行为(exporter.py:72 isdigit 分支), tags 断言按此写。

跑法: `commands run real.run -- --case RM10-11 --yes` 单跑; 整片 `real.suite -- --slice RM10 --yes`
(会连同 RM10 既有 5 条一起跑; 只跑本文件可 `uv run pytest tests-real/rm10_notify/test_rm10_export_merge.py -q --no-cov`)。
收尾: real.seed.rm --all + real.seed.clean 清自造种子与 .work 残留。
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Callable

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import app, instances, torrent  # noqa: E402
from auto_qb.infra.utils import extract_tracker_hostnames  # noqa: E402
from auto_qb.infra.versioning import CURRENT_VERSIONS  # noqa: E402

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm10"
TAG = "real-fake"
SETTLED = {
    "stalledUP",
    "stalledDL",
    "pausedUP",
    "pausedDL",
    "stoppedUP",
    "stoppedDL",
    "missingFiles",
    "error",
    "moving",
}

# 设计 announce 域(互异 127.x IP 字面量, 死端口 :1; 见模块 docstring)
H_A, H_B, H_C, H_D = "127.0.0.7", "127.0.0.12", "127.0.0.13", "127.0.0.14"
DESIGNED = {H_A, H_B, H_C, H_D}
MERGED_GROUP = sorted({H_A, H_B, H_C})  # 传递闭包: A∩B 共现
MERGED_NAME = H_A.replace(".", "_")  # 代表=组内最短(9 < 10), 键=非法字符换下划线
SINGLE_GROUP = [H_D]
SINGLE_NAME = H_D.replace(".", "_")
SPLIT_NAMES = sorted(d.replace(".", "_") for d in DESIGNED)
CONFIGURED_DOMAIN = "rm10em.invalid"  # 测试配置已配域: 与全部 announce 域零命中(保缺失面成立)
CONFIGURED_NAME = "rm10em_invalid"
SPLIT_ERR_TEXT = "--split-trackers 需配合 --export-yaml 使用"


def metric(line: str) -> None:
    """实测数字落盘(<.work>/rm10/metrics.log): 基线切片从这里誊写。"""
    WORK.mkdir(parents=True, exist_ok=True)
    with open(WORK / "metrics.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {line}\n")


def _is_link(p) -> bool:
    import stat

    try:
        st = p.lstat()
    except OSError:
        return False
    tag = getattr(st, "st_reparse_tag", 0)
    return bool(tag) or stat.S_ISLNK(st.st_mode)


def purge_tree(root) -> None:
    """删目录树, 绝不递归删穿链接(RM04 §08 红线同款)。"""
    root = Path(root)
    if _is_link(root):
        os.rmdir(root)
        return
    if not root.exists():
        return
    for dirpath, dirnames, _files in os.walk(root, topdown=True):
        for d in list(dirnames):
            full = Path(dirpath) / d
            if _is_link(full):
                os.rmdir(full)
                dirnames.remove(d)
    shutil.rmtree(root, ignore_errors=True)


def case_dir(name: str) -> Path:
    purge_tree(WORK / name)
    d = WORK / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _tags_of(t) -> set[str]:
    """qB 多标签「, 」连接的 strip 防御(§2.9 / 26-10-31-1215)。"""
    return {x.strip() for x in (t.get("tags") or "").split(",") if x.strip()}


def rm_all_fakes(qb) -> list[str]:
    """删光本实例全部 real-fake 自造种子(连数据), 返回删掉的名字。"""
    gone = []
    for t in qb.torrents():
        if TAG in _tags_of(t):
            qb.delete(t["hash"], delete_files=True)
            gone.append(t["name"])
    if gone:
        wait_until(lambda: not [t for t in qb.torrents() if TAG in _tags_of(t)], 15, f"real-fake 清理未生效: {gone}")
    return gone


def wait_until(fn, timeout: float, desc: str | Callable[[], str], interval: float = 0.4):
    """轮询到 fn() 为真值并返回它; 超时抛 AssertionError 带最后一次观测。

    desc 支持 str 或惰性 callable(超时构造报错时才求值): 调用点拼带「最后观测值」的
    f-string desc 必须传 lambda —— str 在调用期求值, 超时报错里显示的是等待前的旧值
    而非超时时刻实况(issue 26-11-08-0044, RM07-11 首版踩过)。
    """
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(interval)
    raise AssertionError(f"等待超时({timeout}s): {desc() if callable(desc) else desc}; 最后观测: {last}")


def settle(qb, ih: str, timeout: float = 30.0) -> dict:
    """等种子走完加种流程拿到稳定态(paused 加种只查 resume data, 应立即 stopped*)。"""
    deadline = time.time() + timeout
    t: dict = {}
    while time.time() < deadline:
        t = qb.torrent(ih) or {}
        if t.get("state") in SETTLED:
            return t
        time.sleep(0.3)
    return t


def _add_retry(qb, raw: bytes, savepath: str, ih: str) -> None:
    """加种子, 409 双义处理(§2.9: 同 infohash 一律删旧重加, 绝不收养)。"""
    from lib.qb import QbError

    for attempt in range(4):
        try:
            qb.add_torrent(raw, savepath=savepath, tags=TAG, infohash_hint=ih)
            return
        except QbError as e:
            if "409" not in str(e):
                raise
            stale = qb.torrent(ih)
            if stale is None:
                time.sleep(1.5)
                continue
            qb.delete(stale["hash"], delete_files=True)
            wait_until(lambda: qb.torrent(ih) is None, 15, f"409 旧副本删除未生效: {ih[:8]}")
    raise AssertionError(f"add 持续 409: {ih[:8]} @ {savepath}")


def add_trackers(qb, ih: str, urls: list[str]) -> None:
    """给已加种子追加 announce(qB 原生 /torrents/addTrackers; 参数名是 hash 单数, urls 换行分隔)。"""
    body = urllib.parse.urlencode({"hash": ih, "urls": "\n".join(urls)}).encode()
    qb._call("/torrents/addTrackers", body, "application/x-www-form-urlencoded")


# 共现设计: A=[7,12] B=[12,13] C=[14]
SEED_SPECS = [
    ("rm10em-a.bin", H_A, [H_B]),
    ("rm10em-b.bin", H_B, [H_C]),
    ("rm10em-c.bin", H_D, []),
]


def build_scene(case_name: str) -> tuple[Path, object, dict, Path]:
    """建用例场景: 3 枚 paused 假种子 + 设计 announce + 校验 tracker 视图可见。

    返回 (case 目录, qb, {种子名: infohash}, savepath)。
    """
    d = case_dir(case_name)
    qb = instances.make(instances.SECONDARY)
    rm_all_fakes(qb)  # 开跑先清场(含上轮半途失败的残留; 各片自清是幂等口径)
    savepath = d / "seeds"
    savepath.mkdir(parents=True, exist_ok=True)
    seeds: dict = {}
    try:
        for name, host, extra_hosts in SEED_SPECS:
            urls = [f"http://{host}:1/announce"] + [f"http://{h}:1/announce" for h in extra_hosts]
            raw, ih = torrent.build_stream(name, 256 * 1024, "random", f"rm10em-{name}", urls[0])
            _add_retry(qb, raw, str(savepath), ih)
            settle(qb, ih)
            if len(urls) > 1:
                add_trackers(qb, ih, urls[1:])
            seeds[name] = ih
        for tname, host, extra_hosts in SEED_SPECS:
            ih = seeds[tname]
            want = {host, *extra_hosts}
            wait_until(
                lambda: want <= extract_tracker_hostnames(qb.trackers(ih)),
                15,
                f"{tname} 的 announce 未在 tracker 视图出现: want={sorted(want)}",
            )
    except BaseException:
        rm_all_fakes(qb)  # 造场半途失败也自清, 不留残留
        raise
    return d, qb, seeds, savepath


EXPORT_CONFIG_TEMPLATE = """\
config:
    schema_version: 8
    qbittorrent:
        host: 127.0.0.1
        port: {secondary_port}
        username: ""
        password: ""
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
        enabled: false
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
    trackers:
        {configured_name}:
            domains:
                - {configured_domain}
            tags:
                - Rm10Em
            upload_speed_limit: 0KiB/s
            download_speed_limit: 0KiB/s
            hr:
                required_seeding_time: 3D
                required_share_ratio: 0
                extra_seeding_time: 12H
                condition: 80%
    notify:
        enabled: false
"""


def write_export_cfg(case: Path) -> Path:
    """生成 tests-real 派生导出配置: 指**副实例**空凭据(bypass_local_auth, 规程 §2.5.2)。

    token 零落盘 —— 任何 api_key/凭据不写进配置文件(D2 拍板: 主实例路径必须写 api_key, 故弃用)。
    """
    cfg = case / "config.yml"
    cfg.write_text(
        EXPORT_CONFIG_TEMPLATE.format(
            secondary_port=instances.SECONDARY,
            data_dir=(case / "data").as_posix(),
            web_port=app.free_port(),
            configured_name=CONFIGURED_NAME,
            configured_domain=CONFIGURED_DOMAIN,
        ),
        encoding="utf-8",
    )
    text = cfg.read_text(encoding="utf-8")
    assert f"port: {instances.SECONDARY}" in text, "配置没指向副实例(空凭据草稿本)"
    assert f"port: {instances.PRIMARY}" not in text, "配置指向了主实例(需要 token 落盘), 拒跑"
    assert "api_key" not in text, "配置混入 api_key —— token 落盘红线"
    assert CONFIGURED_DOMAIN in text
    return cfg


def entry_domains(data: dict) -> dict:
    return {k: list((e or {}).get("domains") or []) for k, e in data["config"]["trackers"].items()}


def find_entry(data: dict, domains: list) -> str:
    """按 domains 精确找条目键; 恰一条, 否则响亮失败。"""
    matches = [k for k, d in entry_domains(data).items() if d == domains]
    assert len(matches) == 1, f"domains={domains} 应恰一条目, 实际 {matches}; 全部条目: {entry_domains(data)}"
    return matches[0]


def assert_designed_domains_scoped(data: dict) -> None:
    """设计域定界断言: 每个设计域恰出现在一个条目(他方残链不进断言集)。"""
    seen: dict = {}
    for k, d in entry_domains(data).items():
        for dom in d:
            if dom in DESIGNED:
                seen.setdefault(dom, []).append(k)
    assert set(seen) == DESIGNED, f"设计域缺失: {sorted(DESIGNED - set(seen))}; 观测: {seen}"
    dup = {dom: ks for dom, ks in seen.items() if len(ks) > 1}
    assert not dup, f"设计域出现在多个条目: {dup}"


def assert_merged_entry_shape(data: dict) -> None:
    """合并条目形态单点: 键/域名序/空标签/示例字段(计划 §04 期望值)。"""
    key = find_entry(data, MERGED_GROUP)
    assert key == MERGED_NAME, f"合并条目键应为代表域名派生名 {MERGED_NAME!r}, 实际 {key!r}"
    entry = data["config"]["trackers"][key]
    assert entry["domains"] == MERGED_GROUP, f"合并条目 domains 应为整组 sorted {MERGED_GROUP}, 实际 {entry['domains']}"
    assert entry["tags"] == [""], f"IP 形态默认标签应为空串(已知正确行为), 实际 {entry['tags']!r}"
    assert entry["upload_speed_limit"] == "0KiB/s" and entry["download_speed_limit"] == "0KiB/s", \
        f"限速占位应为 UNLIMITED_SPEED, 实际 {entry}"
    hr = entry["hr"]
    assert hr["required_seeding_time"] == "3D" and hr["required_share_ratio"] == 0 \
        and hr["extra_seeding_time"] == "12H" and hr["condition"] == "80%", f"hr 示例段漂移: {hr}"


def assert_single_entry_shape(data: dict) -> None:
    key = find_entry(data, SINGLE_GROUP)
    assert key == SINGLE_NAME, f"单元素条目键应 {SINGLE_NAME!r}, 实际 {key!r}"
    assert data["config"]["trackers"][key]["tags"] == [""]


def cleanup_scene(qb, case: Path) -> None:
    try:
        rm_all_fakes(qb)
    finally:
        purge_tree(case)


# ================================================================ RM10-11


def test_rm10_11_only_missing_merge_positive():
    """[RM10-11] only_missing 合并正向 + dry-run 零写: 共现域名并组, 代表=最短域名派生键

    前置: 副实例(56590)在线且空库(除本轮自造); 3 枚 paused 假种子按 SEED_SPECS 共现设计;
      tests-real 派生导出配置(已配域 rm10em.invalid 与 announce 零命中)。
    副作用: 副实例加 3 枚 real-fake 假种子(全程 paused); 写 .work/rm10/rm10_11/ 下落盘 YAML;
      dry-run 轮零写盘。
    回滚: 删自造种子(连数据) + purge case 目录。
    失败判据: dry-run 轮输出文件出现(写侧失守) / 合并组未成立(3 元素条目缺失或拆散) /
      代表键不是最短域名派生名 / 单元素组未单独成条 / 设计域跨条目重复 / 骨架混入已配域或多余段 /
      IP 形态标签非空串(行为漂移)。
    """
    d, qb, seeds, _savepath = build_scene("rm10_11")
    cfg = write_export_cfg(d)
    out_dry = d / "export-dry.yml"
    out = d / "export-missing.yml"
    try:
        # 1. dry-run: 日志照打「已导出」但输出文件必须不存在(§2.9 同款零写判据)
        r = app.run_cli([str(cfg), "--export-yaml", str(out_dry), "--only-missing", "--dry-run"], timeout=120)
        assert r.returncode == 0, f"dry-run 导出非 0: rc={r.returncode}\nstdout={r.stdout[-600:]}\nstderr={r.stderr[-600:]}"
        assert "已导出" in (r.stdout + r.stderr), "dry-run 轮缺「已导出」日志"
        assert not out_dry.exists(), "dry_run 轮输出文件出现 —— 写侧失守"

        # 2. only_missing 正向
        r = app.run_cli([str(cfg), "--export-yaml", str(out), "--only-missing"], timeout=120)
        assert r.returncode == 0, f"only_missing 导出非 0: rc={r.returncode}\nstdout={r.stdout[-600:]}\nstderr={r.stderr[-600:]}"
        data = yaml.safe_load(out.read_text(encoding="utf-8"))

        # 3. 骨架形状: 只含 trackers + schema_version, 已配域不出现
        assert set(data) == {"config"}, f"顶层多余段: {set(data)}"
        assert set(data["config"]) == {
            "trackers", "schema_version"
        }, f"骨架应只含 trackers+schema_version, 实际 {set(data['config'])}"
        assert data["config"]["schema_version"] == CURRENT_VERSIONS["config"]
        assert CONFIGURED_DOMAIN not in {x for d in entry_domains(data).values() for x in d}, "骨架混入已配域"

        # 4. 合并组 + 单元素组 + 设计域定界
        assert_merged_entry_shape(data)
        assert_single_entry_shape(data)
        assert_designed_domains_scoped(data)

        names = list(data["config"]["trackers"])
        assert len(names) == len(set(names)), "tracker 名冲突"
        assert all(re.fullmatch(r"[A-Za-z0-9_]+", n) for n in names), f"tracker 名含非法字符: {names}"
        metric(f"RM10-11 合并组={MERGED_GROUP} 单元素={SINGLE_GROUP} 条目数={len(names)} dry零写=ok")
    finally:
        cleanup_scene(qb, d)


# ================================================================ RM10-12


def test_rm10_12_append_mode_merge():
    """[RM10-12] 追加模式合并: 既有配置条目原样保留 + 缺失合并条目追加

    前置: 同 RM10-11(同一共现设计, 独立造场)。
    副作用: 同 RM10-11; 追加模式不落 --only-missing 骨架而是整配置回显。
    回滚: 删自造种子(连数据) + purge case 目录。
    失败判据: 既有条目丢失/被改写 / 缺失合并条目未追加 / 导出缺原始配置段 /
      设计域跨条目重复 / schema_version 不是当前版本。
    """
    d, qb, seeds, _savepath = build_scene("rm10_12")
    cfg = write_export_cfg(d)
    out = d / "export-append.yml"
    try:
        r = app.run_cli([str(cfg), "--export-yaml", str(out)], timeout=120)
        assert r.returncode == 0, f"追加导出非 0: rc={r.returncode}\nstdout={r.stdout[-600:]}\nstderr={r.stderr[-600:]}"
        data = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert data["config"]["schema_version"] == CURRENT_VERSIONS["config"]

        # 既有条目原样保留(domains/tags 逐字) + 整配置回显(data_dir 等原始段在场)
        trackers = data["config"]["trackers"]
        assert CONFIGURED_NAME in trackers, f"既有配置条目丢失: {list(trackers)}"
        kept = trackers[CONFIGURED_NAME]
        assert kept["domains"] == [CONFIGURED_DOMAIN], f"既有条目 domains 被改写: {kept['domains']}"
        assert kept["tags"] == ["Rm10Em"], f"既有条目 tags 被改写: {kept['tags']!r}"
        assert "data_dir" in data["config"], "追加模式缺原始配置段(data_dir)"

        assert_merged_entry_shape(data)
        assert_single_entry_shape(data)
        assert_designed_domains_scoped(data)
        metric("RM10-12 追加模式 既有保留=ok 合并追加=ok")
    finally:
        cleanup_scene(qb, d)


# ================================================================ RM10-13


def test_rm10_13_split_trackers_red():
    """[RM10-13] --split-trackers 配合校验红验(L3) + split/合并产物键面对照

    前置: 同 RM10-11 场景; 腿 1 零 qB 依赖(argparse 层)。
    副作用: 同 RM10-11(两轮落盘: 合并一轮 + split 一轮)。
    回滚: 删自造种子(连数据) + purge case 目录。
    失败判据: 腿 1 缺 --export-yaml 时 rc==0 或报错文案缺失(配合校验失守, 红验不红即产品缺陷) /
      腿 2 split 产物出现 ≥2 元素条目(回归成合并) / 某设计域无专属条目(拆分漏域) /
      对照腿合并产物无 3 元素条目 / 故意错位的红验断言不红。
    """
    d, qb, seeds, _savepath = build_scene("rm10_13")
    cfg = write_export_cfg(d)
    out_m = d / "export-merged.yml"
    out_s = d / "export-split.yml"
    try:
        # 1. 红验: 缺 --export-yaml → argparse 非 0 + parser.error 文案
        r = app.run_cli([str(cfg), "--split-trackers"], timeout=60)
        assert r.returncode != 0, f"缺 --export-yaml 却 rc=0 —— 配合校验失守\nstdout={r.stdout[-400:]}"
        combined = r.stdout + r.stderr
        assert SPLIT_ERR_TEXT in combined, f"报错文案缺失: 期望含 {SPLIT_ERR_TEXT!r}\n{combined[-500:]}"

        # 2. 同批种子: 合并产物 vs split 产物键面对照
        r = app.run_cli([str(cfg), "--export-yaml", str(out_m), "--only-missing"], timeout=120)
        assert r.returncode == 0, f"合并导出非 0: {r.stderr[-500:]}"
        merged = yaml.safe_load(out_m.read_text(encoding="utf-8"))
        r = app.run_cli([str(cfg), "--export-yaml", str(out_s), "--only-missing", "--split-trackers"], timeout=120)
        assert r.returncode == 0, f"split 导出非 0: {r.stderr[-500:]}"
        split = yaml.safe_load(out_s.read_text(encoding="utf-8"))

        # split 面: 逐域名条目, 键集恰为 4 个设计域派生名, 无任何 ≥2 设计域条目
        assert set(entry_domains(split)) == set(SPLIT_NAMES), \
            f"split 键集漂移: {sorted(entry_domains(split))} != {SPLIT_NAMES}"
        for dom in DESIGNED:
            find_entry(split, [dom])
        fat = {k: d for k, d in entry_domains(split).items() if len([x for x in d if x in DESIGNED]) >= 2}
        assert not fat, f"红验命中: split 产物出现合并条目 {fat} —— 拆分语义失守"

        # 对照面: 同批种子合并产物含 3 元素组; 127.0.0.12 在合并面无专属条目、在 split 面有
        assert find_entry(merged, MERGED_GROUP)
        assert not [k for k, dd in entry_domains(merged).items() if dd == [H_B]], \
            "合并面不应有 127.0.0.12 专属条目"
        assert_designed_domains_scoped(merged)

        # 红验(对照断言效力自证): 故意错位的期望必须红
        try:
            find_entry(split, ["bogus.rm10em.invalid"])
        except AssertionError:
            pass
        else:
            raise AssertionError("红验失败: split 产物找不存在域的断言没有红")
        metric("RM10-13 配合校验红=ok split逐域名=4 对照=ok")
    finally:
        cleanup_scene(qb, d)


# ================================================================ RM10-14


def test_rm10_14_double_run_idempotent():
    """[RM10-14] 双跑幂等: 同参数连跑两次输出逐字节一致(§2.7/§2.9 幂等口径)

    前置: 同 RM10-11 场景(独立造场)。
    副作用: 同 RM10-11(两模式各双跑一轮)。
    回滚: 删自造种子(连数据) + purge case 目录。
    失败判据: 任一模式双跑字节漂移(tracker 名/序/内容不稳定)。
    """
    d, qb, seeds, _savepath = build_scene("rm10_14")
    cfg = write_export_cfg(d)
    try:
        for label, extra, out_name in (
            ("only_missing", ["--only-missing"], "export-idem-om.yml"),
            ("append", [], "export-idem-ap.yml"),
        ):
            out = d / out_name
            r1 = app.run_cli([str(cfg), "--export-yaml", str(out), *extra], timeout=120)
            assert r1.returncode == 0, f"{label} 第一跑非 0: {r1.stderr[-500:]}"
            first = out.read_bytes()
            r2 = app.run_cli([str(cfg), "--export-yaml", str(out), *extra], timeout=120)
            assert r2.returncode == 0, f"{label} 第二跑非 0: {r2.stderr[-500:]}"
            assert out.read_bytes() == first, f"{label} 双跑输出字节漂移(tracker 名/序不稳定)"
        metric("RM10-14 双跑字节一致 only_missing=ok append=ok")
    finally:
        cleanup_scene(qb, d)
