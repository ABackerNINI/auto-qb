"""test_hr_channel 测试计划: 通道协议 / 密钥 / origin 白名单 / URL 白名单(SSRF)

## 测试计划(每个测试函数一条)
- test_token_from_config_wins: 配了 token 就直接用, 不生成密钥文件
- test_token_generated_then_reused: 留空 -> 随机生成并持久化到 <data_dir>/hr.token, 再调复用同一值
- test_generated_token_not_in_logs: 生成的密钥内容不进日志(只提示文件路径) —— 日志会被 /api/log 读回
- test_origin_allowed_extension_only: 扩展 origin 放行, 普通网页 origin 拒(纵深防御), 空 Origin 放行
- test_origin_pinned_extension_id: 配了 extension_id 就只认那一个扩展
- test_extension_id_regex_matches_validation: 通道侧正则与 config 校验层等价(两处实现必须一致)
- test_url_policy_allows_declared_host_and_paths: 同域名的 HR 页与下载路径放行, 他站/他路径/非 http 拒
- test_url_policy_require_raises_on_unlisted: require 非白名单 URL 抛 HrChannelError(下发前 fail-fast)
- test_result_from_json_text_and_binary: text 与 body_b64 两种回传都能解析
- test_result_from_json_rejects_malformed: 缺 id / base64 坏 / 成功但无体 -> HrChannelError
- test_parse_results_single_and_batch: 单条与 {"results":[...]} 批量都可
- test_decode_json_rejects_garbage: 非 JSON 字节 -> HrChannelError
- test_host_and_path_helpers: host_of/path_of 对端口/查询串/无 scheme/无路径的处理
- test_describe_token_source: 密钥来源只报来源不报内容
"""
import logging

import pytest

from auto_qb.config.validation import sections as validation_sections
from auto_qb.hr.channel import (
    EXTENSION_ID_RE,
    HrChannelError,
    HrResult,
    UrlPolicy,
    decode_json,
    describe_token_source,
    host_of,
    origin_allowed,
    parse_results,
    path_of,
    resolve_token,
    token_path,
)
from hr_helpers import site_conf

EXT_A = "chrome-extension://" + "a" * 32
EXT_B = "chrome-extension://" + "b" * 32


def _policy(**overrides) -> UrlPolicy:
    conf = site_conf(**overrides)
    return UrlPolicy({"pt.example.com": conf})


# ---------- 密钥 ----------


def test_token_from_config_wins(tmp_path):
    assert resolve_token("configured-token", str(tmp_path)) == "configured-token"
    assert not (tmp_path / "hr.token").exists(), "显式配置时不该生成密钥文件"


def test_token_generated_then_reused(tmp_path):
    first = resolve_token("", str(tmp_path))
    assert len(first) == 64, "随机密钥为 32 字节 hex"
    assert token_path(str(tmp_path)) == str(tmp_path / "hr.token")
    assert (tmp_path / "hr.token").read_text(encoding="ascii").strip() == first
    assert resolve_token("", str(tmp_path)) == first, "重启复用同一密钥(否则扩展侧要反复改)"


def test_generated_token_not_in_logs(tmp_path, caplog):
    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr.channel"):
        token = resolve_token("", str(tmp_path))
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert token not in text, "密钥内容绝不能进日志(/api/log 能读回日志)"
    assert "hr.token" in text, "应提示密钥文件路径供用户查看"
    assert describe_token_source("", str(tmp_path)) == "file"


# ---------- origin 白名单 ----------


def test_origin_allowed_extension_only():
    assert origin_allowed(EXT_A)
    assert origin_allowed(EXT_A, "a" * 32), "填了 id 且匹配 -> 放行"
    assert origin_allowed(EXT_A, "b" * 32) is False, "填了 id 但不匹配 -> 拒"
    assert origin_allowed("https://evil.example.com") is False, "普通网页 JS 一律拒"
    assert origin_allowed("") is True, "无 Origin(扩展后台请求未必带): 放行, 真鉴权是 token"


def test_origin_pinned_extension_id():
    assert origin_allowed(EXT_B, "b" * 32)
    assert origin_allowed("chrome-extension://" + "c" * 32, "b" * 32) is False


def test_extension_id_regex_matches_validation():
    """两处实现(hr.channel 与 config 校验层)必须等价, 否则「配了却永远不生效」"""
    samples = ["a" * 32, "p" * 32, "q" * 32, "a" * 31, "A" * 32, "1" * 32, "", "a" * 33]
    for sample in samples:
        assert bool(EXTENSION_ID_RE.match(sample)) == bool(validation_sections._EXTENSION_ID_RE.match(sample)), sample


# ---------- URL 白名单(SSRF) ----------


def test_url_policy_allows_declared_host_and_paths():
    policy = _policy()
    assert policy.site_of("https://pt.example.com/myhr.php?hrtype=A&page=2") == "pt.example.com"
    assert policy.allows("pt.example.com", "https://pt.example.com/myhr.php?hrtype=A")
    assert policy.allows("pt.example.com", "https://pt.example.com/download.php?id=313852")
    assert policy.allows("pt.example.com", "http://pt.example.com/download.php?id=1"), "http 放行"
    assert policy.allows("pt.example.com", "https://other.example.com/myhr.php") is False, "他站域名拒"
    assert policy.allows("pt.example.com", "https://pt.example.com/admin.php") is False, "同站非声明路径拒"
    assert policy.allows("pt.example.com", "file:///etc/passwd") is False, "非 http(s) 拒"
    assert policy.site_of("https://unlisted.example.com/myhr.php") == ""


def test_url_policy_require_raises_on_unlisted():
    policy = _policy()
    with pytest.raises(HrChannelError):
        policy.require("https://evil.example.com/myhr.php")
    with pytest.raises(HrChannelError):
        policy.require("https://pt.example.com/secret.php")
    assert policy.require("https://pt.example.com/myhr.php") == "pt.example.com"


# ---------- 回传解析 ----------


def test_result_from_json_text_and_binary():
    text = HrResult.from_json({"id": "t1", "ok": True, "status": 200, "url": "u", "text": "<html>ok</html>"})
    assert text.ok and text.text == "<html>ok</html>"
    blob = HrResult.from_json({"id": "t2", "ok": True, "body_b64": "AAEC"})
    assert blob.body == b"\x00\x01\x02"
    fail = HrResult.from_json({"id": "t3", "ok": False, "error": "HTTP 403", "retry_after": 30})
    assert not fail.ok and fail.error == "HTTP 403" and fail.retry_after == 30.0


def test_result_from_json_rejects_malformed():
    for bad in (
        "not-a-dict",
        {},
        {
            "ok": True,
            "text": "x"
        },
        {
            "id": "t",
            "ok": True
        },
        {
            "id": "t",
            "ok": True,
            "body_b64": "!!!not base64!!!"
        },
        {
            "id": "t",
            "ok": True,
            "body_b64": 123
        },
        {
            "id": "t",
            "ok": True,
            "text": 42
        },
    ):
        with pytest.raises(HrChannelError):
            HrResult.from_json(bad)


def test_parse_results_single_and_batch():
    one = parse_results({"id": "a", "ok": False, "error": "x"})
    assert [r.task_id for r in one] == ["a"]
    many = parse_results({"results": [{"id": "a", "ok": False}, {"id": "b", "ok": False}]})
    assert [r.task_id for r in many] == ["a", "b"]
    assert [r.task_id for r in parse_results([{"id": "c", "ok": False}])] == ["c"]
    with pytest.raises(HrChannelError):
        parse_results({"results": "nope"})


def test_decode_json_rejects_garbage():
    assert decode_json(b'{"a":1}') == {"a": 1}
    for bad in (b"not json", b"\xff\xfe\x00"):
        with pytest.raises(HrChannelError):
            decode_json(bad)


def test_host_and_path_helpers():
    assert host_of("https://PT.Example.com:8443/myhr.php?a=1") == "pt.example.com"
    assert path_of("https://pt.example.com:8443/myhr.php?a=1") == "/myhr.php"
    assert host_of("/no-scheme") == ""
    assert path_of("https://pt.example.com") == ""
    assert path_of("https://pt.example.com/") == "/"


def test_describe_token_source(tmp_path):
    assert describe_token_source("given", str(tmp_path)) == "config"
    assert describe_token_source("", str(tmp_path)) == "none"
    resolve_token("", str(tmp_path))
    assert describe_token_source("", str(tmp_path)) == "file"
