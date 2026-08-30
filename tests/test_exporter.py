"""exporter 模块测试: 域名收集 / 缺失筛选 / 默认标签 / 模板导出"""
import os
import tempfile

import yaml

from auto_qb import exporter
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


def test_find_missing_domains():
    """筛选未配置域名(包含关系: configured 在 host 中或 host 在 configured 中)"""
    all_domains = {"tracker.hhanclub.net", "tracker.kufirc.com", "other.site.net"}
    configured = {"tracker.hhanclub.net"}
    assert exporter.find_missing_domains(all_domains, configured) == {"tracker.kufirc.com", "other.site.net"}
    # 无缺失
    assert exporter.find_missing_domains(all_domains, set(all_domains)) == set()


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
