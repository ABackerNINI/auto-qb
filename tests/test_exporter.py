"""test_exporter 测试计划: exporter 域名收集/缺失筛选/默认标签/模板导出

## 测试计划(每个测试函数一条)
- test_collect_configured_domains: 收集已配置域名
- test_collect_all_tracker_hostnames: 收集全部 tracker hostname
- test_collect_all_tracker_hostnames_skips_errors: 收集出错跳过
- test_collect_all_tracker_hostnames_skip_empty_url: 空 URL 跳过
- test_collect_torrent_tracker_hostnames: 逐种子收集, 每颗种子一个集合
- test_collect_torrent_tracker_hostnames_error_isolated: 单种查询异常该种子空集, 不终止
- test_collect_torrent_tracker_hostnames_call_shape: qB 调用面 = 一次 torrents_info + 逐种 torrents_trackers
- test_find_missing_domains: 找出缺失域名
- test_group_missing_domains_cooccurrence: 共现合并(两缺失域名同现于一种子即一组)
- test_group_missing_domains_transitive: 跨种子传递闭包(A+B 同现种1, B+C 同现种2 -> 一组)
- test_group_missing_domains_no_cooccurrence_singletons: 不共现的缺失域名各自成组(全单元素组)
- test_group_missing_domains_configured_never_glues: 已配置域名不进任何组, 也不粘合缺失域名
- test_capitalize_special_tag: 特殊标签大写化
- test_gen_default_tag: 生成默认标签
- test_build_tracker_entry: 构建 tracker 条目
- test_build_merged_entry: 合并条目(返回 (name, entry) 二元组, 代表=最短/tie 字典序, domains 整组 sorted, 名字进 taken, 字段同源)
- test_build_merged_entry_singleton_degenerates: 单元素组退化 = 逐域名 build_tracker_entry(名字由该域名生成)
- test_gen_tracker_name: 域名转合法站点名(非法字符替换/既有占用与批内冲突加 _N 后缀)
- test_export_yaml_template_append: 模板导出追加
- test_export_yaml_template_only_missing_dry_run: 仅缺失 dry-run 导出
- test_export_yaml_template_stamps_schema_version: 导出模板统一带当前 schema 版本章
- test_export_yaml_template_name_collision: 名称冲突处理
- test_export_yaml_template_merged_default_only_missing: 默认合并(仅缺失)—— 共现缺失域名一条合并条目(键=最短域名名字)
- test_export_yaml_template_merged_default_append: 默认合并(追加)—— 现有配置保留 + 共现缺失域名合并条目
- test_export_yaml_template_split_trackers: split_trackers=True 拆回逐域名路径
- test_export_yaml_template_split_trackers_append: split_trackers=True + 追加模式(only_missing=False), 保留既有条目并逐域名各一条
- test_export_yaml_template_all_singleton_groups_equivalent: 全单元素缺失组时合并路径与 split 路径产物等价
- test_collect_all_tracker_hostnames_per_hash_union_and_error_isolation: 守阵(W6 变异审计)—— 逐种取 tracker 按 hash,
  单种异常跳过不终止扫描, 多种域名并集
- test_find_missing_domains_substring_both_directions: 守阵(W6)—— 缺失筛选包含匹配双向成立
- test_capitalize_special_tag_bare_hd_pt: 守阵(W6)—— 裸 hd/pt(无后随字母)大写化不产生垃圾后缀
- test_gen_tracker_name_uppercase_and_multi_conflict: 守阵(W6)—— 大写域名清洗 + 双重冲突后缀序列 _2
- test_build_tracker_entry_template_contract: 守阵(W6)—— 导出模板条目 schema 键名与示例值逐字契约
- test_export_yaml_template_default_append_mode: 守阵(W6)—— only_missing 缺省为追加模式(唯一调用方显式传参面)
- test_export_yaml_template_scan_audit_logs: 守阵(W6)—— 扫描/发现/导出 INFO 审计日志丢真即红
- test_export_yaml_template_only_missing_output_keys: 守阵(W6)—— only_missing 产物 config 键面与回写 trackers 键名
- test_export_yaml_template_missing_trackers_section: 守阵(W6)—— 配置无 trackers 段走缺省 {}(不崩)
- test_export_yaml_template_pins_utf8_encoding: 守阵(W6, 平台相关)—— 读 config/写 output 显式钉 encoding="utf-8"
  (参数面用 open 探针全平台可观测; Windows locale 内容面 mojibake 仅作加强, WSL UTF-8 locale 下不敏感)
- test_collect_torrent_tracker_hostnames_prefers_fresh_bypass: 扫描优先走 fresh 直查(不吃记录级缓存)
- test_collect_torrent_tracker_hostnames_fresh_bypass_facade_cache: 红验(issue 26-11-04-0228)——
  facade 记录级缓存吃 qB 侧旧值时, 扫描仍读到改后新值
"""
import os
import tempfile

import yaml

from auto_qb.core import exporter
from auto_qb.config import TrackerConfig
from helpers import FakeClient, FakeConfig, FakeTorrent


def _make_config_with_trackers(*trackers):
    cfg = FakeConfig()
    cfg.trackers = {t.name: t for t in trackers}
    return cfg


def _tracker(name, domains, tags=None):
    return TrackerConfig(
        name=name,
        domains=domains,
        tags=tags or [name],
        remove_tags=[],
        upload_speed_limit=None,
        download_speed_limit=None,
        hr=None,
        rules=[],
        remove_similar_tags=False,
    )


def test_collect_configured_domains():
    """收集配置中所有 tracker 域名"""
    cfg = _make_config_with_trackers(
        _tracker("HHan", ["tracker.hhanclub.net"]),
        _tracker("Kufirc", ["kufirc.com", "www.kufirc.com"]),
    )
    assert exporter.collect_configured_domains(cfg) == {"tracker.hhanclub.net", "kufirc.com", "www.kufirc.com"}


def test_collect_all_tracker_hostnames():
    """从所有种子收集去重 tracker hostname"""
    client = FakeClient()
    t1 = FakeTorrent(hash="H1", name="T1")
    t2 = FakeTorrent(hash="H2", name="T2")
    client.torrents["H1"] = t1
    client.torrents["H2"] = t2
    hosts = exporter.collect_all_tracker_hostnames(client)
    assert hosts == {"tracker.hhanclub.net"}


def test_collect_all_tracker_hostnames_skips_errors():
    """单个种子 tracker 查询异常时跳过, 不影响其它种子"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")
    client.torrents_trackers = lambda h: (_ for _ in ()).throw(RuntimeError("boom"))
    assert exporter.collect_all_tracker_hostnames(client) == set()


def test_collect_all_tracker_hostnames_skip_empty_url():
    """无 url 的 tracker 条目被忽略"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    client.torrents_trackers = lambda h: [{"url": ""}, {"url": None}]
    assert exporter.collect_all_tracker_hostnames(client) == set()


def test_collect_torrent_tracker_hostnames():
    """逐种子收集 tracker hostname, 每颗种子一个集合(集合间不合并)"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")
    client.trackers_map = {
        "H1": [{
            "url": "https://a.example.com/announce"
        }],
        "H2": [{
            "url": "https://b.example.com/announce"
        }, {
            "url": "https://a.example.com/announce"
        }],
    }
    assert exporter.collect_torrent_tracker_hostnames(client) == [
        {"a.example.com"},
        {"a.example.com", "b.example.com"},
    ]


def test_collect_torrent_tracker_hostnames_error_isolated():
    """单个种子 tracker 查询异常时该种子给空集, 不影响其它种子"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")

    def trackers(h):
        if h == "H1":
            raise RuntimeError("boom")
        return [{"url": "https://b.example.com/announce"}]

    client.torrents_trackers = trackers
    assert exporter.collect_torrent_tracker_hostnames(client) == [set(), {"b.example.com"}]


def test_collect_torrent_tracker_hostnames_call_shape():
    """qB 调用面与现状一致: 一次 torrents_info + 逐种 torrents_trackers(按 hash)"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")
    info_calls = []
    tracker_hashes = []

    def fake_info():
        info_calls.append(1)
        return list(client.torrents.values())

    def fake_trackers(h):
        tracker_hashes.append(h)
        return []

    client.torrents_info = fake_info
    client.torrents_trackers = fake_trackers
    exporter.collect_torrent_tracker_hostnames(client)
    assert len(info_calls) == 1
    assert sorted(tracker_hashes) == ["H1", "H2"]


def test_find_missing_domains():
    """筛选未配置域名(包含关系: configured 在 host 中或 host 在 configured 中)"""
    all_domains = {"tracker.hhanclub.net", "tracker.kufirc.com", "other.site.net"}
    configured = {"tracker.hhanclub.net"}
    assert exporter.find_missing_domains(all_domains, configured) == {"tracker.kufirc.com", "other.site.net"}
    # 无缺失
    assert exporter.find_missing_domains(all_domains, set(all_domains)) == set()


def test_group_missing_domains_cooccurrence():
    """共现合并: 两缺失域名只在一颗种子里同现即合并一组, 其余各自成组"""
    torrent_sets = [{"a.com", "b.com"}, {"c.com"}]
    missing = {"a.com", "b.com", "c.com"}
    assert exporter.group_missing_domains(torrent_sets, missing) == [["a.com", "b.com"], ["c.com"]]


def test_group_missing_domains_transitive():
    """跨种子传递闭包: A+B 同现于种1, B+C 同现于种2 -> A/B/C 一组"""
    torrent_sets = [{"a.com", "b.com"}, {"b.com", "c.com"}]
    missing = {"a.com", "b.com", "c.com"}
    assert exporter.group_missing_domains(torrent_sets, missing) == [["a.com", "b.com", "c.com"]]


def test_group_missing_domains_no_cooccurrence_singletons():
    """不共现的缺失域名各自成组(全单元素组), 组内与组间均 sorted"""
    torrent_sets = [{"c.com"}, {"a.com"}, {"b.com"}]
    missing = {"a.com", "b.com", "c.com"}
    assert exporter.group_missing_domains(torrent_sets, missing) == [["a.com"], ["b.com"], ["c.com"]]


def test_group_missing_domains_configured_never_glues():
    """已配置域名不出现在任何组, 也不粘合两个从未直接同现的缺失域名

    种1含 A+X、种2含 B+X, X 已配置(不在 missing)—— A、B 必须各自成组。
    """
    torrent_sets = [{"a.com", "x.com"}, {"b.com", "x.com"}]
    missing = {"a.com", "b.com"}
    groups = exporter.group_missing_domains(torrent_sets, missing)
    assert groups == [["a.com"], ["b.com"]]
    assert all("x.com" not in group for group in groups)


def test_capitalize_special_tag():
    """hd/pt 及其后字母转为大写"""
    assert exporter.capitalize_special_tag("HdChina") == "HDChina"
    assert exporter.capitalize_special_tag("hdt") == "HDT"
    assert exporter.capitalize_special_tag("pthome") == "PTHome"
    assert exporter.capitalize_special_tag("chdbits") == "cHDBits"  # hd 及后一字母大写


def test_gen_default_tag():
    """默认标签: 倒数第二级域名, 首字母大写并大写 hd/pt; IP/单段返回空"""
    assert exporter.gen_default_tag("tracker.hhanclub.net") == "Hhanclub"
    assert exporter.gen_default_tag("hdchina.org") == "HDChina"
    assert exporter.gen_default_tag("pttime.org") == "PTTime"
    assert exporter.gen_default_tag("1.2.3.4") == ""  # IP 不生成标签
    assert exporter.gen_default_tag("localhost") == ""  # 单段域名


def test_build_tracker_entry():
    """生成 tracker 配置条目(含示例 hr)"""
    entry = exporter.build_tracker_entry("hdchina.org")
    assert entry["domains"] == ["hdchina.org"]
    assert entry["tags"] == ["HDChina"]
    assert entry["hr"]["required_seeding_time"] == "3D"
    assert entry["upload_speed_limit"] == "0KiB/s"


def test_build_merged_entry():
    """合并条目: 返回 (name, entry) 二元组; 代表域名 = 组内最短(tie 取字典序); domains 键 = 整组 sorted; 站点名就地登记进 taken"""
    # 等长 tie: 取字典序 "a.com" 为代表
    taken = set()
    name, entry = exporter.build_merged_entry(["b.com", "a.com"], taken)
    assert name == "a_com"
    assert entry["domains"] == ["a.com", "b.com"]
    assert taken == {"a_com"}, "站点名应由代表域名生成并登记进 taken"
    expected = exporter.build_tracker_entry("a.com")
    expected["domains"] = ["a.com", "b.com"]
    assert entry == expected, "其余字段必须与 build_tracker_entry(代表域名) 同源"

    # 最短优先于字典序: "abc.example" 比 "tracker.abc.example" 短
    name2, entry2 = exporter.build_merged_entry(["tracker.abc.example", "abc.example"], set())
    assert name2 == "abc_example"
    assert entry2["domains"] == ["abc.example", "tracker.abc.example"]
    assert entry2["tags"] == [exporter.gen_default_tag("abc.example")]


def test_build_merged_entry_singleton_degenerates():
    """全单元素组退化: 单域名组合并条目与逐域名 build_tracker_entry 逐字节等价, 名字由该域名生成"""
    name, entry = exporter.build_merged_entry(["hdchina.org"], set())
    assert name == "hdchina_org"
    assert entry == exporter.build_tracker_entry("hdchina.org")


def test_gen_tracker_name():
    """域名转合法站点名: 非法字符替换下划线; 既有占用与批内清洗同名加 _N 后缀并就地登记"""
    taken = {"hdchina_org"}
    assert exporter.gen_tracker_name("hdchina.org", taken) == "hdchina_org_1", "既有占用 -> _1"
    assert exporter.gen_tracker_name("a.b.com", taken) == "a_b_com"
    assert exporter.gen_tracker_name("a-b.com", taken) == "a_b_com_1", "批内清洗同名 -> 递增后缀"
    assert "a_b_com_1" in taken, "新名应登记回 taken"
    assert exporter.gen_tracker_name("kufirc.com", set()) == "kufirc_com"


def test_export_yaml_template_append():
    """追加模式: 缺失站点追加到现有配置后完整导出"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"config": {
                    "trackers": {
                        "HHan": {
                            "domains": ["tracker.hhanclub.net"]
                        }
                    }
                }},
                f,
                allow_unicode=True,
            )
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [{"url": "https://hdchina.org/announce.php"}]
        cfg = _make_config_with_trackers(_tracker("HHan", ["tracker.hhanclub.net"]))

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=False, only_missing=False)
        with open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        # 原配置保留 + 缺失站点追加
        assert "HHan" in data["config"]["trackers"]
        assert any("hdchina.org" in str(v["domains"]) for v in data["config"]["trackers"].values())


def test_export_yaml_template_only_missing_dry_run():
    """only_missing + dry_run: 只导出未配置站点骨架, 不写文件"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [{"url": "https://hdchina.org/announce.php"}]
        cfg = _make_config_with_trackers(_tracker("HHan", ["tracker.hhanclub.net"]))

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=True, only_missing=True)
        assert not os.path.exists(out_path), "dry-run 不应写文件"


def test_export_yaml_template_name_collision():
    """域名转名称冲突时自动加序号"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {"hdchina_org": {"domains": ["x.com"]}}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [{"url": "https://hdchina.org/announce.php"}]
        cfg = _make_config_with_trackers(_tracker("HHan", ["tracker.hhanclub.net"]))

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=False, only_missing=False)
        with open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        assert "hdchina_org_1" in data["config"]["trackers"]


def test_export_yaml_template_merged_default_only_missing():
    """默认合并(仅缺失): 两个共现缺失域名 -> 一条合并条目(domains 两元素, 键 = 最短域名生成的名字)"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [
            {
                "url": "https://hdchina.org/announce.php"
            },
            {
                "url": "https://pt.example.com/announce.php"
            },
        ]
        cfg = _make_config_with_trackers(_tracker("HHan", ["tracker.hhanclub.net"]))

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=False, only_missing=True)
        with open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        trackers = data["config"]["trackers"]
        assert list(trackers.keys()) == ["hdchina_org"], "共现两域名必须合并为一条, 键 = 最短域名生成的名字"
        merged = trackers["hdchina_org"]
        assert merged["domains"] == ["hdchina.org", "pt.example.com"]
        assert merged["tags"] == [exporter.gen_default_tag("hdchina.org")]


def test_export_yaml_template_merged_default_append():
    """默认合并(追加模式): 现有配置保留, 共现缺失域名并为一条合并条目"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {"HHan": {"domains": ["tracker.hhanclub.net"]}}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [
            {
                "url": "https://hdchina.org/announce.php"
            },
            {
                "url": "https://pt.example.com/announce.php"
            },
        ]
        cfg = _make_config_with_trackers(_tracker("HHan", ["tracker.hhanclub.net"]))

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=False, only_missing=False)
        with open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        trackers = data["config"]["trackers"]
        assert "HHan" in trackers, "追加模式必须保留现有配置"
        assert list(trackers.keys()) == ["HHan", "hdchina_org"]
        assert trackers["hdchina_org"]["domains"] == ["hdchina.org", "pt.example.com"]


def test_export_yaml_template_split_trackers_append():
    """split_trackers=True + 追加模式: 现有配置保留, 共现缺失域名逐域名各一条"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {"HHan": {"domains": ["tracker.hhanclub.net"]}}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [
            {
                "url": "https://hdchina.org/announce.php"
            },
            {
                "url": "https://pt.example.com/announce.php"
            },
        ]
        cfg = _make_config_with_trackers(_tracker("HHan", ["tracker.hhanclub.net"]))

        exporter.export_yaml_template(
            client, cfg, cfg_path, out_path, dry_run=False, only_missing=False, split_trackers=True
        )
        with open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        trackers = data["config"]["trackers"]
        assert "HHan" in trackers, "追加模式必须保留现有配置"
        assert list(trackers.keys()) == ["HHan", "hdchina_org", "pt_example_com"]
        assert trackers["hdchina_org"]["domains"] == ["hdchina.org"]
        assert trackers["pt_example_com"]["domains"] == ["pt.example.com"]


def test_export_yaml_template_split_trackers():
    """split_trackers=True: 拆回逐域名路径, 共现两域名各出一条单域名条目"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [
            {
                "url": "https://hdchina.org/announce.php"
            },
            {
                "url": "https://pt.example.com/announce.php"
            },
        ]
        cfg = _make_config_with_trackers(_tracker("HHan", ["tracker.hhanclub.net"]))

        exporter.export_yaml_template(
            client, cfg, cfg_path, out_path, dry_run=False, only_missing=True, split_trackers=True
        )
        with open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        trackers = data["config"]["trackers"]
        assert set(trackers.keys()) == {"hdchina_org", "pt_example_com"}, "拆分路径必须逐域名各一条"
        assert trackers["hdchina_org"]["domains"] == ["hdchina.org"]
        assert trackers["pt_example_com"]["domains"] == ["pt.example.com"]


def test_export_yaml_template_all_singleton_groups_equivalent():
    """全单元素缺失组: 合并路径(默认)与 split 路径产物等价(退化 = 改造前行为)"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        merged_path = os.path.join(td, "merged.yml")
        split_path = os.path.join(td, "split.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")
        client.torrents_trackers = lambda h: [{"url": f"https://{h}.example.com/announce.php"}]
        cfg = _make_config_with_trackers(_tracker("HHan", ["tracker.hhanclub.net"]))

        exporter.export_yaml_template(client, cfg, cfg_path, merged_path, dry_run=False, only_missing=True)
        exporter.export_yaml_template(
            client, cfg, cfg_path, split_path, dry_run=False, only_missing=True, split_trackers=True
        )
        with open(merged_path, "r", encoding="utf-8") as f:
            merged = yaml.load(f, Loader=yaml.BaseLoader)
        with open(split_path, "r", encoding="utf-8") as f:
            split = yaml.load(f, Loader=yaml.BaseLoader)
        assert merged == split, "全单元素组时合并路径必须与拆分路径产物等价"


def test_export_yaml_template_stamps_schema_version():
    """写出侧打标(计划 26-09-26-0506): 导出的模板统一带当前 schema 版本章"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents_trackers = lambda h: []
        cfg = _make_config_with_trackers()

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=False, only_missing=False)
        with open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        from auto_qb.infra.versioning import CURRENT_VERSIONS

        assert data["config"]["schema_version"] == str(CURRENT_VERSIONS["config"]), \
            "模板必须带当前版本章(BaseLoader 读回为字符串)"


# ---------- W6(R30) 变异审计守阵: exporter.py 功能面 ----------


def test_collect_all_tracker_hostnames_per_hash_union_and_error_isolation():
    """守阵(变异审计 W6): 逐种取 tracker 必须按 tor.hash; 单种异常跳过不终止; 多种域名并集

    - 取 tracker 不按 hash(恒 None) -> 替身按 hash 分桶失配, 全部域名丢失;
    - continue -> break: 首个异常即终止扫描, 缺失域漏报;
    - 并集变覆盖: 只剩最后一个种子的域名。
    """
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")

    def trackers(h):
        if h == "H1":
            raise RuntimeError("boom")  # H1 异常: 隔离后 H2 照常收集
        if h == "H2":
            return [{"url": "https://tracker.kufirc.com/announce.php"}]
        return [{"url": "https://tracker.hhanclub.net/announce.php"}]

    client.torrents_trackers = trackers
    assert exporter.collect_all_tracker_hostnames(client) == {"tracker.kufirc.com"}

    client.torrents_trackers = lambda h: [{"url": f"https://{h}.example/announce.php"}]
    hosts = exporter.collect_all_tracker_hostnames(client)
    assert hosts == {"h1.example", "h2.example"}, "多种域名必须并集(覆盖语义只留最后一个)"


def test_find_missing_domains_substring_both_directions():
    """守阵(变异审计 W6): 缺失筛选的包含匹配双向成立(configured in host 或 host in configured)

    or -> and(近似全等)时已配置站点的子域被误判缺失 -> 重复条目。
    """
    # 方向一: configured 是 host 的子域
    assert exporter.find_missing_domains({"tracker.hhanclub.net"}, {"hhanclub"}) == set()
    # 方向二: host 是 configured 的子域
    assert exporter.find_missing_domains({"hhanclub"}, {"tracker.hhanclub.net"}) == set()
    assert exporter.find_missing_domains({"tracker.hhanclub.net"}, {"kufirc"}) == {"tracker.hhanclub.net"}


def test_capitalize_special_tag_bare_hd_pt():
    """守阵(变异审计 W6): 裸 hd/pt(无后随字母)大写化 —— 条件恒真时 None.upper() 崩溃;
    else "" -> "XXXX" 时生成 "HDXXXX" 垃圾标签写入导出模板(产物污染)"""
    assert exporter.capitalize_special_tag("hd") == "HD"
    assert exporter.capitalize_special_tag("pt") == "PT"
    assert exporter.capitalize_special_tag("HD") == "HD"
    assert exporter.capitalize_special_tag("x-hd-y") == "x-HD-y"


def test_gen_tracker_name_uppercase_and_multi_conflict():
    """守阵(变异审计 W6): 大写域名逐字清洗; 双重冲突(_1 也被占)后缀递进到 _2

    - 字符类去 A-Z: 大写域名整段被替换成下划线, 生成名不同;
    - counter+=1 -> =1: 双重冲突恒重试 base_1 -> 死循环挂起(本用例在变异下超时即红);
    - counter+=1 -> -=1/+=2: 后缀序列变 _0/跳号。
    """
    assert exporter.gen_tracker_name("HDChina.org", set()) == "HDChina_org"
    taken = {"x_com", "x_com_1"}
    assert exporter.gen_tracker_name("x.com", taken) == "x_com_2", "双重冲突: _1 已占 -> 递进 _2"
    assert "x_com_2" in taken


def test_build_tracker_entry_template_contract():
    """守阵(变异审计 W6): 导出模板条目 schema 键名与示例值逐字契约

    键名损坏(XX/大写) -> 用户照填后 load_config fail-fast 拦下(交付物损坏面);
    示例值被污染(XX12HXX/12h/XX80%XX/ratio 1)同样即红。
    """
    assert exporter.build_tracker_entry("hdchina.org") == {
        "domains": ["hdchina.org"],
        "tags": ["HDChina"],
        "upload_speed_limit": "0KiB/s",
        "download_speed_limit": "0KiB/s",
        "hr":
            {
                "required_seeding_time": "3D",
                "required_share_ratio": 0,
                "extra_seeding_time": "12H",
                "condition": "80%",
            },
    }


def test_export_yaml_template_default_append_mode():
    """守阵(变异审计 W6, 极低危): only_missing 缺省 False(追加模式)

    唯一调用方 cli.py 显式传参, 默认值生产不可达 —— 但默认翻 True 会静默丢掉整份现有配置,
    本条以「不传 only_missing 的调用形态」钉住缺省契约。
    """
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {"HHan": {"domains": ["tracker.hhanclub.net"]}}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [{"url": "https://hdchina.org/announce.php"}]
        cfg = _make_config_with_trackers(_tracker("HHan", ["tracker.hhanclub.net"]))

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=False)
        with open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        assert "HHan" in data["config"]["trackers"], "缺省必须是追加模式(保留现有配置)"
        assert any("hdchina.org" in str(v["domains"]) for v in data["config"]["trackers"].values())


def test_export_yaml_template_scan_audit_logs(caplog):
    """守阵(变异审计 W6, 低危): 扫描/发现/导出 INFO 审计日志逐条在位(丢真即红)"""
    import logging

    caplog.set_level(logging.INFO, logger="auto_qb.core.exporter")
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [{"url": "https://hdchina.org/announce.php"}]
        cfg = _make_config_with_trackers()

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=True)
        msgs = [r.getMessage() for r in caplog.records]
        assert any("扫描 1 个种子" in m for m in msgs), msgs
        assert any("发现 1 个去重" in m for m in msgs), msgs
        assert any("发现 1 个未配置域名" in m for m in msgs), msgs
        assert any("未配置域名" in m and "hdchina.org" in m for m in msgs), msgs
        assert any("已导出 YAML 模板" in m for m in msgs), msgs


def test_export_yaml_template_only_missing_output_keys():
    """守阵(变异审计 W6): only_missing 产物 config 键面恰为 trackers+schema_version;
    回写 trackers 键名损坏 -> 追加条目丢失/多伪键(交付物损坏面)"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"trackers": {}}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [{"url": "https://hdchina.org/announce.php"}]
        cfg = _make_config_with_trackers()

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=False, only_missing=True)
        with open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        assert set(data["config"].keys()) == {"trackers", "schema_version"}, data["config"].keys()
        assert any("hdchina.org" in str(v["domains"]) for v in data["config"]["trackers"].values()), \
            "生成的站点条目必须回写到 trackers 键下"


def test_export_yaml_template_missing_trackers_section():
    """守阵(变异审计 W6, 中危): 配置无 trackers 段(_strip_none 剔空常态)走缺省 {} 不崩

    get("trackers", {}) 缺省 -> None 时 set(None) TypeError(默认值即常态路径)。
    """
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump({"config": {"schema_version": "0"}}, f, allow_unicode=True)
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [{"url": "https://hdchina.org/announce.php"}]
        cfg = _make_config_with_trackers()

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=False, only_missing=False)
        with open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        assert any("hdchina.org" in str(v["domains"]) for v in data["config"]["trackers"].values())


def test_export_yaml_template_pins_utf8_encoding(monkeypatch):
    """守阵(变异审计 W6, 中危/平台相关): 读 config 与写 output 显式 encoding="utf-8"

    encoding -> None 在 Windows 生产 locale(GBK)下读 utf-8 配置即 mojibake/UnicodeDecodeError;
    WSL 测试环境 UTF-8 locale 下该面不敏感 —— 故用 open 探针把 encoding 参数本身钉成
    全平台可观测断言, 中文站点名往返作内容面加强(Windows 下变异即 mojibake)。
    """
    import builtins

    real_open = builtins.open
    seen = {}

    def spy(file, mode="r", *args, **kwargs):
        seen[os.fspath(file)] = (mode, kwargs.get("encoding"))
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        out_path = os.path.join(td, "out.yml")
        with real_open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"config": {
                    "trackers": {
                        "站A": {
                            "domains": ["tracker.hhanclub.net"]
                        }
                    }
                }},
                f,
                allow_unicode=True,
            )
        client = FakeClient()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents_trackers = lambda h: [{"url": "https://hdchina.org/announce.php"}]
        cfg = _make_config_with_trackers(_tracker("HHan", ["tracker.hhanclub.net"]))

        exporter.export_yaml_template(client, cfg, cfg_path, out_path, dry_run=False, only_missing=False)
        assert seen[cfg_path] == ("r", "utf-8"), seen
        assert seen[out_path] == ("w", "utf-8"), seen
        with real_open(out_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        assert "站A" in data["config"]["trackers"], "中文站点名必须按 utf-8 原样往返"


def test_collect_torrent_tracker_hostnames_prefers_fresh_bypass():
    """api 暴露 fresh 直查(= QbApi facade)时扫描优先用之, 不吃记录级缓存; 逐种按 hash 取"""
    class _FacadeShapedApi:
        def __init__(self):
            self.fresh_hashes = []

        def torrents_info(self):
            return [FakeTorrent(hash="H1"), FakeTorrent(hash="H2")]

        def torrents_trackers(self, h):  # 模拟记录级缓存: 恒回旧值
            return [{"url": "https://stale.example.com/announce"}]

        def torrents_trackers_fresh(self, h):
            self.fresh_hashes.append(h)
            return [{"url": "https://fresh.example.com/announce"}]

    api = _FacadeShapedApi()
    assert exporter.collect_torrent_tracker_hostnames(api) == [{"fresh.example.com"}, {"fresh.example.com"}]
    assert sorted(api.fresh_hashes) == ["H1", "H2"], "必须逐种走 fresh 直查"


def test_collect_torrent_tracker_hostnames_fresh_bypass_facade_cache():
    """红验(issue 26-11-04-0228): qB 侧改 tracker 后记录级缓存吃旧值, 扫描仍读到改后新值"""
    from auto_qb.core.qbapi import QbApi
    from auto_qb.torrents import TorrentRecord, TorrentStore

    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
    client.trackers_map["H1"] = [{"url": "https://old.example.com/announce"}]
    store = TorrentStore(client)
    store.restore_torrent(TorrentRecord.from_torrent(FakeTorrent(hash="H1", name="T1")))
    api = QbApi(client, store)

    # 常规读路径先填充记录级惰性缓存(old; 主循环/tracker 重绑的既有语义)
    assert api.torrents_trackers("H1")[0]["url"] == "https://old.example.com/announce"

    # qB 侧(网页/外部)改 tracker —— 不经产品写路径, 缓存不失效
    client.trackers_map["H1"] = [{"url": "https://new.example.com/announce"}]

    # 常规 facade 读路径吃旧值(惰性缓存的既有语义, 主循环/tracker 重绑依赖它零调用)
    assert api.torrents_trackers("H1")[0]["url"] == "https://old.example.com/announce"
    # 扫描走 fresh 直查: 读到改后新值(且不回填污染记录级缓存)
    assert exporter.collect_torrent_tracker_hostnames(api) == [{"new.example.com"}]
    assert api.torrents_trackers("H1")[0]["url"] == "https://old.example.com/announce"
