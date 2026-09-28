# 配置参考

> auto-qb 的完整配置手册：通用约定、完整 YAML 示例、全局限速曲线与规则系统。
> 无论用 Web UI 图形化编辑（推荐）还是直接编辑 YAML，**字段与语义完全一致**。功能总览见 [README](../README.md)。

## 两种配置方式

| 方式 | 适用 | 生效方式 |
|------|------|----------|
| **Web UI 设置页**（推荐） | 日常全部配置：基础、qB 连接、日志、通知、站点、规则集、全局限速曲线 | 保存前自动校验（不通过不落盘）→ 自动备份 `.bak` → 立即生效（需重启的项自动回退并提示） |
| **直接编辑 YAML** | 批量调整、纳入版本管理 | 改完**重启程序**生效；启动时全量校验，所有错误一次列全 |

Web UI 表单与 YAML 键一一对应；两种方式可混用——Web UI 保存会写回配置文件，并保留你原有的注释与书写风格。热重载仅 Web UI 保存管线支持，直接改 YAML 后必须重启。

## 通用约定与注意事项

- 启动时全量检查配置（未知配置项 / 必填项 / 格式 / 取值范围 / 规则引用），所有错误一次列全，不会带病运行；显式留空的配置项视为未配置、使用默认值
- 标签 / 分类 / 路径匹配支持正则（`regex:` 前缀）与忽略大小写（`:ignore_case` 后缀）
- Windows 路径请用 `/` 作分隔符（`\` 在正则中是转义符）；路径匹配默认区分大小写
- 速度单位：`B/s` 或 `[KMG]iB/s`；文件大小单位：`B` 或 `[KMGT]iB`；时间单位：`S` 秒 / `M` 分 / `H` 时 / `D` 天（均不区分大小写）
- 以横杠"-"开头的配置可以同时有多个
- **运行时数据目录** `data_dir`（默认 `auto-qb-data/`）：状态文件、单实例锁、日志、跳检备份默认都存放在其下，多实例运行请为每个实例指定不同目录；状态文件路径也可用 `state_file` 显式指定（优先于 data_dir 派生）

## 完整配置示例

```yaml
---
config:
    # qBittorrent 连接信息
    qbittorrent:
        host: 127.0.0.1
        port: 8080
        username: <USERNAME>
        password: <PASSWORD>

    # 运行时数据主目录: 状态/单实例锁/日志/跳检备份默认均存其下; 默认 auto-qb-data, 多实例请用不同路径
    data_dir: "auto-qb-data"

    # 主循环任务线检查间隔(0.5S~1H)
    main_tick: 2S
    # 种子状态同步线间隔: 只拉 qB 增量刷新快照/事件, 不跑任务(1S~10M; 默认 1.5S, 与 qB 自带 WebUI 同量级)
    sync_interval: 1.5S
    # 状态周期落盘间隔: 断电/强杀等非优雅终止时最多丢失该窗口内的状态(默认 120S; 须 >= 30S, 0 = 关闭)
    state_save_interval: 120S
    # 每个循环最大执行任务数(1~500, 默认 20), 种子数多可适当增加
    max_tasks_per_tick: 50

    # 内置任务检查间隔(1S~1D; 从上一轮处理结束开始计时，不叠加)
    interval: 60S

    # 日志设置(留空则默认落盘到 <data_dir>/logs/auto-qb.log)
    log:
        file: ""                 # 日志文件路径，默认 <data_dir>/logs/auto-qb.log
        level: INFO              # 日志等级
        max_bytes: 10MiB         # 日志轮转大小(1MiB~1GiB)
        format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s" # 日志格式

    # Web UI: 辅种管理 + 图形化配置编辑(默认关闭; 推荐的日常配置方式)
    web:
        enabled: false           # 启用后随主程序启动(--dry-run 不启动)
        host: "127.0.0.1"        # 监听地址, 默认仅本机; 改 0.0.0.0 会暴露管理接口
        port: 8080               # 监听端口
        token: ""                # 访问密钥; 留空首启随机生成 -> <data_dir>/web.token
        skip_local_verify: false  # 本机(127.0.0.1)访问跳过密钥鉴权直接进入; 对外暴露仍强制

    # 主动通知: WARNING 及以上日志推送系统原生通知(默认关闭)
    # ❗容器部署无效: 无桌面会话, 且 slim 镜像没有 notify-send —— send() 只返回 False, 静默无通知
    notify:
        enabled: true              # 启用主动通知
        min_level: WARNING         # 通知最低日志级别: INFO / WARNING / ERROR
        quiet_hours: "23:00-08:00" # 免打扰时段(支持跨午夜)，时段内跳过发送；留空不启用
        max_per_hour: 20           # 每小时通知上限(正整数且 ≤100)，超出丢弃(防风暴)
        dedup_window: 10M          # 相同通知的去重窗口(≤24H)，0 表示不去重
        # channels: [platform]     # 通知渠道，v1 仅平台原生通知(缺省即启用)

    # 删除种子类似(单词相同大小写不同)的标签
    remove_similar_tags: true

    # 自动添加集数标签，仅种子添加时触发; 模板含 ${episode_first}/${episode_last} 占位,
    # 单集/多集分别配置，多集仅在集数连续时生成，不连续视为不可靠放弃添加
    add_episode_tags:
        enabled: true                                       # 启用自动添加集数标签
        add_tag_single: "zE${episode_first}"                # 单集标签格式
        add_tag_multi: "zE${episode_first}-${episode_last}" # 多集标签格式

    # 种子分组管理(辅种管理)
    grouping:
        enabled: true             # 启用种子分组
        check_missing_files: true # 启用缺文件检查(❗容器部署且未配 fs.path_map 时必须设为 false:
                                  #   程序读 qB 报回的宿主保存路径, 容器里看不到那块盘 ⇒ 误暂停整组;
                                  #   配好映射后可保持 true —— 见 docs/deployment.md §11.3/§11.5)
        missing_tag: MISSING      # 文件丢失时整组添加的标签

    # 下载目录路径映射(容器部署, plan 26-09-27-1407): qB 报回的宿主路径前缀 -> 本容器挂载点。
    # 留空(默认)= 完全现状(宿主直跑 / Linux 同路径挂载不需要); 配好映射后缺文件扫描/跳检前置/
    # exists()/disk_*()/目录浏览恢复可用, 映射 miss 一律判「不可判定」不误判缺失。
    # 完整说明与 Windows 宿主样例: docs/deployment.md §11.5
    fs:
        path_map: []
        # - from: "D:/Downloads"   # qB 报回的宿主保存路径前缀
        #   to: "/mnt/downloads"   # 本容器挂载点(compose -v D:\Downloads:/mnt/downloads:ro)

    # 全局自动彻底删除标签
    delete_tags:                        # 彻底删除的标签格式，支持正则
        - "M-Team - TP:ignore_case"
        - "regex:^BTSCHOOL$"
    delete_tags_if_has_no_torrents:     # 无种子使用时才删除
        - "@tracker_tags:ignore_case"   # 引用全部 tracker 配置的标签， 并忽略大小写
        - "regex:^zE.*$"                # 删除所有集数标签
        - "MISSING"                     # 删除缺失文件标签

    # 全局 HR 设置(可在 tracker 中单独配置 hr 覆盖全局设置)
    hr:
        add_tag: ''                                                     # 满足 HR 触发条件时添加的标签格式，支持变量: ${required_seeding_time} - 要求做种时长
        add_category: '!!HR${required_seeding_time}!!'                  # 满足 HR 触发条件时添加的分类格式，支持变量
        overwrite_category: false                                       # HR 触发条件时是否覆盖分类 (qb中一个种子只能有一个分类)
        add_tag_for_satisfied: ''                                       # 做种时长满足要求时添加的标签格式
        add_category_for_satisfied: '--HR${required_seeding_time}--'    # 做种时长满足要求时添加的分类格式
        overwrite_category_for_satisfied: false                         # 做种时长满足要求时是否覆盖分类

    # 跳检成功标签(全局统一, checking 动作不可按规则覆盖)
    # 带此标签的种子未经哈希校验, 查找参考种子时一律排除(防"未验证"经辅种参考链传播); 默认 zSkipChecked
    skip_checking_tag: zSkipChecked

    # 全局限速曲线配置 (需配置数据来源, 完整示例见[#全局限速曲线])
    # global_speed_limit_curve:

    # 自定义规则集 (名称以 "_rules" 结尾): 完整示例见[#规则系统])
    # example_rules:
    #     rule1: ...

    # tracker 站点配置 (也可在 Web UI 设置页增删改, 「站点」分区可一键导入缺失站点自动生成默认配置;
    # 用 YAML 时建议先 `--export-yaml missing.yml --only-missing` 导出骨架再改)
    trackers:
        tracker1:                                  # 自定义 tracker 站点名称
            domains:                               # 站点域名，可以有多个
                - domain1
                - domain2
            tags:                                  # 自动添加站点标签
                - tag1
                - tag2
            remove_tags:                           # 自动删除站点标签，支持正则
                - tag3
                - tag4
            groups:                                # 站点分组(可多个，供规则 tracker_group 条件按分组筛选；配置层概念，不写种子)
                - 国内
            upload_speed_limit: 1000KiB/s          # 单种上传限速，0 指无限制
            download_speed_limit: 10MiB/s          # 单种下载限速，0 指无限制
            hr:                                    # HR 规则(可覆盖全局设置)
                required_seeding_time: 3D          # 要求做种时间
                required_share_ratio: 2.0          # 要求分享率(0~100)
                extra_seeding_time: 12H            # 额外做种时间防止意外
                condition: 80%                     # 触发 HR 的下载比例(0 < 比例 ≤ 100)；也可用绝对量(须 >0)，如 10MiB
            # rules:                               # tracker 引用规则(完整示例见[#规则系统])
            #     - "@example_rules"               # 引用整个规则集
            #     - "@example_rules.rule1"         # 引用具体规则
        tracker2:
            # ...
```

## HR 在线核实(`hr_check`)

> 🚧 **取数通道已落地**: 后端会起一个**仅监听 `127.0.0.1`** 的本地端点, 由
> [`extensions/hr-fetch-proxy/`](../extensions/hr-fetch-proxy/README.md)(浏览器扩展)拉清单并回传
> 页面 DOM 与 `.torrent` 字节 —— 后端**零 cookie / 零直连站点**。装上扩展并在 `channel` 里开启后
> 才会真的在线核实; 没装扩展的实例只读共享站点数据(不会报错, 也不会静默降级为直连)。

部分站点只对**一部分**种子计 H&R, 且不提供可机读的逐种标记 —— 只能上站查。`hr_check` 就是为此而生。
**判定语义是硬编码的, 没有撤退路径**(v3, 计划 26-09-28-1932): 对每个绑定站点的种子按四行判定表出结论 ——
**命中考察中(A) → 受管束**(网站绝对权威, 本地达标与否都管, 删了前功尽弃真吃 H&R); **命中终态档
B 已达标 / C 未达标 / D 已免罪 → 放行**(站点结论已定, 终态不可逆); **覆盖范围内未列出 → 放行**
(站点不管它了); **无有效站点证据 → 本地判据兜底**(达标放行 / 未达标管束 —— 「本地做种达到要求
就可视为完成, 在线核实只是保障准确」)。做种时长 ≥ 3 × 要求时长(程序常量)的种子免除在线对账义务
(不为它翻页下载), 但被动命中考察中仍照常管束。

- **全局段** `config.hr_check`(6 键): `enabled`(总开关, 默认 false) + 单频控三键 ——
  `min_interval`(默认 90S, 相邻请求最小间隔, 页面与 .torrent 统一适用, 抖动只向上 +0~25%)、
  `max_requests_per_day`(默认 240, 站点级日额保险, 零点重置)、`max_pages_per_wave`(默认 30,
  单波页数上限安全阀, 到顶该档截断, 下波从头再翻) + `allow_window`(可选, 仅该时段取数) +
  `shared_dir`(多实例共享目录) + `channel`。
- **取数通道** `hr_check.channel`: `enabled`(本实例是否装了扩展)、`port`(默认 8788; **同机多实例必须各不相同**,
  被占则启动直接报错)、`token`(留空 = 随机生成到 `<data_dir>/hr.token`, 扩展侧逐实例填)、
  `extension_id`(可选: 填了就只放行该扩展 id, 留空 = 靠 token 鉴权; ❗留空时任意扩展 origin 都能带上
  正确 token 调用端点 —— 启动时会记一条 WARNING 提示, 建议把扩展的固定 id 填进来作第二道防线)、
  `request_timeout`(默认 180S: 等扩展回传的上限)。
  安装与配置步骤见 [扩展说明](../extensions/hr-fetch-proxy/README.md)。
- **站点接入** `hr_check.sites.<站点>`(**唯一站点配置源**, 共 3 键): `enabled`(启用即管) +
  `tracker`(显式绑定; 留空 = 档案按 announce 域自动映射) + `refresh_interval`(对账波周期, 默认 12H;
  失败的档位也按本周期自然重试)。页面地址、解析器、种子下载路径、翻页参数、清单形态(listing)这些
  **程序已知、人易配错**的内容由内置站点档案自动填充, 配置里写这些值不再被接受。
- **波次与数据有效性**: 每个对账波都从第 1 页开始、以覆盖全部对象(未对账 ∪ 考察中)为目标 ——
  首波深(大站 20 页级), 此后随种子对账/转终态/做满 3× 单调变浅, 稳态一两页即停。拿到有效的数据
  **永续有效**(终态不可逆), 没有时效只有真伪; 页面失败/解析失效只让该档证据在失效点截断
  (之前的数据照常生效), 下个周期自然重试 —— 没有熔断、没有停用、没有退避。
- **证据防伪**(防改版吞行被误放行): 批量签发「未列出」放行前过三道闸 —— ① A 档流转守恒
  (上波考察中行本波留存率 ≥ 70%); ② 总行数骤降(< 基线 30%)冻结; ③ 结构完好的零行波**不签发放行**,
  需 `--hr-confirm-empty <站点>`(或 WebUI 站点卡片「确认空清单」按钮)写一次性人工对账戳 ——
  清单再现任何非零行时确认戳自动失效。上波命中考察中、本波没看到的种子**维持管束**(失踪观察期):
  自身位置被覆盖且连续 2 波未重见才判「移出」放行。
- **登录失效**: 页面变成登录页 ⇒ 记 `[HR 登录失效]` 告警(不计失败), 该档截断, 周期自然重试 ——
  只有去浏览器登录才有用。

配置期会直接报错的规则(都是为了不让人踩到「保护静默失效」):

1. **`sites` 的键必须是已登记的档案 id** —— 未入档案的站点不允许启用(运行期只会静默跳过, 必须配置期拦下);
   报错文案会给出当前已支持清单。
2. **启用的站点必须绑定成功** —— 默认映射: 档案已知 announce 域在站点 `domains`(同命名空间)查表,
   双向子域容错, 恰好 1 个命中即自动绑定; 绑不上(0 命中)或歧义(≥2 命中)时报错并要求在条目里
   显式填 `tracker` 指定。绑定的站点还必须配置 `hr` 段, 否则该站的 HR 判定前置条件恒为假,
   整站保护不会有任何提示地失效。

### 已支持站点与绑定规则

启用一个站点 = 在 `hr_check.sites` 下写一行 `enabled: true`, **零 URL / 路径 / 参数 / 域名引用填写**:

```yaml
config:
    hr_check:
        enabled: true
        min_interval: 90S            # 相邻请求最小间隔(页面 + 下载统一)
        max_requests_per_day: 240    # 日额保险
        max_pages_per_wave: 30       # 单波页数上限
        sites:
            btschool:
                enabled: true
                # ↓ 两键可省
                # tracker: BTSchool      # 显式绑定(自动映射未命中/歧义时必填)
                # refresh_interval: 12H  # 对账波周期
```

当前内置档案(随版本发布; 新站点/新 adapter 以 `src/auto_qb/config/site_presets.py` 为准):

| 档案 id | 解析器 | web 域(派生 HR 页) | announce 域(默认映射查表键) | HR 页 | 种子下载 | 翻页参数 |
|---|---|---|---|---|---|---|
| `btschool` | `nexusphp` | `pt.btschool.club` | `pt.btschool.club` | `/myhr.php` | `/download.php?id={id}` | `page` |
| `carpt` | `carpt` | `carpt.net` | `tracker.carpt.net` | `/myhr.php` | `/download.php?id={id}` | `page` |

- **绑定 = 映射**: web 域与 announce 域是两个命名空间, **永不互相比对**(CarPT 两域无关正是例证)。
  默认映射查表命中即零配置绑定; 显式 `tracker` 填 trackers 下的条目名直取。
- **旧键**: `trackers.<站点>.hr_check` 已废除 —— config v2→v3 迁移自动改写(`mode: partial/all`
  → `enabled: true`), v3 起出现即直接删除, 无常驻兼容。

### 想接的站点不在档案里怎么办

站点「可启用」的判定单点在内置档案表(`src/auto_qb/config/site_presets.py`), 未入档案的站点配置期就会被拒。
新站点按三种情形接入(登记点单点化, 见 `src/auto_qb/hr/adapters/__init__.py` 模块说明):

1. **NexusPHP 标准形态**(`myhr.php` 九列表, 绝大多数 PT 站): 不用写代码, 只在 `site_presets.py` 立一条档案
   (adapter=`nexusphp` + 档案域名 + 页面路径), 随版本发布后即可在 `hr_check.sites` 点选启用。
2. **页面形态变体**(状态参数/表头名不同, 如 CarPT): 写一个薄 adapter 并在 `hr/adapters/__init__.py` 登记名字, 再立档案。
3. **有更便宜的来源**(JSON 接口 / 逐种 HR 标记, 可完全不下载 `.torrent`): 写一个 adapter, 接口不变, 再立档案。

- 站点之间**完全隔离**: 各自一个站点文件(`<data_dir>/hr/<站点>.json`)、各自一把锁、各自一本频控账本 ——
  一个站点失败或正在慢速取数, 不会影响另一个。
- 取数在**登录态下**由浏览器扩展完成(后端零 cookie); 档案里的页面事实**拿不准就先跑一次走查**
  (`--hr-once`) —— 它会如实报「未找到 HR 表(疑似改版)」或「排序假设不成立」, 而不是默默少抓。

❗`hr_check.allow_window` 与 `notify.quiet_hours` **语义相反**: 那个是「这段时间不发通知」,
本项是「只在这段时间取数」。

❗多实例共享同一账号时: 把 `hr_check.shared_dir` 指向各实例都能看到的**同一目录**(网络盘可以,
云同步盘不可用), 并让各实例用**不同的 `channel.port`**。同站点靠「文件锁 + 复用窗」保证只被访问一次,
所以**每台有浏览器的实例都建议开 `channel`** —— 不会双倍访问站点, 却消掉了「只有一台能抓」的单点。

只读走查(不写文件、不连 qB, 可与正式实例并发):

```bash
python src/auto-qb.py config.yml --hr-once
# 用保存下来的页面离线验证解析与索引(目录里按 <档位>.html 命名, 如 A.html)
python src/auto-qb.py config.yml --hr-once --hr-html-dir ./saved-pages
```

只读现状(同样不写盘 / 不连 qB / **不取数**): 把**已落盘**的数据摊开给你核对 —— 各档波次状态
(页数/行数/覆盖边界/截断原因)、守恒与骤降观测、放行签发开关、观察期中的种子数, 以及最需要人眼对账的
**明细表**(`tid / 档位 / 上传量 / 下载量 / 分享率 / 还需做种 / 名称 / infohash`; 档位写实际意思 ——
考察中 / 已达标 / 未达标 / 已免罪, 「还需做种」与站点页面同形态, 可逐格核对):

```bash
python src/auto-qb.py config.yml --hr-status            # 每站点最多显示 10 行明细
python src/auto-qb.py config.yml --hr-status --hr-status-rows 50
```

人工对账(写操作, 单独执行): 排查确认「账号的 HR 清单确实为空」后, 用一次性确认戳解除零行波的
签发冻结 —— 之后零行波可正常签发放行, 清单再现非零行时戳自动失效:

```bash
python src/auto-qb.py config.yml --hr-confirm-empty btschool
```

站点级现状在**界面里**也能看: 设置页「HR 在线核实」分区页尾「站点状态」 —— 每站点一段,
写着数据新鲜度(上次取波 / 最近健康波 / 复用窗)、各档波次状态、频控账本、守恒与骤降观测,
以及一句「**现在为什么不放行**」; 零行未确认的站点直接给「确认空清单」按钮。
它与 `--hr-status` 是**同一层数据**(同一个 `hr.status` 快照, 字段口径单点), 只是呈现不同 ——
界面里看到的是「打开时那一刻」的只读快照, 不会触发任何取数。

### 出问题时先看日志标签

「需要人做点什么」的事件在日志里都带标签前缀(可直接 `grep "[HR "` 过滤):

| 标签 | 意思 | 该做什么 |
|---|---|---|
| `[HR 登录失效]` | 那个浏览器里的站点登录态掉了(页面变成登录页) | 去该浏览器登录这个站点(该档截断, 周期自然重试) |
| `[HR 页面改版]` | 表头找不到 / 字段缺失 / 排序崩塌 / 守恒或骤降不过 ⇒ 该档截断 | 人工核对站点 HR 页结构; 连续 3 波失效会 ERROR 告警建议走查 |
| `[HR 通道静默]` | 端点长期没被扩展联系(浏览器没开 / 扩展停用 / 端口或 token 不一致) | 按告警里列的**受影响站点**逐个自查 |

❗**日志里出现 `配额/间隔受限(间隔: 还差 Ns)` 不是故障** —— 那是后端在按自己的频控节奏取数:
波内每个请求之间至少隔 `min_interval`(默认 90s), 默认配置下一波要跑好几分钟是正常的。
这类「被自己拦住」的状态按 INFO 记录(且同一原因只记一次, 不逐轮刷); 只有**页面/字段/翻页问题**、
取数失败、通道静默才会 WARNING —— 因为 WARNING 会被 notify 推成系统通知, 若把频控也算进去就会弹窗轰炸。
启动 / 关闭 / 热重载这些「程序自己决定要发生」的消息同理走 INFO。
想知道「数据到底拉到没有 / 对不对」用 `--hr-status`, 想知道「现在能不能取到数」用 `--hr-once`。

站点数据文件(<data_dir>/hr/<站点>.json, 或 `shared_dir` 下的同名文件)自带两层保护:
每次写盘把上一版留为 `<站点>.json.bak`; 读到**坏文件**(空文件 / 非 JSON)时把现场挪到
`<站点>.json.bad-<时间戳>` 并尝试用 `.bak` 恢复 —— 丢失索引/已取记录等于要重新烧配额抓一遍
(`hr_downloaded` 没了还会重下 .torrent), 所以值得两份。若反复出现这一告警, 先看 `.bad-*` 里到底是什么:
**空文件**通常是写盘被中断或有编辑器 / 同步盘在动这个目录(HR 目录不要放云同步盘)。

## 全局限速曲线

> 目前本软件不支持监控设备全局流量，所以需配置外部流量数据来源。

根据流量数据来源记录的每日流量，按日 / N天 / 月等周期聚合，上传或下载量达到阈值后自动收紧 qB 全局限速；同一方向命中多条曲线时取**最严**限速。

```yaml
---
config:
    global_speed_limit_curve:
        enabled: true            # 功能总开关(缺省 true); false = 整体停用
        interval: 10M            # 曲线任务执行间隔(缺省回退主 interval)
        traffic_source:
            - traffic_monitor: # Traffic Monitor: 流量监控软件，可记录每天使用流量
                dat_path: "D:/Programs/TrafficMonitor/history_traffic.dat" # 路径若需使用\，则请使用\\
            # 后续可能支持接入其它软件来源
        curves: # 每条 period 曲线为 curve 单项映射; 重复 period 拒绝
            - curve:
                period: DAY    # 周期，支持 DAY(当天)、MONTH(当月)、ND(最近N天)
                upload_curve:  # 由上传量阈值和对应速度组成，限制上传速度(阈值须严格递增)
                    - 10GiB:   # 上传量小于 10GiB 时，限制上传速度为 6MiB/s
                        upload_speed_limit: 6MiB/s
                    - 20GiB:   # 上传量大于等于 10GiB 且小于 20GiB 时，限制上传速度为 5MiB/s
                        upload_speed_limit: 5MiB/s
                    - 50GiB:   # ...
                        upload_speed_limit: 2MiB/s
                    - 100GiB:
                        upload_speed_limit: 1MiB/s
                download_curve: # 由下载量阈值和对应速度组成，限制下载速度(可省略 = 不管理该方向)
                    - 100GiB:   # 同理
                        download_speed_limit: 5MiB/s
                    - 200GiB:
                        download_speed_limit: 2MiB/s
            - curve: # 多条曲线同方向取最严限速(各 period 口径都需满足)
                period: 7D
                upload_curve:
                    - 50GiB:
                        upload_speed_limit: 4MiB/s
            # ... 可继续添加 MONTH / ND 等周期的 curve
```

> 全局限速曲线也可在 Web UI 设置页以表单 + 阶梯图方式编辑。

### 流量数据来源：Traffic Monitor

[Traffic Monitor](https://github.com/zhongyang219/TrafficMonitor)（[Gitee 镜像](https://gitee.com/zhongyang219/TrafficMonitor)）是一款显示当前网速、CPU / 内存利用率的桌面悬浮窗软件。可以记录每天的上传 / 下载流量，建议开启开机自启，以便持续记录流量。

> **如何找到数据文件路径？** 常规设置 → 配置和数据文件 → 打开配置文件所在目录。其中 `history_traffic.dat` 记录了每天的上传 / 下载流量历史，格式如下：

```text
lines: "30"
2026/09/04 64033621/104743685
2026/09/03 23295975/37857445
2026/09/02 23243979/53483350
...
```

> 希望接入其它流量监控软件可提Issue。

## 规则系统

规则集名称以 `_rules` 结尾，挂在 `config` 段下；tracker 通过 `rules` 引用（`@规则集` 引用整组，`@规则集.规则名` 引用单条）。规则同样可在 Web UI 设置页以卡片 + 选择面板方式编辑（16 种条件 / 12 种动作的选择、排序与参数）。

```yaml
---
config:
    example_rules: # 🚧
        rule1:
            enabled: true
            trigger: interval                      # 触发时机: interval / on_torrent_added / on_torrent_state_enum_changed / on_torrent_deleted
            interval: 60S                          # 执行间隔(interval 触发时使用)
            execute_once: never                    # 去重: never/once/daily/hourly 🚧
            cooldown: 0S                           # 距上次执行成功不足该时长则跳过 🚧
            conditions:                            # 筛选条件必须全部满足
                - path: /path/to/file              # 路径，支持正则
                - size: ">=100MiB"                 # 文件大小
                - tags:                            # 标签(不同标签组之间为或)
                    - tag1,tag2
                - category:                        # 分类
                    - category
                - trackers:                        # tracker 自定义名称(不同组之间为或) 🚧
                    - tracker1
                - state:                           # 语义化状态(不同组之间为或) 🚧
                    - is_complete&is_uploading     # 已完成且正在上传(& 连接)
                - hr: condition-met                # condition-met/condition-not-met/satisfied 🚧
                - date_time:                       # 当前时间 🚧
                    day_of_month: 1-31
                    day_of_week: 1-7
                    time: 10:00-23:00
                - seedtime: "<24H"                 # 做种时长 🚧
                - upload_ratio: ">1.5"             # 上传比率 🚧
                - freespace:                       # 剩余空间 🚧
                    path: "R:/"
                    amount: "<100GiB"
            actions:                               # 动作顺序执行，默认一个出错后续不执行
                - checking:                        # ⚠️ 校验/跳检(见下方 checking 动作说明) 🚧
                    basic_check: filelist          # filelist/piecehashes/custom
                    with_reference:                # 有参考种子(已完成的同组种子)
                        enabled: true              # 启用
                        mode: skip-checking        # skip-checking 跳检(风险可控)/full-checking 全量校验
                        auto_start: true           # 校验成功后自动开始
                    without_reference:             # 无参考种子
                        enabled: true              # 启用
                        mode: full-checking        # full-checking 安全；skip-checking 高风险
                        auto_start: true           # 校验成功后自动开始
                - start: true                      # 开始
                - stop: true                       # 暂停
                - print_torrent_details: true      # 打印种子详情到日志(只读留档; on_torrent_deleted 唯一允许动作)
                - ignore_next_action_error: true   # 忽略下一个动作的错误继续执行 🚧
                - add_tags:                        # 添加标签，支持变量
                    - tag-format1
                - remove_tags:                     # 删除标签，支持正则和变量
                    - tag-format3
                - add_category:                    # 添加分类
                    format: category-format
                    overwrite: true                # 强制覆盖已有分类
                - remove_category: true            # 自动删除站点分类
                - move_to:                         # ⚠️ 移动保存路径 🚧
                    path: /path/to/move/to
                    overwrite: true
                - reannounce: true                 # ⚠️ 强制汇报 tracker(有风险) 🚧
                - upload_speed_limit: 1000KiB/s    # 上传速度，不覆盖单数值
                - download_speed_limit: 1000KiB/s  # 下载速度，不覆盖单数值
            # 可选: conditions-met / conditions-not-met / action-failed /
            #       all-actions-succeed / always / never
            stop_following_rules_if: conditions-met # 🚧
    trackers:
        tracker1:
            domains:
                - domain1
            rules:                                 # tracker 引用规则
                - "@example_rules"                 # 引用整个规则集
                - "@example_rules.rule1"           # 引用具体规则
```

### 触发时机

| 触发时机                         | 状态      | 说明                                                                 |
|----------------------------------|-----------|----------------------------------------------------------------------|
| `interval`                       | ✅ 已实现  | 固定时间间隔循环一次                                                 |
| `on_torrent_added`               | ✅ 已实现  | 新种子添加时事件触发；checking 等异步动作经 rule-event 断点续跑       |
| `on_torrent_state_enum_changed`  | ✅ 已实现  | 种子 qB 状态枚举发生变化时事件触发                                   |
| `on_torrent_deleted`             | ✅ 已实现  | 种子删除时触发（现场为删除前快照）；仅允许 `print_torrent_details`    |

`interval` 触发的规则未显式配置 `interval` 时，默认每个主循环 tick 检查一次（等价 `0S`，既有行为）；显式配置时必须 > 0。

### 筛选条件（12 种）

| 条件                     | 说明                                                                                      |
|--------------------------|-------------------------------------------------------------------------------------------|
| `path`                   | 保存路径，支持正则，使用 `/` 分隔符                                                         |
| `size`                   | 文件大小限制，支持比较符 `> < >= <=`                                                       |
| `tags`                   | 标签，不同标签组之间为或关系，支持正则和 `${required_seeding_time}` 变量                    |
| `category`               | 分类，支持正则和变量                                                                       |
| `trackers`               | tracker 自定义名称，不同组之间为或关系，支持正则                                            |
| `tracker_group`          | 站点分组：匹配站点 `groups` 字段声明的分组（配置层概念，不写种子），不同组之间为或关系，支持正则 |
| `state`                  | 语义化状态（见[状态映射表](#状态映射表)），支持 `&` 连接多个状态                             |
| `hr`                     | HR 筛选：`condition-met`（满足触发）/ `condition-not-met` / `satisfied`（满足要求 + 额外时长） |
| `date_time`              | 日期时间：`day_of_month` / `day_of_week` / `time`                                          |
| `seedtime`               | 做种时长                                                                                  |
| `upload_ratio`           | 上传比率                                                                                  |
| `freespace`              | 指定路径剩余空间                                                                          |

### 动作（12 种）

| 动作                                          | 说明                                                                                       |
|-----------------------------------------------|--------------------------------------------------------------------------------------------|
| `checking`                                    | 校验 / 跳检：skip-checking (⚠️ __<font color="red">有风险!</font>__) 或 full-checking（安全） |
| `start` / `stop`                              | 开始 / 暂停种子                                                                            |
| `print_torrent_details`                       | 打印种子详情到日志（只读留档，不操作种子；`on_torrent_deleted` 触发下唯一允许的动作）        |
| `add_tags` / `remove_tags`                    | 添加 / 删除标签，支持正则和变量                                                             |
| `add_category` / `remove_category`            | 设置 / 清空分类，支持强制覆盖                                                               |
| `move_to`                                     | 移动保存路径                                                                               |
| `reannounce`                                  | 强制汇报 tracker (⚠️ __<font color="red">有风险!</font>__)                                 |
| `upload_speed_limit` / `download_speed_limit` | 单种上传 / 下载限速 （⚠️ 注意上传限速过低有风险）                                            |
| `ignore_next_action_error`                    | 忽略下一个动作的错误继续执行（仅对下一个动作起效）                                           |

### 去重与一次执行

- 规则默认 `execute_once: never`，只适合幂等动作（加 / 删标签、设分类）
- 非幂等动作（校验、开始、强制汇报、限速）**必须**配置 `execute_once` 或 `cooldown`，否则会在条件成立期间反复触发
- `execute_once` 取值：`never` / `once`（每种子仅一次）/ `daily`（每种子每天最多一次）/ `hourly`（每种子每小时最多一次）
- `cooldown` 可覆盖 `execute_once` 粒度，如 `execute_once: never` + `cooldown: 10M`
- 执行历史保存在数据目录的状态文件中，按 `规则名 + 种子 + 时间窗口(日/小时)` 记录；`daily` 按自然日切换
- 跳检另有独立兜底：同一种子当日只跳检一次（跨规则生效）+ 全量校验连续失败 3 次当日冷却（防损坏文件反复校验死循环，次日重置）+ 强制汇报运行时最小间隔 10M（不依赖规则去重）

### 动作结果与错误处理

- 每个动作返回统一结果：`success` / `failed` / `skipped`
- `failed`：qB 返回失败或出错；`skipped`：条件不满足（如标签已存在、分类已设置），**不算失败**
- `stop_following_rules_if: action-failed` 只对 `failed` 生效，`skipped` 不影响
- `ignore_next_action_error` 只对下一个动作生效，忽略 `failed` 继续执行

### 状态映射表

规则条件里的 `state` 是语义化状态，与 qB 官方状态语义一致：

| 状态             | 覆盖的 qB state                                                                                   | 说明                         |
|------------------|---------------------------------------------------------------------------------------------------|------------------------------|
| `is_checking`    | checkingDL, checkingUP, checkingResumeData                                                        | 正在校验                     |
| `is_downloading` | downloading, forcedDL, metaDL, forcedMetaDL, checkingDL, queuedDL, stalledDL, pausedDL, stoppedDL | 下载中（含暂停 / 排队 / 校验） |
| `is_complete`    | uploading, stalledUP, pausedUP, forcedUP, queuedUP, stoppedUP, checkingUP                         | 已完成下载                   |
| `is_uploading`   | uploading, forcedUP, stalledUP, queuedUP, checkingUP                                              | 上传做种中                   |
| `is_errored`     | missingFiles, error                                                                               | 出错                         |
| `is_stopped`     | pausedDL, pausedUP, stoppedDL, stoppedUP                                                          | 已暂停 / 停止                |

`is_complete&is_uploading` 即"正在做种中"（含 queuedUP/checkingUP）。
注意 `downloading` 含 pausedDL/stoppedDL 等暂停下载状态；条件不支持 `!` 取反，需排除暂停下载时用 `is_stopped` 另行判断。

### `checking` 动作说明

- `basic_check` 决定如何从同组「已完成」的成员中确定**参考种子**：
  - `filelist`：分组已保证文件列表与大小一致，候选直接作为参考（最宽松）
  - `piecehashes`：额外对比双方每个数据块的 hash 列表完全相同（不读取实际文件）；直接转种有效，重新制作且块大小不同的种子无效（较严格）
  - `custom`：运行外部程序判定（参数 `<候选hash> <保存路径>`，返回码 0 即视为参考，需配 `custom_basic_check_program_path`）
    - ❗**容器部署不可用**：该程序不在镜像里，`FileNotFoundError` 被吞掉后每个候选都判为「非参考」并刷一条 WARNING。容器内请改用 `filelist` / `piecehashes`（同组文件一致性由分组保证，与能否读到磁盘无关）
  - 此外，历史上全量校验通过的种子会记入内存参考集，同样可作参考（程序重启后重新积累）
- 确定参考后按段执行（`with_reference` / `without_reference` 两段均可独立 `enabled: false` 关闭）：
  - **有参考种子**：`full-checking` 为 qB 自带全量哈希校验 __<font color="green">安全</font>__；`skip-checking` 跳检 __<font color="orange">风险相对可控</font>__
  - **无参考种子**：`full-checking` __<font color="green">安全</font>__；`skip-checking` 为⚠️ __<font color="red">高风险</font>__（仅做基础文件存在与大小对比、不做哈希校验直接开始，文件内容错误会上传垃圾数据，被大部分 PT 站点严令禁止）

**配置组合风险对照表**

| 参考种子              | 模式            | 风险等级                                     | 说明                                                                                |
|-----------------------|-----------------|----------------------------------------------|-------------------------------------------------------------------------------------|
| 有(with_reference)    | `full-checking` | __<font color="green">安全</font>__          | qB 全量哈希校验，且同组已有完整种子佐证数据                                          |
| 有(with_reference)    | `skip-checking` | __<font color="orange">风险相对可控</font>__ | 文件内容有同组完整种子参照，跳过哈希但数据相对可信                                   |
| 无(without_reference) | `full-checking` | __<font color="green">安全</font>__          | qB 全量哈希校验，本身不依赖参考种子                                                  |
| 无(without_reference) | `skip-checking` | __<font color="red">高风险</font>__          | 仅文件存在与大小对比、无任何哈希校验，内容错误即上传垃圾数据，被大部分 PT 站点严令禁止 |

> 「有参考」是否可靠取决于 `basic_check` 的严格度：`piecehashes`（块 hash 列表完全相同）严于 `filelist`（仅文件列表与大小一致）。判定越严格，「有参考 + skip-checking」的 <font color="orange">风险相对可控</font> 才越站得住脚；不确定时优先用 `full-checking`。

- **skip-checking 的机制与代价**：通过「导出种子 → **删除种子** → 重新导入时跳过哈希校验」实现，它可**保留**标签、分类、上传 / 下载限速、保存路径，但**丢失**下载量、上传量、做种时长、上传比率等**本地统计数据**（删除种子会清空 qB 本地统计，属固有代价），请务必谨慎使用。
  - 注意: 跳检在**删除种子之前**就会把 .torrent 备份到数据目录 `skip-check-backup/`（崩溃安全：删除是第一个不可逆步骤）；重加成功后备份自动清理，只有在重加失败或跳检途中程序崩溃时才会留下备份文件（连同 state 里的元数据），此时请自行手动恢复。
- 校验通过后的种子可成为同组其他种子的**参考种子**，让后续辅种走上面「有参考种子」的路径。
- **跳检打标与参考排除**（`skip_checking_tag`，默认 `zSkipChecked`）：跳检成功后自动给该种子打上标签，标记它**未经哈希校验**；此后查找参考种子时，凡带此标签的种子一律排除（即使它在内存参考集中）。这样可避免「未验证」的种子被当作可信参考、经辅种参考链把潜在的数据错误扩散到整组。标签名是全局配置 `config.skip_checking_tag`，对所有 checking 动作统一生效，不可按规则覆盖。
  - ⚠️ **修改标签名的风险**：标签打在种子上持久保存，而参考排除只认**当前配置**的标签名。更改全局标签名后：
    - 此前按旧标签打标的种子将**不再被排除**出参考种子——「未验证」的旧跳检种子会重新成为可信参考，数据错误可能经参考链扩散到整组；
    - 旧标签**不会自动移除**，仍残留在种子上；若日后改回旧名，这些种子又会重新被排除。
  - 建议：确需更换标签名时，先在 qB 中手动替换所有种子上的旧标签，再修改配置；并保持标签名长期稳定，避免频繁变更。

#### `checking` 安全保障

为防止误传垃圾数据被站点处罚，checking 动作在真正执行前会按顺序经过多道闸门，任一不满足即跳过或等待（均无副作用）：

**① 状态与分组门槛**

- 仅处理「暂停中且未完成」的种子；已完成或下载 / 做种中的种子直接跳过，避免已完成种子被反复校验
- 组内有种子正在下载 → 整组视为未完成，**不进行任何校验**（包括跳检）

**② 组内校验协同**

- 组内其它成员正在全量校验 → **让位等待**（组内共享同一份文件，并行校验只是重复读盘），待其完成后重走决策链；等待上限 2 小时，防止异常卡死
- 组内其它成员当日校验失败、且文件大小与本种子一致（即同一份物理数据）→ 校验结果必然相同，**直接跳过**（失败推断）

**③ 执行前文件复查**

- 分段确定后、真正校验前，再次确认文件全部存在且大小一致（分组虽已保证，仍强制复查一遍），不通过则跳过

**④ 跳检专属红线**（仅 skip-checking）

- **部分下载的种子禁止跳检**：下载到一半的种子，文件尺寸已被 qB 预分配为完整尺寸，尺寸检查发现不了尚未下载的部分，跳检会把空数据当作有效数据上传垃圾；**只有从未下载过（全新辅种、数据完整）的种子才能跳检**，部分下载请改用全量校验
- **同日去重**：同一种子当日最多跳检一次（跳检必然清空本地统计，重复跳检只有损失没有收益）

**⑤ 全量校验失败冷却**

- 同一种子当日连续校验失败 3 次后不再重试（防止损坏文件触发反复校验死循环），次日自动重置
