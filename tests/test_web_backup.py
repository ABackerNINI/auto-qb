"""test_web_backup 测试计划: 配置备份 bundle 导出 GET /api/backup/export(计划 26-11-14-0624 S1)

## 测试计划(每个测试函数一条)
- test_backup_export_requires_auth: 无 Bearer 一律 401(与其它 /api/* 同走 factory 全局鉴权闸)
- test_backup_export_bundle_shape_and_masks: bundle 顶层形状(format/bundle_version/created_at/
  app_version)+ 敏感键全掩码(主 qB 密码 / tracker passkey / hr.token / transfer targets 条目
  password+api_key 同一哨兵; web.token 留空不掩码)+ 全响应无任何明文凭据(D2 掩码不出机);
  契约负例钉死: 普通列表(非 targets)不下钻(条目内 password 键原样保留), targets 条目
  空值不掩码
- test_backup_export_mask_diff_only_sensitive_lines: R7 byte 级钉 —— config_yaml 与
  dump(load(原文)) 无掩码基线逐行比对: 行数一致, 差异行必是敏感值行(掩码侧含哨兵),
  前注/行尾注释/空行/尾换行全保留
- test_backup_export_mask_failure_500_no_secret_echo: 重复键坏 YAML(ruamel DuplicateKeyError
  路径) -> 500, 且响应不含异常文本回显的任何明文凭据(500 detail 只留固定文案 + 类型名,
  绝不拼 {e} —— 异常文本逐字回显重复键明文值, D2)
- test_mask_yaml_text_non_mapping_returns_empty: mask_yaml_text 直调 —— 空串/列表 YAML/
  标量 YAML 输入一律返回 ""(非映射当空, 与 read_tree 同口径, 堵明文原样返回的 D2 旁路)
- test_backup_export_gtm_offline_section_null: 工具离线(agent 探活 None) -> bundle["gtm"]
  is None(缺段 = 不含该面), 且 config_yaml/webui_keys 照常导出(离线不致命, D9)
- test_backup_export_missing_config_file_empty_section: config.yml 不存在 -> config_yaml 段
  为空串, 其余段(webui_keys/gtm/顶层形状)照常导出
- test_backup_export_mask_exception_wrapped_500: monkeypatch mask_yaml_text 抛异常 -> 500,
  detail 含「掩码化失败」与异常类型名, 不含异常文本(泄敏面同上)
- test_backup_export_gtm_online_section: 工具在线 -> gtm 段 = {config 合并树, tool_version,
  captured_at}, 与 GET /api/traffic/monitor/status 同源(同走 _source_status 单点)
- test_backup_export_gtm_echo_not_dict_null: 探活成功但 /status 回显非 200(如密钥不符)/
  ToolUnreachable 竞态 -> bundle["gtm"] is None 且整体 200(离线不致命, D9)
- test_backup_export_keys_section_matches_get_api_keys: webui_keys 段形状与 GET /api/keys
  逐字一致(同走 load_keys_doc 单点)

S2(POST /api/backup/import, 计划 §04 S2 验收矩阵逐条):
- test_backup_import_requires_auth: 无 Bearer 一律 401(factory 全局鉴权闸)
- test_backup_import_same_machine_restores_secrets: 同机掩码还原 —— 导出 bundle 原样导回,
  写盘值=本机现值非哨兵(含 targets 条目 password/api_key), 「********」字面量绝不落盘,
  落盘内容 byte 级还原原文(R7 round-trip 注释不丢), reload_config 已投递主循环
- test_backup_import_unresolvable_sentinels_422_aggregated: 跨机不可 resolve(R1)—— bundle
  有哨兵条目而本机无对应键 -> 422 聚合逐路径列出, 可 resolve 的键不报, 磁盘一字未动
- test_backup_import_readonly_fallback: bundle 的 data_dir(readonly 程序托管字段)回退为本机
  磁盘旧值, 不随 bundle 落盘
- test_backup_import_rejects_newer_versions: bundle_version 高于本机 -> 422 提示先升级;
  config schema_version 高于当前 -> 422; 两道闸都磁盘一字未动
- test_backup_import_older_bundle_writes_as_is: 旧版本 bundle(v7)原样落盘 —— 磁盘版本章保持
  bundle 原值不盖当前章(R2, 迁移靠下次启动 materialize 链), 内容 byte 级=掩码 resolve 后原文,
  applied 且 reload_config 已投递(loaders 内存迁移)
- test_backup_import_unknown_section_ignored_with_warning: 未知顶层 section 忽略 + warnings
  (向前兼容); 已知段照常应用
- test_backup_import_request_shape_400: sections 缺失/空/bundle_version 非整数 -> 400
- test_backup_import_invalid_keys_422_no_half_apply: keys 结构非法 -> 422, config 不半应用
  (磁盘一字未动, keys 文件未创建)
- test_backup_import_empty_config_yaml_skipped: config_yaml 空串段 -> skip + warnings(不致命),
  同请求的 webui_keys 照常应用
- test_backup_import_partial_sections_only_selected_applied: 部分段勾选 —— 只勾 webui_keys,
  config 磁盘未动且不投递 reload
- test_backup_import_gtm_offline_skipped_not_fatal: gtm 离线(D9)—— 段为 null 或工具未就绪
  均 skipped + 原因, config 照常应用不阻断
- test_backup_import_gtm_online_applied: 工具在线 -> gtm 走 PUT /config 代理应用, 信封内
  未知键(tool_version 等)忽略不报错
- test_backup_import_gtm_tool_400_into_warnings: 工具 400 校验错透传进 warnings(R3, 该段不
  应用), 不阻断 config 应用
- test_backup_import_idempotent: 幂等 —— 同一 bundle 导入两次, config/keys 终态一致

评审修复回归(26-11-15 三面评审 13 条):
- test_backup_import_root_non_mapping_422: config_yaml 为列表/标量文档 -> 422「不是映射文档」,
  磁盘未动
- test_backup_import_empty_config_section_422: 根映射但 config 段缺失/空映射/非映射键(major:
  防一次 200 导入静默重置生产配置)-> 422, 磁盘未动
- test_backup_import_residual_sentinel_422: 手编 bundle 在 unmask 不下钻的普通列表位放哨兵
  (R1 旁路)-> 写盘前残留哨兵兜底闸 422 逐路径, 磁盘未动
- test_backup_import_gtm_tool_400_nondict_payload: 工具 400 回非 dict JSON(契约漂移)->
  error_text 兜底 str 化进 warnings, 不 500(gtm 失败不阻断契约保住)
- test_backup_import_gtm_online_applied: 捕获入参替身 —— 断言转发 payload == tool_config
  (只转发 config 键, tool_version/信封未知键不进载荷)
- test_backup_import_older_bundle_writes_as_is: 补断 reload 载荷为 load_config 内存迁移产物
- test_backup_import_same_machine_restores_secrets: 补断 .bak 存在且内容 == 导入前磁盘原文
- test_backup_import_readonly_delete_branch: 本机无该 readonly 键而 bundle 带 -> 导入后该键
  消失(走 schema 默认)
- test_backup_import_holds_write_lock: R8 证据 —— 导入路径经 writer._WRITE_LOCK 同一单点
  (录制锁)
- test_unmask_yaml_doc_old_value_table: 顶层路径表驱动(空串旧值/旧值哨兵 -> missing; 数字/
  布尔/串原样回填)
- test_unmask_yaml_doc_target_items_old_value: targets 路径同口径直测(空串旧值 -> missing,
  正常值按 name 配对回填)
- test_unmask_yaml_doc_no_local_doc_all_missing: 本机无配置文件(old_doc=None)全 missing

覆盖率闸回绿回归(26-11-15, S1-S4 评审轮防御闸门分支补测):
- test_backup_import_alias_shared_reference_422: alias 共享引用闸 —— anchor/alias 文档 422
  (磁盘未动) + _scan_yaml_doc_shape 直测(共享容器 False / 无共享 True)
- test_backup_import_depth_gate_422: 深度上限闸(小阈值注入 _MAX_YAML_DOC_DEPTH)-> 422
- test_backup_import_node_count_gate_422: 节点数上限闸(小阈值注入 _MAX_YAML_DOC_NODES)-> 422
- test_backup_import_text_length_gate_422: 文本 1MiB 长度上限闸(解析前拒, 不耗解析时间)
- test_backup_import_parse_recursion_422: 解析期 RecursionError(flow 深嵌套小文本)-> 422
- test_backup_import_parse_failure_500_no_secret_echo: bundle 重复键解析失败 -> 500 只留类型名,
  异常文本回显的明文凭据不进响应(D2)
- test_backup_import_body_non_dict_400: body 非 dict -> 400(端点直调注入; TestClient JSON 非
  dict 被 FastAPI 先拦)
- test_backup_import_local_config_broken_commit_500: 本机 config.yml 坏 YAML -> 提交路径现读炸
  500 只留类型名(R8 锁内读改写面), 明文不回显
- test_backup_import_precheck_local_broken_500: keys 已有错 + 本机坏 YAML -> 聚合先验面 500
- test_backup_import_precheck_config_error_aggregated: config 侧 load_config 校验失败 + keys 侧
  非法 -> 同一 422 聚合两侧错误
- test_backup_import_precheck_missing_aggregated: keys 已有错 + config 有不可 resolve 哨兵 ->
  同一 422 含 R1 逐路径与 keys 错
- test_backup_import_no_local_config_all_sentinels_missing: 本机无 config.yml -> 全部哨兵不可
  resolve(R1 端点级, 走提交路径 missing 兜底闸), 未写盘
- test_backup_import_gtm_tool_unreachable_skipped: 探活在线但 PUT /config 时 ToolUnreachable ->
  skipped, 不阻断 config
- test_backup_import_gtm_unexpected_status_skipped: 工具返回非预期状态码(503)-> skipped +
  error_text 透传
- test_write_yaml_doc_direct_write_and_residual_gate: write_yaml_doc 直测(S2 非端点落盘口)+
  残留哨兵兜底闸 ConfigError 拒写不半写
- test_mask_unmask_yaml_node_non_dict_passthrough: _mask_yaml_node/_unmask_yaml_node 非 dict
  节点直通(防御分支直测)
- test_mask_yaml_targets_non_dict_items_untouched: targets 列表非 dict 条目掩码侧原样保留(loop
  短路弧), dict 条目照常掩码
- test_unmask_yaml_target_items_edge_shapes: targets 还原边角 —— 旧条目非 dict/缺名不进配对表,
  bundle 条目非 dict 跳过, 无名条目 missing 用下标
- test_find_residual_sentinels_shared_containers_dedup: 残留哨兵扫描容器去重(dict/list 两面)
- test_validate_yaml_doc_cleanup_guard_when_tempfile_open_fails: validate_yaml_doc finally
  清理守卫空值弧(369 空值)—— NamedTemporaryFile 打开失败(临时目录不可用)时 tmp_path 保持
  None, 守卫跳过删除且原异常照常传播(issue 26-11-15-1359)
"""
import io
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from auto_qb import __version__
from auto_qb.config import writer as config_writer
from auto_qb.config.writer import (
    MASK_SENTINEL,
    SENSITIVE_KEY_PARTS as _SENSITIVE_PARTS,
    _build_yaml,
    find_residual_sentinels,
    mask_yaml_text,
    unmask_yaml_doc,
)
from auto_qb.core.traffic_source import agent
from auto_qb.webui.server.common import config_backup_path
from auto_qb.webui.server.routes import traffic_monitor as tm_routes
from auto_qb.webui.server.routes.keys import keys_file_path

# 导出夹具配置文本(测试独用 tmp 路径, 与生产 config.yml 无关): 覆盖全部敏感键类别
# (qB 密码 / tracker passkey / hr.token / transfer targets 条目 password+api_key) +
# web.token 留空(自动生成 = 非机密, 不掩码) + 前注/行尾注释/空行(R7 注释保留面) +
# 两段契约负例: targets 条目空 password/api_key(空值不掩码) + 普通列表不下钻
# (path_map 条目内 password 键原样保留 —— 与 mask_tree「不进列表」同口径)。
# **有意非法**(issue 26-11-15-1359 评估留痕: top-level trackers / config.hr.token /
# config.web.path_map 未知键, targets type=local 不在 qb/tr 枚举): 导出/掩码面不过
# load_config —— 掩码按 key-part 匹配任意 YAML, 不校验键面, 非法不影响被测行为; 且
# tracker passkey 在现 schema 无对应键(config.trackers.* 只收 domains/tags/限速等,
# 未知键被 load_config 拒收, 2026-11-15 对照实证), passkey 类别**原理上进不了合法
# 配置** —— 本夹具无法并入导入侧合法基夹具, 两套并存是设计而非欠账。导入侧走
# IMPORT_CONFIG_TEXT(合法 + round-trip byte 形态); 合法配置的掩码还原由
# test_backup_import_same_machine_restores_secrets 端到端覆盖。
BACKUP_CONFIG_TEXT = """\
# 顶部注释: 备份导出夹具
config:
  schema_version: 8
  # qB 凭据(敏感)
  qbittorrent:
    host: 127.0.0.1
    port: 8080
    username: admin
    password: "qb-real-pass"   # 行尾注释
  web:
    token: ""
    skip_check_menu: true
    transfer:
      targets:
        - name: local
          type: local
          base_url: ""
          password: target-secret
          api_key: target-api-key-123
        - name: empty-pass-target
          type: local
          base_url: ""
          password: ""
          api_key: ""
    # 普通列表(非 targets): 掩码不下钻的契约负例
    path_map:
      - password: list-item-pass
        src: a
        dst: b
  hr:
    token: hr-real-token
trackers:
  DemoSite:  # 站点注释
    tags: [demo]
    passkey: tracker-passkey-999
"""

# 夹具里的全部明文凭据(D2: 任一出现在响应即红)。刻意不含 list-item-pass ——
# 普通列表不下钻是既有掩码契约(见 BACKUP_CONFIG_TEXT 注), 该值在掩码测试里断言原样保留
SECRET_PLAINTEXTS = (
    "qb-real-pass",
    "target-secret",
    "target-api-key-123",
    "hr-real-token",
    "tracker-passkey-999",
)

# 重复键坏 YAML(ruamel round-trip loader 抛 DuplicateKeyError; 异常文本回显重复键明文值)
DUP_KEY_CONFIG_TEXT = """\
config:
  schema_version: 8
  qbittorrent:
    host: 127.0.0.1
    port: 8080
    username: admin
    password: "dup-first-pass"
    password: "dup-second-pass"
"""


def _export(mgr, client):
    """带鉴头的导出响应(bundle 测试共用的单行入口)"""
    return client.get("/api/backup/export", headers={"Authorization": f"Bearer {mgr.web.token}"})


def _online_gtm_env(mgr, tmp_path, monkeypatch):
    """探活成功 + 工具密钥就绪的 gtm 环境(在线/回显缺失两类用例共用)"""
    token_file = tmp_path / "gtm" / "monitor.token"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text("tool-token-abc\n", encoding="utf-8")
    monkeypatch.setattr(
        agent,
        "probe",
        lambda timeout=None: agent.ToolEndpoint(
            base_url="http://127.0.0.1:8099",
            token_path=str(token_file),
            data_dir=str(tmp_path / "gtm-data"),
            version="0.1.0",
            pid=4321,
            autostart_registered=True,
            autostart_error=None,
        ),
    )
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: object())


def test_backup_export_requires_auth(web_env):
    """无 Bearer 一律 401(鉴权由 factory 全局 dependencies 单点覆盖, 端点不另挂)"""
    _, client = web_env
    assert client.get("/api/backup/export").status_code == 401


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_bundle_shape_and_masks(web_env):
    """bundle 形状(§03) + 敏感键全掩码 + 全响应无明文凭据(D2)+ 列表不下钻/空值不掩码负例"""
    mgr, client = web_env
    r = _export(mgr, client)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")
    # 可下载 JSON: 文件名 auto-qb-backup-<YYYYMMDD-HHMMSS>.json(Content-Disposition 先例同 .torrent 导出)
    cd = r.headers["content-disposition"]
    assert re.search(r'filename="auto-qb-backup-\d{8}-\d{6}\.json"', cd), cd
    bundle = r.json()
    assert bundle["format"] == "auto-qb-config-bundle"
    assert bundle["bundle_version"] == 1
    assert bundle["app_version"] == __version__
    datetime.fromisoformat(bundle["created_at"])  # 可解析的时间戳(带时区)
    # 敏感键全掩码(含 transfer targets 条目; 与 mask_tree 同一套哨兵)
    tree = yaml.safe_load(bundle["config_yaml"])
    qb = tree["config"]["qbittorrent"]
    web = tree["config"]["web"]
    assert qb["password"] == MASK_SENTINEL
    assert tree["config"]["hr"]["token"] == MASK_SENTINEL
    assert tree["trackers"]["DemoSite"]["passkey"] == MASK_SENTINEL
    targets = web["transfer"]["targets"]
    assert targets[0]["password"] == MASK_SENTINEL
    assert targets[0]["api_key"] == MASK_SENTINEL
    # 空值不掩码(web.token 留空 = 自动生成; targets 条目空 password/api_key 同口径)
    assert web["token"] == ""
    assert targets[1]["password"] == "" and targets[1]["api_key"] == ""
    # 普通列表(非 targets)不下钻: 条目内 password 键原样保留(掩码契约与 mask_tree 同一口径)
    assert web["path_map"][0]["password"] == "list-item-pass"
    # 非敏感键原样
    assert qb["username"] == "admin" and qb["host"] == "127.0.0.1"
    # ui_prefs 服务端零接触(D3): 响应不含该段, 前端并入后再落盘
    assert "ui_prefs" not in bundle
    # 掩码不出机: 整个响应文本(含 headers 不看, body 全量)不含任何明文凭据
    for secret in SECRET_PLAINTEXTS:
        assert secret not in r.text, secret


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_mask_diff_only_sensitive_lines(web_env):
    """R7 byte 级钉: 与 dump(load(原文)) 无掩码基线逐行比对, 差异仅敏感值行 + 注释全保留"""
    mgr, client = web_env
    with open(mgr.config_path, "r", encoding="utf-8") as f:
        raw = f.read()
    # 无掩码基线: 同一 ruamel 实例工厂 load+dump(剔除 ruamel 归一化差异, 基线口径见 mask_yaml_text docstring)
    ry = _build_yaml()
    baseline_buf = io.StringIO()
    ry.dump(ry.load(io.StringIO(raw)), baseline_buf)
    baseline = baseline_buf.getvalue()

    bundle = _export(mgr, client).json()
    masked = bundle["config_yaml"]

    base_lines = baseline.splitlines()
    mask_lines = masked.splitlines()
    assert len(base_lines) == len(mask_lines), "掩码不得增删行"
    for i, (bl, ml) in enumerate(zip(base_lines, mask_lines)):
        if bl == ml:
            continue
        # 差异行必是敏感值行: 掩码侧含哨兵, 基线侧键名含敏感片段
        assert MASK_SENTINEL in ml, f"第 {i + 1} 行非敏感值被改动: {bl!r} -> {ml!r}"
        key = bl.split(":", 1)[0].strip().lower()
        assert any(part in key for part in _SENSITIVE_PARTS), f"第 {i + 1} 行非敏感值被改动: {bl!r} -> {ml!r}"
    # 注释 byte 级保留(前注 / 行尾注释 / 嵌套注释) + 尾换行形态一致
    for note in ("# 顶部注释: 备份导出夹具", "# qB 凭据(敏感)", "# 行尾注释", "# 站点注释"):
        assert note in masked, note
    assert masked.endswith("\n") == baseline.endswith("\n")


@pytest.mark.parametrize("web_env", [{"config_text": DUP_KEY_CONFIG_TEXT}], indirect=True)
def test_backup_export_mask_failure_500_no_secret_echo(web_env):
    """重复键坏 YAML(DuplicateKeyError) -> 500, 响应不含异常文本回显的明文凭据(D2)"""
    mgr, client = web_env
    r = _export(mgr, client)
    assert r.status_code == 500
    assert "掩码化失败" in r.text
    # 异常文本会逐字回显重复键的明文值 —— detail 进响应 = 泄敏, 两个明文凭据都不得出现
    for secret in ("dup-first-pass", "dup-second-pass"):
        assert secret not in r.text, secret


def test_mask_yaml_text_non_mapping_returns_empty():
    """mask_yaml_text 直调: 空串/列表/标量文档一律返回 ""(非映射当空, 堵明文旁路)"""
    from auto_qb.config.writer import mask_yaml_text

    assert mask_yaml_text("") == ""
    assert mask_yaml_text("- a\n- b\n") == ""
    assert mask_yaml_text("just-a-scalar\n") == ""


def test_backup_export_gtm_offline_section_null(web_env, monkeypatch):
    """工具离线(agent 探活 None) -> bundle["gtm"] is None, 其余段照常导出(D9 离线不致命)"""
    mgr, client = web_env
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: None)
    r = _export(mgr, client)
    assert r.status_code == 200, r.text
    bundle = r.json()
    assert bundle["gtm"] is None
    assert bundle["config_yaml"] != ""
    assert bundle["webui_keys"]["schema_version"] == 1


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_missing_config_file_empty_section(web_env, monkeypatch):
    """config.yml 不存在 -> config_yaml 段空串, 其余段照常导出(不致命)"""
    mgr, client = web_env
    Path(mgr.config_path).unlink()
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: None)
    r = _export(mgr, client)
    assert r.status_code == 200, r.text
    bundle = r.json()
    assert bundle["config_yaml"] == ""
    assert bundle["format"] == "auto-qb-config-bundle"
    assert bundle["webui_keys"]["schema_version"] == 1
    assert bundle["gtm"] is None


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_mask_exception_wrapped_500(web_env, monkeypatch):
    """掩码化抛异常 -> 500, detail 含「掩码化失败」+ 类型名, 不含异常文本(泄敏面同 500 收口)"""
    mgr, client = web_env

    def boom(text):
        raise RuntimeError("leak-exception-text")

    monkeypatch.setattr(config_writer, "mask_yaml_text", boom)  # 端点内延迟导入, 调用时现取属性
    r = _export(mgr, client)
    assert r.status_code == 500
    assert "掩码化失败" in r.text
    assert "RuntimeError" in r.text
    assert "leak-exception-text" not in r.text


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_gtm_online_section(web_env, tmp_path, monkeypatch):
    """工具在线 -> gtm 段 = {config 合并树, tool_version, captured_at}(与 /api/traffic/monitor/status 同源)"""
    mgr, client = web_env
    _online_gtm_env(mgr, tmp_path, monkeypatch)
    tool_config = {"sample_interval": 5.0, "http_host": "127.0.0.1", "http_port": 8099}
    monkeypatch.setattr(tm_routes, "_call_tool", lambda *a, **k: (200, {"ok": True, "config": tool_config}))
    bundle = _export(mgr, client).json()
    assert bundle["gtm"]["config"] == tool_config
    assert bundle["gtm"]["tool_version"] == "0.1.0"
    datetime.fromisoformat(bundle["gtm"]["captured_at"])


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_gtm_echo_not_dict_null(web_env, tmp_path, monkeypatch):
    """探活成功但 /status 回显非 200 / ToolUnreachable 竞态 -> gtm 段 None 且整体 200(D9 不致命)"""
    mgr, client = web_env
    _online_gtm_env(mgr, tmp_path, monkeypatch)
    # 分支一: 工具 /status 回非 200(如密钥不符) -> reachable 但 status=None -> gtm 段 None
    monkeypatch.setattr(tm_routes, "_call_tool", lambda *a, **k: (401, {"error": "invalid token"}))
    r = _export(mgr, client)
    assert r.status_code == 200, r.text
    assert r.json()["gtm"] is None
    assert r.json()["config_yaml"] != ""

    # 分支二: 探活与 /status 之间工具掉线(ToolUnreachable) -> 展示面降级 -> gtm 段 None
    def boom(*a, **k):
        raise tm_routes.ToolUnreachable("connection refused")

    monkeypatch.setattr(tm_routes, "_call_tool", boom)
    r2 = _export(mgr, client)
    assert r2.status_code == 200, r2.text
    assert r2.json()["gtm"] is None


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_keys_section_matches_get_api_keys(web_env):
    """webui_keys 段形状与 GET /api/keys 逐字一致(同走 load_keys_doc 单点)"""
    mgr, client = web_env
    doc = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "Ctrl+KeyP"}}
    assert client.put("/api/keys", headers={"Authorization": f"Bearer {mgr.web.token}"}, json=doc).status_code == 200
    keys_doc = client.get("/api/keys", headers={"Authorization": f"Bearer {mgr.web.token}"}).json()
    bundle = _export(mgr, client).json()
    assert bundle["webui_keys"] == keys_doc
    assert json.loads(json.dumps(bundle["webui_keys"])) == doc


# ---------------------------------------------------------------------------
# S2: POST /api/backup/import(计划 26-11-14-0624; 测试矩阵见模块 docstring)
# ---------------------------------------------------------------------------

# 导入侧夹具(测试独用 tmp 路径): 与 BACKUP_CONFIG_TEXT 的差异 —— 本夹具**必须过 load_config
# 全量校验**(导入管线走聚合校验), 因此段名/键名都在 schema 键面内: 敏感键用 config.qbittorrent
# .password / config.web.transfer.targets 条目 password+api_key / config.hr_check.channel.token;
# data_dir(readonly 程序托管字段)供回退断言。书写形态与 _build_yaml 的 round-trip 输出
# byte 级一致(mapping 4 空格 + sequence offset 2), 供「落盘内容 = bundle 原文」byte 断言。
IMPORT_CONFIG_TEXT = """\
# 顶部注释: 导入测试夹具
config:
    schema_version: 8
    # qB 凭据(敏感)
    qbittorrent:
        host: 127.0.0.1
        port: 8080
        username: admin
        password: "qb-real-pass"   # 行尾注释
    data_dir: "C:/local/data"
    web:
        token: ""
        skip_check_menu: true
        transfer:
            targets:
              - name: local
                type: qb
                base_url: "http://127.0.0.1:8081"
                password: target-secret
                api_key: target-api-key-123
              - name: empty-pass-target
                type: qb
                base_url: ""
                password: ""
                api_key: ""
    # 站点段(无敏感键)
    trackers:
        DemoSite:  # 站点注释
            tags: [demo]
            domains: [d.com]
    hr_check:
        channel:
            token: hr-real-token
"""

# 跨机导入的「本机」夹具: 只带 qB 凭据的极简合法配置 —— bundle 里 targets / hr_check 的哨兵
# 在本机无对应键(R1 不可 resolve 面), qbittorrent.password 可 resolve(本机有对应键)
CROSS_MACHINE_LOCAL_TEXT = """\
config:
    schema_version: 8
    qbittorrent:
        host: 127.0.0.1
        port: 8080
        username: admin
        password: local-only-pass
"""


def _import(mgr, client, payload):
    """带鉴头的导入响应(导入测试共用的单行入口)"""
    return client.post("/api/backup/import", headers={"Authorization": f"Bearer {mgr.web.token}"}, json=payload)


def _read_disk(mgr) -> str:
    with open(mgr.config_path, "r", encoding="utf-8") as f:
        return f.read()


def _keys_payload(mgr, client) -> dict:
    """取一份合法 webui_keys 段(经 GET /api/keys 同源形状)"""
    return client.get("/api/keys", headers={"Authorization": f"Bearer {mgr.web.token}"}).json()


def test_backup_import_requires_auth(web_env):
    """无 Bearer 一律 401(鉴权由 factory 全局 dependencies 单点覆盖, 端点不另挂)"""
    _, client = web_env
    assert client.post("/api/backup/import", json={"sections": {}}).status_code == 401


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_same_machine_restores_secrets(web_env):
    """同机掩码还原: 导出 bundle 原样导回 -> 写盘值=本机现值非哨兵, 哨兵字面量绝不落盘(R7 注释保留)"""
    mgr, client = web_env
    before = _read_disk(mgr)
    bundle = _export(mgr, client).json()
    r = _import(
        mgr, client, {
            "bundle_version": bundle["bundle_version"],
            "sections": {
                "config_yaml": bundle["config_yaml"]
            }
        }
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == ["config_yaml"]
    assert data["skipped"] == [] and data["warnings"] == []
    disk = _read_disk(mgr)
    assert MASK_SENTINEL not in disk  # 「********」字面量绝不落盘(fail-fast)
    # 落盘内容 = bundle 掩码 resolve 后的原文(byte 级: 夹具书写形态 = round-trip 输出形态)
    assert disk == IMPORT_CONFIG_TEXT
    tree = yaml.load(disk, Loader=yaml.BaseLoader)
    # 敏感键全部还原为本机现值(非哨兵)
    assert tree["config"]["qbittorrent"]["password"] == "qb-real-pass"
    targets = tree["config"]["web"]["transfer"]["targets"]
    assert targets[0]["password"] == "target-secret"
    assert targets[0]["api_key"] == "target-api-key-123"
    assert tree["config"]["hr_check"]["channel"]["token"] == "hr-real-token"
    # 注释 byte 级随 round-trip 保留(R7)
    for note in ("# 顶部注释: 导入测试夹具", "# 行尾注释", "# 站点注释"):
        assert note in disk, note
    # .bak 链验收(评审): 存在且内容 = 导入前磁盘原文
    bak = config_backup_path(mgr)
    assert os.path.exists(bak)
    with open(bak, "r", encoding="utf-8") as f:
        assert f.read() == before
    # reload_config 已投递主循环(黄金法则 5: 热重载归主循环线程)
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "reload_config" and "config" in payload


@pytest.mark.parametrize("web_env", [{"config_text": CROSS_MACHINE_LOCAL_TEXT}], indirect=True)
def test_backup_import_unresolvable_sentinels_422_aggregated(web_env):
    """跨机不可 resolve(R1): 聚合 422 逐路径列出, 可 resolve 键不报, 磁盘一字未动"""
    mgr, client = web_env
    bundle_yaml = mask_yaml_text(IMPORT_CONFIG_TEXT)
    before = _read_disk(mgr)
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": bundle_yaml}})
    assert r.status_code == 422
    detail = r.json()["detail"]
    # 逐路径列出: 本机无对应键的哨兵条目全部在列
    for path in (
        "config.hr_check.channel.token",
        "config.web.transfer.targets[local].password",
        "config.web.transfer.targets[local].api_key",
    ):
        assert path in detail, path
    # 本机有对应键的哨兵(qbittorrent.password)不在报错里(可 resolve, 不算错)
    assert "config.qbittorrent.password" not in detail
    # 整体拒: 磁盘一字未动(绝不把哨兵字面量写盘)
    assert _read_disk(mgr) == before
    assert MASK_SENTINEL not in before


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_readonly_fallback(web_env):
    """readonly(程序托管)字段回退: bundle 的 data_dir 不落盘, 恢复为本机磁盘旧值"""
    mgr, client = web_env
    bundle_yaml = mask_yaml_text(
        IMPORT_CONFIG_TEXT.replace('data_dir: "C:/local/data"', 'data_dir: "C:/old-machine/data"')
    )
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": bundle_yaml}})
    assert r.status_code == 200, r.text
    assert r.json()["applied"] == ["config_yaml"]
    disk = _read_disk(mgr)
    tree = yaml.load(disk, Loader=yaml.BaseLoader)
    assert tree["config"]["data_dir"] == "C:/local/data"  # 回退为本机旧值
    assert "C:/old-machine/data" not in disk


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_rejects_newer_versions(web_env):
    """bundle_version / config schema_version 高于本机 -> 422 拒(R2), 磁盘一字未动"""
    mgr, client = web_env
    before = _read_disk(mgr)
    # 闸一: bundle_version 高于本机 -> 拒并提示先升级
    r = _import(mgr, client, {"bundle_version": 2, "sections": {"gtm": None}})
    assert r.status_code == 422, r.text
    assert "升级" in r.json()["detail"]
    # 闸二: config schema_version 高于当前程序 -> 拒
    newer = mask_yaml_text(IMPORT_CONFIG_TEXT.replace("schema_version: 8", "schema_version: 9"))
    r2 = _import(mgr, client, {"sections": {"config_yaml": newer}})
    assert r2.status_code == 422
    assert "高于本程序支持" in r2.json()["detail"]
    # 两道闸都未触碰磁盘
    assert _read_disk(mgr) == before


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_older_bundle_writes_as_is(web_env):
    """旧版本 bundle(v7)原样落盘+reload(R2): 版本章不盖当前值, 迁移靠下次启动 materialize 链"""
    mgr, client = web_env
    older = IMPORT_CONFIG_TEXT.replace("schema_version: 8", "schema_version: 7")
    bundle_yaml = mask_yaml_text(older)
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": bundle_yaml}})
    assert r.status_code == 200, r.text
    assert r.json()["applied"] == ["config_yaml"]
    disk = _read_disk(mgr)
    # 原样落盘: 内容 byte 级 = bundle 掩码 resolve 后原文(版本章保持 bundle 原值)
    assert disk == older
    assert "schema_version: 7" in disk and "schema_version: 8" not in disk
    assert MASK_SENTINEL not in disk
    # reload_config 已投递(loaders 内存迁移: load_config 链内归一, 磁盘终态靠下次启动)
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "reload_config"
    # 内存迁移生效证据(评审): reload 载荷 = load_config(v7 磁盘) 的迁移产物 —— Config 模型不
    # 携带版本键(版本闸在 load_config/detect_version 内部), 载荷正常产出即迁移链跑通
    assert payload["config"] is not None


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_unknown_section_ignored_with_warning(web_env):
    """未知顶层 section 忽略 + warnings(向前兼容); 已知段照常应用"""
    mgr, client = web_env
    bundle = _export(mgr, client).json()
    r = _import(
        mgr, client, {"sections": {
            "config_yaml": bundle["config_yaml"],
            "future_face": {
                "x": 1
            },
            "new_thing": 3
        }}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == ["config_yaml"]
    joined = "\n".join(data["warnings"])
    assert "未知 section" in joined and "future_face" in joined and "new_thing" in joined
    assert _read_disk(mgr) == IMPORT_CONFIG_TEXT


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_request_shape_400(web_env):
    """请求 shape: sections 缺失/无已知段/bundle_version 非整数 -> 400"""
    mgr, client = web_env
    assert _import(mgr, client, {}).status_code == 400
    assert _import(mgr, client, {"sections": {}}).status_code == 400
    assert _import(mgr, client, {"sections": {"unknown_only": 1}}).status_code == 400
    assert _import(mgr, client, {"bundle_version": "2", "sections": {"gtm": None}}).status_code == 400
    assert _import(mgr, client, {"bundle_version": True, "sections": {"gtm": None}}).status_code == 400


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_invalid_keys_422_no_half_apply(web_env):
    """keys 结构非法 -> 422 整体拒: config 不半应用(磁盘一字未动), keys 文件未创建"""
    mgr, client = web_env
    bundle = _export(mgr, client).json()
    bad_keys = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "not-a-serial!"}}
    r = _import(
        mgr, client, {
            "bundle_version": 1,
            "sections": {
                "config_yaml": bundle["config_yaml"],
                "webui_keys": bad_keys
            }
        }
    )
    assert r.status_code == 422
    assert "webui_keys" in r.json()["detail"]
    assert _read_disk(mgr) == IMPORT_CONFIG_TEXT  # 不半应用
    assert not os.path.exists(keys_file_path(mgr))


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_empty_config_yaml_skipped(web_env):
    """config_yaml 空串段 -> skip + warnings(不致命), 同请求的 webui_keys 照常应用"""
    mgr, client = web_env
    keys_doc = _keys_payload(mgr, client)
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": "", "webui_keys": keys_doc}})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == ["webui_keys"]
    assert [s["section"] for s in data["skipped"]] == ["config_yaml"]
    assert data["warnings"], "空段要有 warnings"
    assert _read_disk(mgr) == IMPORT_CONFIG_TEXT
    assert os.path.exists(keys_file_path(mgr))


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_partial_sections_only_selected_applied(web_env):
    """部分段勾选: 只勾 webui_keys -> config 磁盘未动且不投递 reload, keys 应用"""
    mgr, client = web_env
    keys_doc = dict(_keys_payload(mgr, client), overrides={"act-pause": "Ctrl+KeyP"})
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"webui_keys": keys_doc}})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == ["webui_keys"]
    assert data["skipped"] == [] and data["warnings"] == []
    assert _read_disk(mgr) == IMPORT_CONFIG_TEXT  # 未勾选的 config 段未动
    assert mgr.web.commands.qsize() == 0  # config 未应用 -> 无 reload 投递
    assert json.loads(open(keys_file_path(mgr), encoding="utf-8").read())["overrides"] == {"act-pause": "Ctrl+KeyP"}


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_gtm_offline_skipped_not_fatal(web_env, monkeypatch):
    """gtm 离线(D9): 段为 null 或工具未就绪均 skipped + 原因, 不致命不阻断 config 应用"""
    mgr, client = web_env
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: None)
    bundle = _export(mgr, client).json()
    # 分支一: bundle gtm 段为 null(离线导出) -> 按缺面跳过
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": bundle["config_yaml"], "gtm": None}})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == ["config_yaml"]
    assert [s["section"] for s in data["skipped"]] == ["gtm"] and data["skipped"][0]["reason"]
    # 分支二: 勾了 gtm 且段带 config, 但工具未就绪 -> skipped + 原因, config 照常应用
    r2 = _import(
        mgr,
        client,
        {
            "bundle_version": 1,
            "sections": {
                "config_yaml": bundle["config_yaml"],
                "gtm": {
                    "config": {
                        "sample_interval": 5.0
                    }
                }
            }
        },
    )
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    assert data2["applied"] == ["config_yaml"]
    assert [s["section"] for s in data2["skipped"]] == ["gtm"] and data2["skipped"][0]["reason"]
    assert _read_disk(mgr) == IMPORT_CONFIG_TEXT


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_gtm_online_applied(web_env, tmp_path, monkeypatch):
    """工具在线 -> gtm 走 PUT /config 代理应用; 捕获入参断言只转发 config 键(信封键不入载荷)"""
    mgr, client = web_env
    _online_gtm_env(mgr, tmp_path, monkeypatch)
    tool_config = {"sample_interval": 5.0, "http_host": "127.0.0.1", "http_port": 8099}
    captured = {}

    def fake_call_tool(base_url, path, method, token, payload=None):
        captured.update(url=base_url, path=path, method=method, payload=payload)
        return 200, {"ok": True}

    monkeypatch.setattr(tm_routes, "_call_tool", fake_call_tool)
    bundle = _export(mgr, client).json()
    gtm_section = {
        "config": tool_config,
        "tool_version": "0.1.0",
        "captured_at": "2026-11-14T12:00:00+08:00",
        "unknown_envelope_key": 1,
    }
    r = _import(
        mgr, client, {
            "bundle_version": 1,
            "sections": {
                "config_yaml": bundle["config_yaml"],
                "gtm": gtm_section
            }
        }
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == ["config_yaml", "gtm"]
    assert data["skipped"] == [] and data["warnings"] == []
    # 转发载荷 = 恰好 bundle 的 config 键(评审 fix2: 回归转发整个信封在此必红)
    assert (captured["path"], captured["method"]) == ("/config", "PUT")
    assert captured["payload"] == tool_config


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_gtm_tool_400_into_warnings(web_env, tmp_path, monkeypatch):
    """工具 400 校验错透传进 warnings(R3): gtm 段不应用, 不阻断 config 应用"""
    mgr, client = web_env
    _online_gtm_env(mgr, tmp_path, monkeypatch)
    monkeypatch.setattr(
        tm_routes, "_call_tool", lambda *a, **k: (400, {
            "errors": ["unknown key: foo", "bad value: bar"]
        })
    )
    bundle = _export(mgr, client).json()
    r = _import(
        mgr, client, {
            "bundle_version": 1,
            "sections": {
                "config_yaml": bundle["config_yaml"],
                "gtm": {
                    "config": {
                        "foo": 1
                    }
                }
            }
        }
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == ["config_yaml"]
    assert [s["section"] for s in data["skipped"]] == ["gtm"]
    joined = "\n".join(data["warnings"])
    assert "400" in joined and "unknown key: foo" in joined and "bad value: bar" in joined
    assert _read_disk(mgr) == IMPORT_CONFIG_TEXT  # config 不被 gtm 失败阻断


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_idempotent(web_env):
    """幂等(黄金法则 1): 同一 bundle 导入两次, config/keys 终态一致"""
    mgr, client = web_env
    bundle = _export(mgr, client).json()
    payload = {
        "bundle_version": bundle["bundle_version"],
        "sections": {
            "config_yaml": bundle["config_yaml"],
            "webui_keys": bundle["webui_keys"]
        },
    }
    r1 = _import(mgr, client, payload)
    assert r1.status_code == 200, r1.text
    disk1 = _read_disk(mgr)
    keys1 = open(keys_file_path(mgr), encoding="utf-8").read()
    r2 = _import(mgr, client, payload)
    assert r2.status_code == 200, r2.text
    assert r2.json()["applied"] == r1.json()["applied"] == ["config_yaml", "webui_keys"]
    assert _read_disk(mgr) == disk1 == IMPORT_CONFIG_TEXT
    assert open(keys_file_path(mgr), encoding="utf-8").read() == keys1


# ---------------------------------------------------------------------------
# 评审修复回归(26-11-15 三面评审 13 条)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_root_non_mapping_422(web_env):
    """根非映射(列表/标量文档)-> 422「不是映射文档」, 磁盘未动"""
    mgr, client = web_env
    before = _read_disk(mgr)
    for text in ("- a\n", "42\n"):
        r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": text}})
        assert r.status_code == 422, (text, r.text)
        assert "不是映射文档" in r.json()["detail"]
    assert _read_disk(mgr) == before


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_empty_config_section_422(web_env):
    """根映射但 config 段缺失/空映射 -> 422(major: 防一次 200 导入静默重置生产配置), 磁盘未动"""
    mgr, client = web_env
    before = _read_disk(mgr)
    for text in ("{}\n", "config: {}\n", "config:\n", "other: 1\n"):
        r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": text}})
        assert r.status_code == 422, (text, r.text)
        assert "缺 config" in r.json()["detail"]
    assert _read_disk(mgr) == before


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_residual_sentinel_422(web_env):
    """R1 旁路兜底: 手编 bundle 在 unmask 不下钻的普通列表位放哨兵 -> 写盘前兜底闸 422 逐路径

    掩码/还原两侧对非 targets 列表都不下钻(delete_tags 等字符串列表项掩码侧原样), 导出 bundle
    不会有该形态 —— 手造哨兵项若不拦会原样落盘(fail-fast 红线)。"""
    mgr, client = web_env
    crafted = (
        "config:\n"
        "    schema_version: 8\n"
        "    delete_tags:\n"
        "        - '********'\n"
        "    qbittorrent:\n"
        "        host: 127.0.0.1\n"
        "        port: 8080\n"
        "        username: admin\n"
        "        password: plain-pass\n"
    )
    # 直测单点: 兜底扫描能看到列表位哨兵(unmask 侧不下钻, 两闸互补)
    doc = _build_yaml().load(io.StringIO(crafted))
    assert find_residual_sentinels(doc) == ["config.delete_tags[0]"]
    before = _read_disk(mgr)
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": crafted}})
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert "掩码哨兵" in detail and "config.delete_tags[0]" in detail
    assert _read_disk(mgr) == before


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_gtm_tool_400_nondict_payload(web_env, tmp_path, monkeypatch):
    """工具 400 回非 dict JSON(契约漂移)-> error_text 兜底 str 化进 warnings, 不 500"""
    mgr, client = web_env
    _online_gtm_env(mgr, tmp_path, monkeypatch)
    monkeypatch.setattr(tm_routes, "_call_tool", lambda *a, **k: (400, ["not-a-dict"]))
    bundle = _export(mgr, client).json()
    r = _import(
        mgr,
        client,
        {
            "bundle_version": 1,
            "sections": {
                "config_yaml": bundle["config_yaml"],
                "gtm": {
                    "config": {
                        "foo": 1
                    }
                }
            }
        },
    )
    assert r.status_code == 200, r.text  # 不被打成 500(gtm 失败不阻断契约)
    data = r.json()
    assert data["applied"] == ["config_yaml"]
    assert [s["section"] for s in data["skipped"]] == ["gtm"]
    assert any("400" in w and "not-a-dict" in w for w in data["warnings"])


@pytest.mark.parametrize("web_env", [{"config_text": CROSS_MACHINE_LOCAL_TEXT}], indirect=True)
def test_backup_import_readonly_delete_branch(web_env):
    """readonly 回退删除分支: 本机 config 无该键而 bundle 带 -> 导入后该键消失(走 schema 默认)"""
    mgr, client = web_env
    bundle_yaml = mask_yaml_text(
        "config:\n"
        "    schema_version: 8\n"
        "    data_dir: \"C:/other/machine\"\n"
        "    qbittorrent:\n"
        "        host: 127.0.0.1\n"
        "        port: 8080\n"
        "        username: admin\n"
        "        password: local-only-pass\n"
    )
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": bundle_yaml}})
    assert r.status_code == 200, r.text
    assert r.json()["applied"] == ["config_yaml"]
    disk = _read_disk(mgr)
    assert "data_dir" not in disk  # 本机无旧值 -> 删除该键(走 schema 默认)
    assert "C:/other/machine" not in disk


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_holds_write_lock(web_env, monkeypatch):
    """R8 证据: 导入路径(resolve/写盘)与 write_tree 共用 writer._WRITE_LOCK 同一单点(录制锁)"""
    from auto_qb.config import writer as cw

    events = []

    class RecordingLock:
        def __enter__(self):
            events.append("acquire")
            return self

        def __exit__(self, *exc):
            events.append("release")
            return False

    monkeypatch.setattr(cw, "_WRITE_LOCK", RecordingLock())  # commit/写盘以模块属性引用该单点
    mgr, client = web_env
    bundle = _export(mgr, client).json()
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": bundle["config_yaml"]}})
    assert r.status_code == 200, r.text
    assert events.count("acquire") >= 1
    assert events.count("acquire") == events.count("release")


@pytest.mark.parametrize(
    "old_value,resolved",
    [
        ("", None),  # 空串旧值 = 不可 resolve(本机未设置, 没有现值可回填, 不猜)
        ("real-secret", "real-secret"),
        (42, 42),  # 数字旧值原样回填
        (True, True),  # 布尔旧值原样回填
        (MASK_SENTINEL, None),  # 旧值本身是哨兵 = 不可 resolve(导入侧没有「保持」余地)
    ],
)
def test_unmask_yaml_doc_old_value_table(old_value, resolved):
    """unmask_yaml_doc 旧值形态表驱动: 空串/哨兵旧值 -> missing; 数字/布尔/串原样回填"""
    ry = _build_yaml()
    doc = ry.load(io.StringIO("config:\n    k: '********'\n"))
    missing = unmask_yaml_doc(doc, {"config": {"k": old_value}})
    if resolved is None:
        assert missing == ["config.k"]
    else:
        assert missing == []
        assert doc["config"]["k"] == resolved


@pytest.mark.parametrize("old_value,resolved", [("", None), ("real-target-pass", "real-target-pass")])
def test_unmask_yaml_doc_target_items_old_value(old_value, resolved):
    """targets 路径同口径直测(fix5: _unmask_yaml_target_items 与顶层分支对齐)—— 空串旧值 ->
    missing(本机该条目未设置现值, 不猜); 正常值按 name 配对回填"""
    ry = _build_yaml()
    target_yaml = (
        "config:\n"
        "    web:\n"
        "        transfer:\n"
        "            targets:\n"
        "              - name: t1\n"
        "                type: qb\n"
        "                base_url: \"\"\n"
        "                password: '********'\n"
    )
    doc = ry.load(io.StringIO(target_yaml))
    old_doc = {
        "config":
            {
                "web": {
                    "transfer": {
                        "targets": [{
                            "name": "t1",
                            "type": "qb",
                            "base_url": "",
                            "password": old_value
                        }]
                    }
                }
            }
    }
    missing = unmask_yaml_doc(doc, old_doc)
    if resolved is None:
        assert missing == ["config.web.transfer.targets[t1].password"]
    else:
        assert missing == []
        assert doc["config"]["web"]["transfer"]["targets"][0]["password"] == resolved


def test_unmask_yaml_doc_no_local_doc_all_missing():
    """本机无配置文件(old_doc=None)-> 任何哨兵都不可 resolve(R1 跨机首装面)"""
    doc = _build_yaml().load(io.StringIO("config:\n    k: '********'\n"))
    assert unmask_yaml_doc(doc, None) == ["config.k"]


# ---------------------------------------------------------------------------
# 覆盖率闸回绿(26-11-15): S1-S4 评审轮防御闸门分支补测(以 test.full 逐行报告为准)
# ---------------------------------------------------------------------------

# YAML anchor/alias 夹具: 同一容器对象被引用两次(ruamel round-trip loader load 后是共享引用)
ALIAS_CONFIG_TEXT = """\
config: &c
    schema_version: 8
    qbittorrent:
        host: 127.0.0.1
        port: 8080
        username: admin
        password: ""
same: *c
"""


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_alias_shared_reference_422(web_env):
    """alias 共享引用闸: config_yaml 含 anchor/alias(容器被引用两次)-> 422 拒, 磁盘未动"""
    from auto_qb.webui.server.routes import backup as backup_routes

    mgr, client = web_env
    before = _read_disk(mgr)
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": ALIAS_CONFIG_TEXT}})
    assert r.status_code == 422, r.text
    assert "anchor/alias" in r.json()["detail"]
    assert _read_disk(mgr) == before
    # 直测单点: 共享容器(挂哨兵与否)一律 False; 无共享引用的文档 True
    shared = {"k": MASK_SENTINEL}
    errs = []
    assert backup_routes._scan_yaml_doc_shape({"a": shared, "b": shared}, errs) is False
    assert "anchor/alias" in errs[0]
    assert backup_routes._scan_yaml_doc_shape({"a": {"k": 1}, "b": [1, 2]}, []) is True


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_depth_gate_422(web_env, monkeypatch):
    """深度上限闸: 嵌套超限 -> 422(小阈值注入测闸门分支, 不造真深文档拖慢用例)"""
    from auto_qb.webui.server.routes import backup as backup_routes

    monkeypatch.setattr(backup_routes, "_MAX_YAML_DOC_DEPTH", 2)
    mgr, client = web_env
    before = _read_disk(mgr)
    deep = "config:\n    a:\n        b:\n            c: 1\n"
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": deep}})
    assert r.status_code == 422, r.text
    assert "嵌套超过 2 层" in r.json()["detail"]
    assert _read_disk(mgr) == before


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_node_count_gate_422(web_env, monkeypatch):
    """节点数上限闸: 文档节点数超限 -> 422(小阈值注入; 节点计数只算值/容器, 不算映射键)"""
    from auto_qb.webui.server.routes import backup as backup_routes

    monkeypatch.setattr(backup_routes, "_MAX_YAML_DOC_NODES", 3)
    mgr, client = web_env
    before = _read_disk(mgr)
    # root + config 段 + 2 个标量值 = 4 节点 > 3
    big = "config:\n    a: 1\n    b: 2\n"
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": big}})
    assert r.status_code == 422, r.text
    assert "节点数超过 3" in r.json()["detail"]
    assert _read_disk(mgr) == before


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_text_length_gate_422(web_env):
    """文本 1MiB 长度上限闸: 解析前拒(不耗解析时间), 磁盘未动"""
    from auto_qb.webui.server.routes import backup as backup_routes

    mgr, client = web_env
    before = _read_disk(mgr)
    long_text = "a" * (backup_routes._MAX_BUNDLE_YAML_CHARS + 1)
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": long_text}})
    assert r.status_code == 422, r.text
    assert "文本超长" in r.json()["detail"]
    assert _read_disk(mgr) == before


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_parse_recursion_422(web_env):
    """解析期 RecursionError -> 422「解析递归溢出」(flow 深嵌套小文本, 不造 1MiB 级文档)"""
    mgr, client = web_env
    before = _read_disk(mgr)
    deep_flow = "config: " + "[" * 300 + "]" * 300 + "\n"
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": deep_flow}})
    assert r.status_code == 422, r.text
    assert "递归溢出" in r.json()["detail"]
    assert _read_disk(mgr) == before


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_parse_failure_500_no_secret_echo(web_env):
    """bundle YAML 解析失败(重复键)-> 500 只留类型名; 异常文本回显的明文值不进响应(D2)"""
    mgr, client = web_env
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": DUP_KEY_CONFIG_TEXT}})
    assert r.status_code == 500
    detail = r.json()["detail"]
    assert "解析失败" in detail and "DuplicateKeyError" in detail
    for secret in ("dup-first-pass", "dup-second-pass"):
        assert secret not in r.text, secret


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_body_non_dict_400(web_env):
    """body 非 dict -> 400「body 必须是对象」(TestClient JSON 非 dict 被 FastAPI 先拦成 422,
    防御闸只能端点直调注入)"""
    from fastapi import HTTPException as _HTTPException

    mgr, client = web_env
    # factory 把各路由包进 _IncludedRouter, 原始 APIRoute 在 original_router.routes 里
    route = None
    for included in client.app.routes:
        for sub in getattr(getattr(included, "original_router", None), "routes", []):
            if getattr(sub, "path", None) == "/api/backup/import":
                route = sub
    assert route is not None
    with pytest.raises(_HTTPException) as ei:
        route.endpoint(["not-a-dict"])
    assert ei.value.status_code == 400
    assert "body 必须是对象" in ei.value.detail


@pytest.mark.parametrize("web_env", [{"config_text": DUP_KEY_CONFIG_TEXT}], indirect=True)
def test_backup_import_local_config_broken_commit_500(web_env):
    """本机 config.yml 坏 YAML -> 提交路径现读炸(锁内 R8)-> 500 只留类型名, 明文不回显(D2)"""
    mgr, client = web_env
    bundle_yaml = mask_yaml_text(IMPORT_CONFIG_TEXT)
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": bundle_yaml}})
    assert r.status_code == 500
    detail = r.json()["detail"]
    assert "本机配置文件解析失败" in detail and "DuplicateKeyError" in detail
    for secret in ("dup-first-pass", "dup-second-pass"):
        assert secret not in r.text, secret


@pytest.mark.parametrize("web_env", [{"config_text": DUP_KEY_CONFIG_TEXT}], indirect=True)
def test_backup_import_precheck_local_broken_500(web_env):
    """keys 已有错时锁内先验也撞本机坏 YAML -> 500(聚合面), 明文不回显(D2, 与提交路径同款)"""
    mgr, client = web_env
    bundle_yaml = mask_yaml_text(IMPORT_CONFIG_TEXT)
    bad_keys = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "not-a-serial!"}}
    r = _import(mgr, client, {"sections": {"config_yaml": bundle_yaml, "webui_keys": bad_keys}})
    assert r.status_code == 500
    assert "本机配置文件解析失败" in r.json()["detail"]
    for secret in ("dup-first-pass", "dup-second-pass"):
        assert secret not in r.text, secret


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_precheck_config_error_aggregated(web_env):
    """config 侧 load_config 校验失败 + keys 侧结构非法 -> 同一 422 聚合两侧错误(先验面)"""
    mgr, client = web_env
    bad_cfg = (
        "config:\n"
        "    schema_version: 8\n"
        "    qbittorrent:\n"
        "        host: 127.0.0.1\n"
        "        port: not-a-port\n"
        "        username: admin\n"
        "        password: \"\"\n"
    )
    bad_keys = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "not-a-serial!"}}
    before = _read_disk(mgr)
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": bad_cfg, "webui_keys": bad_keys}})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "config_yaml" in detail and "webui_keys" in detail
    assert "必须是整数" in detail
    assert _read_disk(mgr) == before


@pytest.mark.parametrize("web_env", [{"config_text": CROSS_MACHINE_LOCAL_TEXT}], indirect=True)
def test_backup_import_precheck_missing_aggregated(web_env):
    """keys 已有错 + config 有不可 resolve 哨兵 -> 同一 422 同时含 R1 逐路径与 keys 错"""
    mgr, client = web_env
    bundle_yaml = mask_yaml_text(IMPORT_CONFIG_TEXT)
    bad_keys = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "not-a-serial!"}}
    before = _read_disk(mgr)
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": bundle_yaml, "webui_keys": bad_keys}})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "掩码值无法还原" in detail and "共 3 处" in detail
    assert "config.hr_check.channel.token" in detail
    assert "webui_keys" in detail
    assert _read_disk(mgr) == before


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_no_local_config_all_sentinels_missing(web_env):
    """本机无 config.yml -> 提交路径 old_doc=None, 全部哨兵不可 resolve(R1 跨机首装面, 端点级)"""
    mgr, client = web_env
    Path(mgr.config_path).unlink()
    bundle_yaml = mask_yaml_text(IMPORT_CONFIG_TEXT)
    r = _import(mgr, client, {"bundle_version": 1, "sections": {"config_yaml": bundle_yaml}})
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert "共 4 处" in detail
    for path in (
        "config.qbittorrent.password",
        "config.hr_check.channel.token",
        "config.web.transfer.targets[local].password",
        "config.web.transfer.targets[local].api_key",
    ):
        assert path in detail, path
    assert not Path(mgr.config_path).exists()  # 未写盘


def _online_gtm_two_phase(monkeypatch, put_result):
    """/status 探活在线(200)+ PUT /config 返回 put_result 的两段替身(写路径分支共用)"""
    def fake_call_tool(base_url, path, method, token, payload=None):
        if path == "/status":
            return 200, {"ok": True, "config": {}}
        assert path == "/config" and method == "PUT"
        return put_result()

    monkeypatch.setattr(tm_routes, "_call_tool", fake_call_tool)


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_gtm_tool_unreachable_skipped(web_env, tmp_path, monkeypatch):
    """探活在线但 PUT /config 时工具掉线(ToolUnreachable)-> skipped, 不阻断 config 应用"""
    mgr, client = web_env
    _online_gtm_env(mgr, tmp_path, monkeypatch)

    def boom(*a, **k):
        raise tm_routes.ToolUnreachable("connection reset during PUT /config")

    _online_gtm_two_phase(monkeypatch, boom)
    bundle_yaml = mask_yaml_text(IMPORT_CONFIG_TEXT)
    r = _import(
        mgr, client, {
            "bundle_version": 1,
            "sections": {
                "config_yaml": bundle_yaml,
                "gtm": {
                    "config": {
                        "foo": 1
                    }
                }
            }
        }
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == ["config_yaml"]
    assert [s["section"] for s in data["skipped"]] == ["gtm"]
    assert "工具不可达" in data["skipped"][0]["reason"]
    assert _read_disk(mgr) == IMPORT_CONFIG_TEXT


@pytest.mark.parametrize("web_env", [{"config_text": IMPORT_CONFIG_TEXT}], indirect=True)
def test_backup_import_gtm_unexpected_status_skipped(web_env, tmp_path, monkeypatch):
    """工具返回非预期状态码(503)-> skipped + 原因透传 error_text, 不炸不阻断"""
    mgr, client = web_env
    _online_gtm_env(mgr, tmp_path, monkeypatch)
    _online_gtm_two_phase(monkeypatch, lambda: (503, {"error": "overloaded"}))
    bundle_yaml = mask_yaml_text(IMPORT_CONFIG_TEXT)
    r = _import(
        mgr, client, {
            "bundle_version": 1,
            "sections": {
                "config_yaml": bundle_yaml,
                "gtm": {
                    "config": {
                        "foo": 1
                    }
                }
            }
        }
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["applied"] == ["config_yaml"]
    assert [s["section"] for s in data["skipped"]] == ["gtm"]
    assert "非预期状态码 503" in data["skipped"][0]["reason"]
    assert "overloaded" in data["skipped"][0]["reason"]


def test_write_yaml_doc_direct_write_and_residual_gate(tmp_path):
    """write_yaml_doc 直测(S2 非端点落盘口): 成功整份写盘; 残留哨兵兜底闸 ConfigError 拒写不半写"""
    from auto_qb.config.errors import ConfigError
    from auto_qb.config.writer import write_yaml_doc

    p = tmp_path / "c.yml"
    bak = tmp_path / "c.bak"
    doc = _build_yaml().load(io.StringIO("config:\n    schema_version: 8\n    qbittorrent:\n        host: 127.0.0.1\n"))
    write_yaml_doc(str(p), doc, str(bak))
    text = p.read_text(encoding="utf-8")
    assert "schema_version: 8" in text and "qbittorrent" in text
    bad = _build_yaml().load(io.StringIO("config:\n    delete_tags:\n        - '********'\n"))
    with pytest.raises(ConfigError, match="掩码哨兵"):
        write_yaml_doc(str(p), bad, str(bak))
    assert p.read_text(encoding="utf-8") == text  # 拒写后磁盘未被半写


def test_mask_unmask_yaml_node_non_dict_passthrough():
    """_mask_yaml_node/_unmask_yaml_node 非 dict 节点直通(防御分支直测, 端点面恒传 dict)"""
    assert config_writer._mask_yaml_node(["x"], ()) is None
    missing = []
    config_writer._unmask_yaml_node("scalar", {"k": "v"}, (), missing)
    assert missing == []


def test_mask_yaml_targets_non_dict_items_untouched():
    """targets 列表含非 dict 条目: 掩码侧原样保留(loop 短路弧), dict 条目照常掩码"""
    text = (
        "config:\n"
        "    web:\n"
        "        transfer:\n"
        "            targets:\n"
        "                - junk-string\n"
        "                - name: t1\n"
        "                  type: qb\n"
        "                  base_url: \"\"\n"
        "                  password: real-pass\n"
    )
    out = mask_yaml_text(text)
    targets = yaml.safe_load(out)["config"]["web"]["transfer"]["targets"]
    assert targets[0] == "junk-string"
    assert targets[1]["password"] == MASK_SENTINEL


def test_unmask_yaml_target_items_edge_shapes():
    """targets 还原边角: 旧条目非 dict/缺名不进配对表; bundle 条目非 dict 跳过; 无名条目
    missing 路径用下标"""
    ry = _build_yaml()
    target_yaml = (
        "config:\n"
        "    web:\n"
        "        transfer:\n"
        "            targets:\n"
        "              - name: t1\n"
        "                type: qb\n"
        "                base_url: \"\"\n"
        "                password: '********'\n"
        "              - junk\n"
        "              - password: '********'\n"
    )
    doc = ry.load(io.StringIO(target_yaml))
    old_doc = {
        "config":
            {
                "web":
                    {
                        "transfer":
                            {
                                "targets":
                                    [
                                        None,
                                        {
                                            "name": "",
                                            "password": "x"
                                        },
                                        {
                                            "name": "t1",
                                            "type": "qb",
                                            "base_url": "",
                                            "password": "real-target-pass"
                                        },
                                    ]
                            }
                    }
            }
    }
    missing = unmask_yaml_doc(doc, old_doc)
    assert missing == ["config.web.transfer.targets[2].password"]
    assert doc["config"]["web"]["transfer"]["targets"][0]["password"] == "real-target-pass"


def test_find_residual_sentinels_shared_containers_dedup():
    """残留哨兵扫描的容器去重(dict/list 两面): 共享引用只报一次路径, 不指数展开"""
    shared_dict = {"k": MASK_SENTINEL}
    shared_list = [MASK_SENTINEL]
    doc = {"a": shared_dict, "b": shared_dict, "c": shared_list, "d": shared_list}
    assert find_residual_sentinels(doc) == ["a.k", "c[0]"]


def test_validate_yaml_doc_cleanup_guard_when_tempfile_open_fails(tmp_path, monkeypatch):
    """validate_yaml_doc finally 清理守卫的空值弧(369 空值, issue 26-11-15-1359): 临时目录不可用
    时 NamedTemporaryFile 在 tmp_path 赋值前抛 OSError -> finally 里 tmp_path 保持 None, 守卫
    `if tmp_path and os.path.exists(...)` 短路跳过删除, 原 OSError 照常传播不被清理路径破坏。

    触发面(自然可达, 非死分支): tempfile.tempdir 指向不存在的目录(对应生产上 TMPDIR 被清
    理/换盘等临时目录失效场景), 走的是 tempfile 真实开文件路径而非替身函数。
    """
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "no-such-temp-dir"))
    doc = _build_yaml().load(io.StringIO("config:\n    schema_version: 8\n"))
    with pytest.raises(OSError):
        config_writer.validate_yaml_doc(doc)
