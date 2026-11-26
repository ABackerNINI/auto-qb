"""`hr_runtime_support` 支撑: 从 `test_hr_runtime.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import logging

import socket

import threading

import time

import pytest

from auto_qb.config.models import Config, HrChannelConfig, HrCheckConfig, SiteHrCheckConfig, TrackerConfig

from auto_qb.hr.channel import HrChannelBindError

from auto_qb.hr.fetcher import HrChannelStopped, HrChannelUnavailable, NullFetcher

from auto_qb.hr.model import HrEntry

from auto_qb.hr.resolve import HrAnchor, HrIdentity, HrSiteView, HrViewSet

from auto_qb.hr.runtime import HrRuntime

from auto_qb.hr.service import POLL_INTERVAL

import auto_qb.hr.runtime as rt_module

from _test_ports import free_port as _free_port  # noqa: E402  端口单点(防散落守卫: tests/test_free_port.py); 取当前空闲端口


class _FakeStore:
    """锚点构建只读 store.all()(plan §05: 实现迁门面后经 manager.store 只读取数)"""
    def all(self):
        return []


class _FakeManager:
    """门面只用到 config 与 store(锚点构建的只读数据源)"""
    def __init__(self, config, anchors=None, store=None):
        self.config = config
        self.store = store if store is not None else _FakeStore()  # anchors 参数已无消费方(P5 后 _anchors 自持实现), 留参兼容旧调用


def make_config(
    tmp_path,
    *,
    enabled=True,
    channel=False,
    port=0,
    # !discovery_port 默认 0(发现关)而不是模型默认 18788: 候选端口 18788-18795 是**固定**的,
    # 并行(-n 8)下多个 worker 与用户真实实例(实测正占着 18788)会把它们占满 ⇒
    # HrDiscoveryServer.start() 记 WARNING「全部被占」⇒ 污染本文件「生命周期消息只记 INFO」
    # 一族断言(issue 26-10-16-0348 实报偶发判红)。发现服务的行为单测在 test_hr_discovery.py
    # (自选 _free_port 基底); 本文件没有一条用例测发现, 不该碰共享固定端口。
    discovery_port=0,
    shared_dir="",
    site_enabled=True,
    request_timeout=180.0,
    extension_id="a" * 32,
):
    # extension_id 默认填一个合法值: 端点纵深提示(extension_id 留空 = WARNING, 见
    # test_extension_id_empty_warns)不应打扰「测生命周期消息是 INFO」这类无关用例
    config = Config()
    config.data_dir = str(tmp_path)
    config.state_file = str(tmp_path / "state.json")
    config.hr_check = HrCheckConfig(
        enabled=enabled,
        channel=HrChannelConfig(
            enabled=channel,
            port=port,
            discovery_port=discovery_port,
            request_timeout=request_timeout,
            extension_id=extension_id,
        ),
        shared_dir=shared_dir,
    )
    config.trackers = {
        "pt.example.com":
            TrackerConfig(
                name="pt.example.com",
                domains=["pt.example.com"],
                hr_check=SiteHrCheckConfig(
                    enabled=site_enabled,
                    tracker="pt.example.com",
                    hr_page_url="https://pt.example.com/myhr.php",
                    required_seeding_time=2 * 86400.0,
                    # 生产里 enabled 站点的 listing 必由档案派生填充(loaders._resolve_hr_site_bindings);
                    # 手工构造贴近生产形态 —— 空 listing = 未绑定, 取数侧 fetchable 不收(issue 26-10-05-0922)
                    listing="list",
                ),
            )
    }
    return config


def make_runtime(tmp_path, **kwargs):
    return HrRuntime(_FakeManager(make_config(tmp_path, **kwargs)))


def _two_site_config(tmp_path, **kwargs):
    """两站点配置: 站点清单的 ", " 拼接在多站点下才可辨"""
    config = make_config(tmp_path, **kwargs)
    config.trackers["pt2.example.com"] = TrackerConfig(
        name="pt2.example.com",
        domains=["pt2.example.com"],
        hr_check=SiteHrCheckConfig(
            enabled=True,
            tracker="pt2.example.com",
            hr_page_url="https://pt2.example.com/myhr.php",
            listing="list",  # 同上: 手工构造贴近生产形态(档案派生), 空 = 未绑定不取数
        ),
    )
    return config
