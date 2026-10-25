# Mihon Harmony Preview —— 维护手册

> 面向后续接手维护的人或 AI 助手。读完本文并拿到一个有 `repo` + `workflow` 权限的 GitHub token，
> 就应能完整理解现状并继续维护本仓库。
>
> 仓库：`https://github.com/Xun2202/mihon-harmony`　维护者 GitHub 账号：`Xun2202`
> 本仓库在 GitHub 上仍标记为 fork 自 `zsyou/mihon-harmony`（无法自行取消），但 `main` 上已经没有 Mihon 源码，
> 只有补丁、脚本、workflow 和文档。2026-09-26 之前的 fork 历史仍在 git 里。

---

## 1. 背景与目标

- [Mihon](https://github.com/mihonapp/mihon) 是安卓漫画阅读器。用户在华为 HarmonyOS NEXT 设备上通过**卓易通**（安卓兼容层）运行它。
- 卓易通的 SAF 文件提供方不支持 `renameDocument`，导致章节下载失败。[zsyou/mihon-harmony](https://github.com/zsyou/mihon-harmony)
  做了改名回退修复，上游 PR [mihonapp/mihon#3446](https://github.com/mihonapp/mihon/pull/3446) 截至 2026-10 仍未合并。
- 用户要用 Mihon 的 **Private 扩展安装器**（把扩展装进 App 自己的目录，绕开卓易通对安装第三方 APK 的限制）。
  上游在 `release` 构建类型里隐藏了该选项（`SettingsAdvancedScreen.kt` 里 `if (isReleaseBuildType) it != PRIVATE`），
  只有 `preview` 构建类型才显示。
- 作者只发布 `release` 构建，官方 Beta 又没有下载修复。因此本仓库：**基于官方稳定版 + 补丁，编译 `preview` 构建类型，并让 App 从本仓库检查更新。**

## 2. 现状总览

| 项目 | 内容 |
| --- | --- |
| 产物 | 每个官方稳定版对应一个 Release，tag `v<官方版本>-harmony-preview.<N>` |
| 包名 | `app.mihon.debug`（nightly 构建类型自带后缀——官方 v0.21.0 把 preview 改名为 nightly，可与官方 `app.mihon` 并存） |
| 推荐安装文件 | `mihon-<tag>-arm64-v8a.apk` |
| 构建方式 | GitHub Actions `.github/workflows/harmony_preview.yml` |
| 触发 | 每天 UTC 04:17 定时 + 手动 `workflow_dispatch`（支持 `dry_run`） |
| 补丁检查 | `.github/workflows/check_patches.yml`：补丁改动时 + 每周一，试套官方最新稳定版（必须成功）和 `main`（只警告） |
| 签名 | 自建密钥，存放于仓库 Secrets；备份见 §6 |
| 应用内更新 | 已启用，指向本仓库 Release |

已发布版本：

- `v0.20.4-harmony-preview.1` —— 首个 preview 构建，**没有**应用内更新器（旧 fork 流水线）。
- `v0.20.4-harmony-preview.2` —— 加入应用内更新器（旧流水线）。
- `v0.20.4-harmony-preview.3` —— 加入 CBZ 临时目录 / 残留容错（旧流水线）。
- 从 2026-10-03 起由本补丁流水线构建；补丁内容与 preview.3 完全一致（已用两套流程产出的源码树逐文件比对确认）。
  切换当天用 `dry_run` 构建了 `v0.20.4-harmony-preview.4` 的 APK 做验证（未发布）：包名 `app.mihon.debug`、versionCode 2904、
  versionName `0.20.4-harmony.4-7876`、签名证书与 preview.3 相同、ZIP 条目数相同。
- `v0.20.4-harmony-preview.4` —— 2026-10-06，加入补丁 0004（数据库 busy timeout / 连接池配置），修复 `database is locked` 闪退。
  是补丁流水线发布的第一个正式版本（versionCode 2904）。
- `v0.20.4-harmony-preview.5` —— 2026-10-06，加入补丁 0005（后台保活：静音音轨 + 唤醒锁，下载服务改 `mediaPlayback` 类型，
  设置 → 下载 新增开关）。修复卓易通后台冻结导致下载停住、以及由此触发的 dataSync 6 小时超时闪退（versionCode 2905）。
- `v0.20.4-harmony-preview.6` —— 2026-10-06，加入补丁 0006（下载通知统一为 Animeko 样式：数量标题、速度 + 进度正文、
  进度条、展开显示当前项；新文件 `DownloadSpeedMeter.kt`）。与 anikku-harmony preview.4、animeko-harmony harmony.7 同一轮
  （versionCode 2906）。
- `v0.20.4-harmony-preview.7` —— 2026-10-06，加入补丁 0007（启动时删除已安装完成的 `update.apk`）。Mihon 的更新流程本身在卓易通里一直正常，
  这一版只是跟 anikku-harmony preview.5 / animeko-harmony harmony.8 一起把"更新包残留在缓存里"统一清掉（versionCode 2907）。
- `v0.20.4-harmony-preview.8` —— 2026-10-06，加入补丁 0008（检查更新先读 `repo` 分支的 `releases.json` 镜像，再退回 `api.github.com`）。
  起因是 Anikku 用户撞上匿名 GitHub 接口每 IP 每小时 60 次的配额（HTTP 403）；Mihon 走同一条路，只是还没撞上。
  与 anikku-harmony preview.7 / animeko-harmony harmony.9 同一轮（versionCode 2908）。
- `v0.20.4-harmony-preview.9` —— 2026-10-11，加入补丁 0009（FlexibleAdapter 改从 Maven Central 取，构建修复）和 0010（移植 anikku-harmony 0016：
  目录改名 `moveDocument` / 合并 / 校验 / 重试，下载队列显示失败原因）。起因是 Anikku 用户的「下载 100% 后变 !」；Mihon 的 0001 是同一份
  `renameToOrCopy`，按跨 App 规则一起改（versionCode 2909）。
- `v0.20.4-harmony-preview.10` —— 2026-10-12，加入补丁 0011（点「下载」被静默跳过的修复：按下载缓存判断已下载、磁盘残留目录完整则登记 / 不完整则删掉重下、
  漫画页面 Snackbar 说明没入队的原因）和 0012（崩溃日志过滤卓易通图形层噪音 + 附应用自己的最近 600 行日志）。起因是用户上报「有个资源点了下载按钮卡了一下但没开始」，
  导出的 crash log 里 701 行有 690 行是卓易通噪音、Mihon 自己只剩 3 行（versionCode 2910）。
- `v0.20.4-harmony-preview.11` —— 2026-10-12，加入补丁 0013（重试失败章节不再弹「已在队列中」）。preview.10 发出后自查发现的，与 Anikku preview.10 同一轮（versionCode 2911）。
- `v0.21.0-harmony-preview.1` —— 2026-10-12，**补丁系列 rebase 到官方 v0.21.0**（v0.20.4 之后 273 个提交：Metro DI、preview 构建类型改名 nightly、
  `DownloadJob` / `LibraryUpdateJob` 改 Worker、`AppUpdateDownloadJob` 删除、`DownloadNotifier` 与下载队列 API 重写、签名改读 `storeFile`）。
  功能与 preview.11 相同；0004（busy_timeout）/ 0009（FlexibleAdapter）因上游已含而删除，其余补丁号不变（§5.1 有逐张要点）。
  流水线：解码密钥到文件给 `storeFile`、按源码树自动识别 nightly / preview 构建类型、`assembleNightly`。
  versionCode 3601（上游 36 × 100 + 1），versionName `0.21.0-harmony.1-8157`，包名仍 `app.mihon.debug`，签名不变，可从 v0.20.4 系列直接覆盖（升级前先在 App 里备份，见 README）。
- `v0.21.0-harmony-preview.2` —— 2026-10-12，加入补丁 0014：书架 / 浏览页新增显示模式「全景松散网格」（从 anikku-harmony 0015 + 0020 移植：横版封面按 3:2 画、瀑布流排布、自动列宽 168 dp）。versionCode 3602。
- `v0.21.1-harmony-preview.1` —— 2026-10-12，**定时任务自动发布**：官方 v0.21.1（versionCode 37）出来后 14 张补丁直接套上。功能与 v0.21.0-preview.2 相同，versionCode 3701。用户的 App 没看到它——见下一条。
- `v0.21.1-harmony-preview.2` —— 2026-10-12，加入补丁 0015（显示模式「全景紧凑网格」）、0016（瀑布流快速滚动条拇指不抽搐）、0017（更新器按版本号取最大，修「检查更新一直停在 v0.21.0-harmony-preview.2」）。versionCode 3702。装着 ≤ v0.21.1-preview.1 的用户这一次要手动装，之后更新检查就正常。
- `v0.21.1-harmony-preview.3` —— 2026-10-13，加入补丁 0018（全景格子形状持久化，滑动中不把新形状写进布局，封面横竖同一调用点）。versionCode 3703，versionName `0.21.1-harmony.3-8177`，签名与 preview.2 相同（`4bd90284…ea8a`）。模拟器（AVD harmony34，TCG）验过形状与落盘，掉帧要用户真机确认。
- `v0.21.1-harmony-preview.4` —— 2026-10-13，加入补丁 0019（全景网格连续 300 ms 不滚动才算停下来；浏览页提前学已加载、还没上屏的封面形状）。versionCode 3704，versionName `0.21.1-harmony.4-8178`，签名与 preview.3 相同（`4bd90284…ea8a`）。本轮 Mihon 只编译，没上模拟器（`PanoramaCoverShapes.kt` 与 Anikku 已测的 0027 逐字节相同）。
- `v0.21.1-harmony-preview.5` —— 2026-10-13，加入补丁 0020（瀑布流快速滚动条拇指不再大约每行回跳一下：位置跨帧累加，滚动中冻结总长度，停下后 150 ms 平滑）。versionCode 3705，versionName `0.21.1-harmony.5-8179`，签名与 preview.4 相同（`4bd90284…ea8a`）。正式 run 38424091586（15:47 UTC，target `3d89a0796`），arm64 26,940,093 B、SHA-256 `d9639da6…`；DEX 含新滚动条字段。发出时 `repo` 分支 `releases.json` 第一项是它（当时共 19 条）。**已发布但被 0.21.2 系取代，不要装**：3705 低于同日定时任务发出的 `v0.21.2-harmony-preview.1`（3801），手机提示版本过老拒装。Release 保留未删（更新器取最高版本，不会推给已在 0.21.2 的用户）。
- `v0.21.2-harmony-preview.1` —— 2026-10-13，**定时任务自动发布**。上游 Mihon 2026-10-13 04:27 UTC 发了 v0.21.2；定时 run 38392710194（11:47 UTC，target `f32a21972`，含补丁 0001–0019）套上后发布。versionCode 3801。功能同当时的 v0.21.1-harmony-preview.4（还没有 0020）。用户手机升到了它。
- `v0.21.2-harmony-preview.2` —— 2026-10-13，含补丁 0020，已被 preview.3 取代。同一套 20 张补丁（含 0020）在干净 v0.21.2 树 `/tmp/mihon-verify212` 套用成功（`prepare-source.sh … v0.21.2 2`，versionCode 3802）。跳过单独 dry_run：0.21.2 preview.1 已用前 19 张编过，0020 只改 `VerticalFastScroller.kt`，正式 run 编译失败不会发布。正式 run 38427442080（16:09 UTC，target `3d89a0796`）。`app.mihon.debug` versionCode 3802、versionName `0.21.2-harmony.2-8191`，签名 `4bd90284…ea8a` 不变，arm64 26,956,473 B、SHA-256 `1a9cd9d5…`，DEX 含新滚动条字段。`repo` 分支 `releases.json` 前三项 `v0.21.2-harmony-preview.2`、`v0.21.2-harmony-preview.1`、`v0.21.1-harmony-preview.5`（共 20 条）。拇指顺不顺要用户在这一版上真机确认。0021 起这套估算已删除。
- `v0.21.2-harmony-preview.3` —— 2026-10-13，已被 preview.4 取代。加入补丁 0021（自建全景瀑布流：末尾不再左空、列数变化当帧重排、滚动条用真实内容高度）。versionCode 3803，versionName `0.21.2-harmony.3-8192`，签名与 preview.2 相同（`4bd90284…ea8a`）。开发树 `/tmp/mihon-verify212` `dev-0021` 提交 `08bd109`（底座 v0.21.2 + 0001–0020），流水线 `e5c6c734e`。`:presentation-core:spotlessCheck` `:app:spotlessCheck` 通过，`:presentation-core:testDebugUnitTest` 16/16，`:app:compileNightlyKotlin` 通过。干净 v0.21.2 树套 21 张成功，12 个改动文件 `cmp` 一致。`check_patches` run 38453485932、`dry_run` run 38453484931、正式 run 38454541710 均成功。arm64 26,940,089 B（SHA-256 前缀 `58ea2694f782`），universal 67,249,088 B，DEX 含 `PanoramaMasonryLayout`。`repo` 分支 `releases.json` 第一条即此版，共 21 条。未上模拟器。与 anikku-harmony 0030 同源。
- `v0.21.2-harmony-preview.4` —— 2026-10-14，已被 preview.5 取代。加入补丁 0022（更新页下载：专用客户端重试 + Range 续传，失败在更新说明上方用红字写原因）。versionCode 3804，versionName `0.21.2-harmony.4-8193`，签名与 preview.3 相同（`4bd90284…ea8a`）。开发树 `/tmp/mihon-verify212` 分支 `dev-0022` 提交 `e1a029d`（底座 v0.21.2 + 0001–0021 + 0022），流水线 `779cccafc`。主代理复跑 `:app:spotlessCheck :app:compileNightlyKotlin :app:testDebugUnitTest --tests '*AppUpdateApkDownloaderTest*'` 退出 0，3/3、skipped 0。干净 v0.21.2 以 N=4 套全部 20 张（0001–0022，0004 / 0009 早已删除） → versionCode 3804，与开发树只差版本号。`check_patches` run 38512243044、`dry_run` run 38512260459、正式 run 38513011212 均成功。Release 非 draft、非 prerelease，target `779cccafc`。arm64 26,942,369 B（SHA-256 前缀 `fbcf9c960068`），universal 67,251,368 B，DEX 含 `Update download attempt`、`update.apk`，资源含 `harmony_update_download_timeout`。`repo` 分支 `releases.json` 22 条，第一条即此版。从旧版升到这一版时，点下载的仍是旧代码，第一下可能还会失败，再点即可；从 preview.4 往后的更新才自动重试。Anikku 不适用；Animeko 待确认。
- `v0.21.2-harmony-preview.5` —— 2026-10-14 07:39 UTC，已被 preview.6 取代。加入补丁 0023–0029（返回位置按 key 记、布局世代、封面形状按版本通知、滚动条按下即抓、自动列宽分档、瀑布流滚动条不再每帧重启），与 anikku-harmony 0031–0037 一一对应、同源。versionCode 3805，versionName `0.21.2-harmony.5-8200`，签名与 preview.4 相同（`4bd90284…ea8a`）。流水线 `0066de0e4`。`check_patches` run 38527739609、`dry_run` run 38527787706、正式 run 38529020510 均成功。`app.mihon.debug`，arm64 26,942,369 B（SHA-256 前缀 `1f52f85fbac7`），universal 67,251,368 B。DEX 含 `PanoramaColumns$Tiered`、`holdOpaqueWhileThumbGrabbed`、`PanoramaMasonryContentEpoch`。`repo` 分支 `releases.json` 23 条，第一条即此版。子代理（grok-4.7-high-fast）实现；主代理复跑 `:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin --rerun-tasks` 通过（presentation-core 35 个用例，0 失败，2 个门控跳过；app 28 个，0 失败）。干净树 `/tmp/mihon-verify213`（v0.21.2，N=5）套用成功，12 个改动文件与开发树 `cmp` 一致。没有真机 / 模拟器手势测试。`PanoramaMasonry.kt` / `PanoramaMasonryLayout.kt` / `PanoramaMasonryLayoutTest.kt` 与 Anikku 逐字节相同。series 27 张（0001–0029，0004 / 0009 已删）。
- `v0.21.2-harmony-preview.6` —— 2026-10-14 10:31 UTC，已被 preview.7 取代。加入补丁 0030–0032（`PanoramaColumns.Shaped`、形状模式、滚动条热区收回为绘制宽度），与 anikku-harmony 0038–0040 一一对应、同源。versionCode 3806，versionName `0.21.2-harmony.6-8203`，签名与 preview.5 相同（`4bd90284…ea8a`）。流水线 `e8220fba2`。`check_patches` run 38548385048、`dry_run` run 38548395586、正式 run 38549485379 均成功。`app.mihon.debug`，arm64 26,958,753 B（SHA-256 前缀 `e7233bbfcd39`），universal 67,267,752 B。DEX 含 `PanoramaColumns$Shaped`、`PanoramaShapeMode`、`committedShapeVersion`。manifest 无 ui-test 的 ComponentActivity。DEX 里的 `robolectric` 字符串 5 处，与上一版相同，来自第三方库的运行时检测，不是新依赖进包。`repo` 分支 `releases.json` 24 条，第一条即此版。子代理（grok-4.7-high-fast）实现；主代理复跑 `:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin --rerun-tasks` 通过（presentation-core 51 个用例，0 失败，2 跳过；app 35 个）。干净树 `/tmp/mihon-verify214`（v0.21.2，N=6）套用成功，18 个改动文件与开发树 `cmp` 一致。没有真机手势测试。三个共享文件与 Anikku 0038–0040 逐字节相同。series 30 张（0001–0032，0004 / 0009 已删）。
- `v0.21.2-harmony-preview.8` —— 2026-10-14 12:01 UTC，已被 preview.9 取代。加入补丁 0034（全景滚动没碰到两端时返回精确 delta），与 anikku-harmony 0042 同源。versionCode 3808，versionName `0.21.2-harmony.8-8205`，签名与 preview.7 相同（`4bd90284…ea8a`）。流水线 `00a9ff810`。`check_patches` run 38558901975、`dry_run` run 38558925925、正式 run 38559877474 均成功。这次 dry_run 成功后才触发正式 run，等待脚本已修好。`app.mihon.debug`，arm64 26,958,753 B（SHA-256 前缀 `79476a3a4758`），universal 67,267,752 B。体积与 preview.7 相同，是对齐填充，分辨版本看 SHA-256 / versionCode。manifest 无 ui-test。`repo` 分支 `releases.json` 26 条，第一条即此版。开发树 `dev-0023` 提交 `be7349e`。`:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin` 通过（presentation-core 55 个用例，0 失败，2 跳过；app 35 个）。干净树 `/tmp/mihon-verify216`（v0.21.2，N=8）套用成功，20 个改动文件与开发树 `cmp` 一致。`PanoramaMasonry.kt` 与 Anikku 0042 逐字节相同。0033 的诊断日志保留。series 32 张（0001–0034，0004 / 0009 已删）。
- `v0.21.2-harmony-preview.7` —— 2026-10-14 11:15 UTC，已被 preview.8 取代。加入补丁 0033（全景网格滑动诊断，不改滚动行为），与 anikku-harmony 0041 同源。versionCode 3807，versionName `0.21.2-harmony.7-8204`，签名与 preview.6 相同（`4bd90284…ea8a`）。流水线 `15289c4df`。`check_patches` run 38553790858、`dry_run` run 38553801784、正式 run 38553912820 均成功。`app.mihon.debug`，arm64 26,958,753 B（SHA-256 前缀 `9f97e5d14716`），universal 67,267,752 B。体积与 preview.6 相同，是对齐填充，分辨版本看 SHA-256 / versionCode。DEX 含 `Panorama scroll trace`、`gapLastMove=`、`fling start v=`。manifest 无 ui-test。`repo` 分支 `releases.json` 25 条，第一条即此版。开发树 `dev-0023` 提交 `7b0bddc`。`:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin` 通过（presentation-core 54 个用例，0 失败，2 跳过；app 35 个）。干净树 `/tmp/mihon-verify215`（v0.21.2，N=7）套用成功，20 个改动文件与开发树 `cmp` 一致。`PanoramaScrollTrace.kt` / `PanoramaMasonry.kt` 与 Anikku 0041 逐字节相同。series 31 张（0001–0033，0004 / 0009 已删）。不改滑动手感。正式 run 在 dry_run 结束前就触发了（等待脚本把一次 API 报错当成完成）；正式 run 在同一并发组里排队，等 dry_run 成功后才执行，结果无影响。
- `v0.21.2-harmony-preview.9` —— 2026-10-14 12:51 UTC，已被 preview.10 取代。加入补丁 0035（滚动条：按在画出来的拇指上立即抓；拇指旁边 20 dp 要按住 120 ms 不动才抓），与 anikku-harmony 0043 同源。versionCode 3809，versionName `0.21.2-harmony.9-8206`，签名与 preview.8 相同（`4bd90284…ea8a`）。流水线 `143b93517`。`check_patches` run 38564906465、`dry_run` run 38564985618、正式 run 38566077398 均成功（dry_run 成功后才触发正式 run）。`app.mihon.debug`，arm64 26,958,757 B（SHA-256 前缀 `01b7d412a7a6`），universal 67,267,756 B。manifest 无 ui-test。开发树 `dev-0023` 提交 `e1621be`（发版时为 `6d579ec`，之后只改了提交信息里的同源编号，代码相同）。`VerticalFastScroller.kt` 的 Harmony 段与 Anikku 0043 相同（Anikku 多第四根滚动条）。series 33 张（0001–0035，0004 / 0009 已删）。
- `v0.21.2-harmony-preview.10` —— 2026-10-14 13:35 UTC，已被 preview.11 取代。加入补丁 0036（滚动性能记录器：设置 → 高级 →「滚动性能记录（调试）」，左下角「记录」按钮导出脱敏的帧耗时文件），与 anikku-harmony 0044 同源。versionCode 3810，versionName `0.21.2-harmony.10-8207`，签名与 preview.9 相同（`4bd90284…ea8a`）。流水线 `bdcc008e0`。`check_patches` run 38570494789、`dry_run` run 38570546143、正式 run 38572070546 均成功。`app.mihon.debug`，arm64 26,976,657 B（SHA-256 前缀 `0df8d7c4aea7`），universal 67,285,656 B。DEX 含 `harmony_scroll_perf_recorder`、`FrameMetrics 未提供`、`privacy: no titles`、`mark user`，preview.9 没有。manifest 无 ui-test。开发树 `dev-0023` 提交 `9f61aef`（发版时为 `46e8ef9`，代码相同），`:presentation-core:testDebugUnitTest :app:testDebugUnitTest` 通过（presentation-core 59 个用例，0 失败，2 跳过；app 41 个）。发版时 `HarmonyFramePerf.kt` / `PanoramaFrameCounters.kt` / `PanoramaScrollTrace.kt` / `PanoramaMasonry.kt` / `HarmonyFramePerfTest.kt` 与 Anikku 0044 逐字节相同；0037 起 `HarmonyFramePerf.kt` 不再与 Anikku 0044 逐字节相同。分析脚本在归档仓 `tools/scroll-perf-analyze/analyze.py`。series 34 张（0001–0036，0004 / 0009 已删）。发版后 `repo` 分支 `releases.json` 的第一条仍是 preview.9：GitHub「列出 Releases」接口不按创建时间排序，preview.10 排在第 7 位（下标 6）。App 端按版本号取最大，不受影响。`write-release-index.sh` 已改为翻完所有页、按 `created_at` 倒序取 30 条（`1db0e3620`，`release_index` run 38574198250），当时第一条是 preview.10，共 28 条。preview.11 起为 29 条、第一条 preview.11。
- `v0.21.2-harmony-preview.11` —— 2026-10-14 约 16:25 UTC，已被 preview.12 取代。加入补丁 0037–0040（记录器补上被丢掉的 FrameMetrics 报告、各阶段分位数和长按对照开关；滑动中学到的跨档形状等停稳再提交；浏览预取默认只读封面文件头；翻页追加不再整表重排）。versionCode 3811，versionName `0.21.2-harmony.11-8211`，签名与 preview.10 相同（`4bd90284…ea8a`）。流水线 `33568c567`。`check_patches` run 38595775346、`dry_run` run 38595854992、正式 run 38597112426 均成功。`app.mihon.debug`，arm64 27,009,425 B（SHA-256 前缀 `544cefae3f39`），universal 67,318,424 B。DEX 含 `harmony-scroll-perf`、`HarmonyPerfToggles`、`HarmonyFramePerfSampler`、`mark toggle`、`harmony_fade`、`cpu_pool`、`privacy: no titles`。开发树 `/tmp/mihon-verify212` 分支 `dev-0024` HEAD `005f27b`（0037=`400fd6c`，0038=`6a7156b`，0039=`14f48c5`，0040=`005f27b`）。`spotlessCheck`、`:app:compileNightlyKotlin`、`:presentation-core:testDebugUnitTest`、`:app:testDebugUnitTest` 通过（presentation-core 65 个用例，0 失败，2 跳过；app 49 个，0 失败）。干净树 `/tmp/mihon-verify217`（v0.21.2，N=11）套用后，除 `app/build.gradle.kts` 的版本号 / 更新器行外，改动文件与开发树 `cmp` 一致。`HarmonyFramePerf.kt` / `HarmonyPerfToggles.kt` 计划与 anikku-harmony 0044 逐字节同源，**Anikku 侧待移植**。0038 / 0039 / 0040 与 anikku-harmony 0025/0027、0027、0030 同一份做法，Anikku 本轮没改，同病待修。分析脚本在归档仓 `tools/scroll-perf-analyze/analyze.py`（当时认导出格式 `harmony-scroll-perf` 2；0041 起改为 3）。series 38 张（0001–0040，0004 / 0009 已删）。`repo` 分支 `releases.json` 当时 29 条、第一条 preview.11（该索引提交的 SHA 待确认）。约 16:52 UTC 的两份记录把「报帧被丢」排除（drops 全是 0），并看到 0038 / 0039 加重了占位先横后缩，见 §5.1 0041–0045。Animeko 没有全景瀑布流网格，也没有 `HarmonyFramePerf`，不适用。
- `v0.21.2-harmony-preview.12` —— 2026-10-14 约 19:10 UTC，**当前版本**。加入补丁 0041–0045（记录器少读线程并统计已组合格子，导出格式 3；全景占位跟着书架、已放下的格子留在原槽；展开窗口上自动列加宽；浏览格子不再每帧读分页；全景浏览在显示前读封面尺寸）。versionCode 3812，versionName `0.21.2-harmony.12-8216`，签名与 preview.11 相同（`4bd90284…ea8a`）。流水线 `fcd0c73bb`。`check_patches` run 38618709323、`dry_run` run 38618768446、正式 run 38619981541 均成功。`app.mihon.debug`，arm64 27,009,425 B（与 preview.11 相同，是对齐填充；SHA-256 前缀 `3e2012802777`），universal 67,318,424 B。DEX 含 `HarmonyCoverHeaderProbe`、`idle_holes`、`cpu_smpl`、`HarmonyPerfSmpl`、`PanoramaMasonryTailEpoch`。开发树 `/tmp/mihon-verify212` 分支 `dev-0025` HEAD `f1adecd`（0041=`39f004f`，0042=`b25f1fb`，0043=`6122cf3`，0044=`805c66e`，0045=`f1adecd`）。本地 `spotlessCheck`、`:app:compileNightlyKotlin`、`:presentation-core:testDebugUnitTest`、`:app:testDebugUnitTest` 通过（presentation-core 71 个用例，69 通过，2 跳过；app 70 个通过）。干净树 `/tmp/mihon-verify219`（v0.21.2，N=12）套用后，除 `app/build.gradle.kts` 外，改动文件与开发树 `cmp` 一致。grok 子代理在 4 个隔离 worktree 里实现；独立 grok 复核 0 个高、4 个中、3 个低，都已修。`HarmonyFramePerf.kt` 与 anikku-harmony 0044 计划逐字节共用，**Anikku 0041–0045 待移植**。0042 与 anikku-harmony 0025 / 0027 / 0030 同病；0043 与 Anikku 的同一条自动列规则同病。分析脚本在归档仓 `tools/scroll-perf-analyze/analyze.py`（已认 `harmony-scroll-perf` 3，含夹具 `fixtures/scroll_perf_v3_sample.txt`）。series 43 张（0001–0045，0004 / 0009 已删）。`repo` 分支 `releases.json` 30 条、第一条 preview.12（该索引提交的 SHA 待确认）。Animeko 没有全景瀑布流网格，也没有 `HarmonyFramePerf`，不适用。真机是否不再先宽后缩、展开横屏是否 5 列，见 §7。

## 3. 仓库结构

```
patches/series                 # 套用顺序, 每行一个文件名, # 开头为注释
patches/0001-*.patch           # git format-patch 格式, 基于官方 v0.20.4 生成
patches/0002-*.patch
patches/0003-*.patch
patches/0004-*.patch
patches/0005-*.patch
patches/0006-*.patch
patches/0007-*.patch
patches/0008-*.patch
patches/0009-*.patch           # 依赖回迁, 上游稳定版自带后 prepare-source.sh 自动跳过
patches/0010-*.patch
patches/0011-*.patch
patches/0012-*.patch
patches/0013-*.patch           # 0011 的补充: 重试失败章节不算「已在队列」
patches/0014-*.patch           # 显示模式「全景松散网格」(Anikku 0015 + 0020 的移植)
patches/0015-*.patch           # 显示模式「全景紧凑网格」(与 Anikku 0022 同源)
patches/0016-*.patch           # 瀑布流快速滚动条拇指不抽搐 (与 Anikku 0023 同源)
patches/0017-*.patch           # 更新器按版本号取最大而不是列表第一项 (与 Anikku 0024 同源)
patches/0018-*.patch           # 全景格子形状持久化 + 滑动中不改排版 (PanoramaCoverShapes.kt 与 Anikku 0025 逐字节相同)
patches/0019-*.patch           # 全景网格静止判断加 300 ms + 浏览页提前学封面形状 (PanoramaCoverShapes.kt 与 Anikku 0027 逐字节相同)
patches/0020-*.patch           # 瀑布流快速滚动条拇指不再每行回跳 (StaggeredGridEstimate 段与 Anikku 0028 逐字节相同; 0021 起整段删除)
patches/0021-*.patch           # 自建全景瀑布流: 阅读顺序容差 + 列数变化当帧重排 (PanoramaMasonry*.kt 与 Anikku 0030 逐字节相同)
patches/0022-*.patch           # 更新下载: 专用客户端重试 + Range 续传 + 失败原因 (AppUpdateApkDownloader.kt)
patches/0023-*.patch           # 全景自动列适合竖封面; 横封面 ≥3 列时跨两列 (与 Anikku 0031 同源)
patches/0024-*.patch           # 全景滚动锚点按 key 存, 列表加载完整后再恢复 (与 Anikku 0032 同源)
patches/0025-*.patch           # 全景布局世代: 内容不变时跳过逐项计算 (与 Anikku 0033 逐字节相同)
patches/0026-*.patch           # 封面形状表按版本通知, 不再整表订阅 (与 Anikku 0034 同源)
patches/0027-*.patch           # 滚动条按下即抓, 按住不淡出 (列表/网格/瀑布流; 与 Anikku 0035 同源)
patches/0028-*.patch           # 自动列宽按网格宽分档 Tiered (常量在 LibraryComfortableGrid.kt; 与 Anikku 0036 同源)
patches/0029-*.patch           # 瀑布流滚动条单个 LaunchedEffect + snapshotFlow (与 Anikku 0037 同源)
patches/0030-*.patch           # 全景自动列 Shaped: 面积大致恒定, 列宽由主导形状推出 (与 Anikku 0038 逐字节相同)
patches/0031-*.patch           # 形状模式 Tall/Wide/Unknown (PanoramaShapeMode.kt 在 app 层; 与 Anikku 0039 同源)
patches/0032-*.patch           # 滚动条热区收回为绘制宽度 ThumbThickness + endInset (与 Anikku 0040 同源)
patches/0033-*.patch           # 全景滑动诊断: 崩溃日志附最近 400 条轨迹, 不改滚动行为 (PanoramaScrollTrace.kt / PanoramaMasonry.kt 与 Anikku 0041 逐字节相同)
patches/0034-*.patch           # 全景滚动没碰到两端时返回精确 delta (PanoramaMasonry.kt 与 Anikku 0042 逐字节相同; 0033 诊断日志保留)
patches/0035-*.patch           # 滚动条: 按在拇指上立即抓, 拇指旁 20 dp 按住 120 ms 才抓 (与 Anikku 0043 同源)
patches/0036-*.patch           # 滚动性能记录器 + 「记录」按钮导出脱敏文件 (发版时 HarmonyFramePerf.kt 等与 Anikku 0044 逐字节相同; 0037 起格式 2, 0041 起格式 3, 不再逐字节相同)
patches/0037-*.patch           # 记录器补丢帧计数、阶段分位数、封面加载和长按对照开关 (导出 harmony-scroll-perf 2; 0041 起改为 3; HarmonyFramePerf.kt / HarmonyPerfToggles.kt 计划与 Anikku 0044 逐字节同源, Anikku 待移植)
patches/0038-*.patch           # 滑动中学到的跨档形状等网格停稳再提交 (与 Anikku 0025/0027 同一份做法, 本轮 Anikku 没改; 0042 改掉「一律等停稳」, 见下)
patches/0039-*.patch           # 浏览页全景预取默认只读封面文件头 (与 Anikku 0027 同一份做法, 本轮 Anikku 没改; 0042 起滑动中不再暂停预取)
patches/0040-*.patch           # 全景瀑布流翻页追加, 不再整表重排 (此前与 Anikku 0030 逐字节相同的那份文件, 本轮 Anikku 没改)
patches/0041-*.patch           # 记录器少读 /proc 线程、统计已组合格子 (导出 harmony-scroll-perf 3; HarmonyFramePerf.kt 计划与 Anikku 0044 逐字节共用, Anikku 待移植)
patches/0042-*.patch           # 全景占位跟着书架, 已放下的格子留在原槽 (与 Anikku 0025/0027/0030 同病, 待移植)
patches/0043-*.patch           # 展开窗口上自动列加宽 (112/140/176 dp; 与 Anikku 同一条自动规则, 待移植)
patches/0044-*.patch           # 浏览格子不再每帧读分页 (contentType / derivedStateOf / SideEffect, 同病待移植)
patches/0045-*.patch           # 全景浏览显示前读封面尺寸 HarmonyCoverHeaderProbe.kt (同病待移植)
scripts/prepare-source.sh      # 官方源码 → 套补丁 → 改版本号, 每步一个 commit
scripts/write-release-index.sh # Releases 接口返回 → repo 分支的 releases.json / latest.json
.github/workflows/harmony_preview.yml   # 每日构建发布, 最后写 Release 索引
.github/workflows/release_index.yml     # Release 被手动增删改时重写索引 (也可手动触发)
.github/workflows/check_patches.yml     # 补丁可套用性检查
docs/MAINTENANCE.md            # 本文
README.md                      # 面向用户的说明 + 补丁一览
LICENSE                        # Apache-2.0 (沿用上游)
```

旧 fork 布局（`.github/patches/harmony.patch` + workflow 内嵌 Python + 整文件覆盖目录 + `downloader.py`）
已全部折算进 0001–0003 三个标准补丁，不再有「字符串锚点替换」这种脆弱机制。

## 4. 构建流程（`harmony_preview.yml` 做了什么）

1. **解析版本**：`upstream_tag`（为空则调 GitHub API 取 `mihonapp/mihon` 最新稳定版）、`patch_number`（默认 1）。
   `release_tag = <upstream_tag>-harmony-preview.<N>`。
2. **跳过已存在的 Release**（`dry_run` 时不跳过）。这是定时任务不重复编译的关键。同一段「Resolve release version」里，非 `dry_run` 且目标 tag 还不存在时，取本仓所有 `vX.Y.Z-harmony-preview.N`，按「上游版本.N」做 `sort -V`，比已发布最高的旧就 `exit 1`，日志「installs would be a downgrade」。已存在的 tag 仍走原来的 skip，每天定时 run 不会因此变红。
3. **校验四个签名 Secrets 非空**。
4. **拉官方源码**：`git clone --branch <tag> --single-branch`（完整历史，约 80 MB、几秒钟）。nightly 构建的
   `versionNameSuffix` 和 `BuildConfig.COMMIT_COUNT` 来自 `git rev-list --count HEAD`，浅克隆会让它变成个位数。
   同时读出官方 `.github/.java-version` 作为 JDK 版本。
5. **`scripts/prepare-source.sh <src> <tag> <N>`**：
   - 逐个 `git apply --3way patches/<file>` 并 commit；任何一个套不上就失败退出，并打印是哪个补丁。
   - `FORK_REPO` 环境变量（workflow 传 `github.repository`）与默认值 `Xun2202/mihon-harmony` 不同时，
     把更新器指向的仓库改掉——方便别人 fork 本仓库后直接用。
   - `versionCode = 官方 versionCode × 100 + N`，`versionName = "<官方版本>-harmony.<N>"`，提交。
6. **编译**：`./gradlew assembleNightly -Penable-updater`（源码树里有 `create("nightly")` 时；v0.20.4 及更早是 `assemblePreview`，
   workflow 的 `Resolve build type` 步骤按 `app/build.gradle.kts` 自动选）
   - `assembleNightly`：nightly 构建类型（官方 v0.21.0 起的名字，之前叫 preview）→ Private 安装器可见，包名 `app.mihon.debug`，
     产物在 `app/build/outputs/apk/nightly/app-{arm64-v8a,universal}-nightly.apk`。
   - `-Penable-updater`：`BuildConfig.UPDATER_ENABLED = true`，否则 App 不检查更新（0.21 的 `Config.enableUpdater` 仍读这个 flag；
     不传 `-Pdist` 即 LOCAL 发行，不含 Firebase 遥测）。
   - 签名：先把 `SIGNING_KEY` base64 解码到 `$RUNNER_TEMP/harmony.keystore`；`MIHON_GITHUB_RELEASE=true` 时 `app/build.gradle.kts`
     从 `storeFile`（v0.21.0 起，文件路径）/ `storeFileBase64`（v0.20.4 及更早）+ `storePassword / keyAlias / keyPassword` 读取密钥，两种变量都注入。
7. **发布**：APK 重命名为 `mihon-<tag>-{arm64-v8a,universal}.apk`，上传 artifact；非 `dry_run` 时
   `gh release create <tag> --target $GITHUB_SHA`，说明里列出补丁 Subject 和 SHA-256。
   - **不推送 tag 到源码**。默认 `GITHUB_TOKEN` 无权推送含 workflow 文件改动的提交，所以让 `gh release create` 直接在 `main` 当前提交上建 tag。
   - **不要**把 `.sha1` / `.sha256` 之类的文件当作 Release 资产上传：更新器用「文件名含 `-arm64-v8a`」挑 APK，
     `mihon-xxx-arm64-v8a.apk.sha1` 会把下载链接顶掉。校验值只写进 Release 说明。
8. **Release 索引**：`scripts/write-release-index.sh` 把 `gh api --paginate repos/<repo>/releases` 的条目按 `created_at` 倒序取前 30 条存成 `releases.json`（字段原样；接口顺序不按创建时间）、`jq` 取最新正式版存成 `latest.json`，
   连同说明 `README.md` 提交到孤儿分支 `repo`（被并发推送拒绝就重取重写，最多 3 次）。应用内更新器（0008 起）优先读
   `https://raw.githubusercontent.com/Xun2202/mihon-harmony/repo/releases.json`。`GITHUB_TOKEN` 创建的 Release 不触发 `release` 事件，所以必须在这里写；
   手动改 Release 时由 `release_index.yml` 兜底。`repo` 分支不要手改。

## 5. 补丁维护（最常见的工作）

### 5.1 官方出新版，`check_patches` 或 `harmony_preview` 报补丁套不上

```bash
# 1. 拿官方新版源码
git clone --branch v0.21.0 --single-branch https://github.com/mihonapp/mihon.git /tmp/mihon && cd /tmp/mihon

# 2. 逐个套补丁, 停在失败的那一个
git am --3way /path/to/mihon-harmony/patches/0001-*.patch   # 成功
git am --3way /path/to/mihon-harmony/patches/0002-*.patch   # 假设这里冲突

# 3. 解决冲突 (编辑带 <<<< 的文件, 保持补丁意图), 然后
git add -A && git am --continue
git am --3way /path/to/mihon-harmony/patches/0003-*.patch

# 4. 重新导出整组补丁, 覆盖 patches/ 下的旧文件 (文件名要和 series 一致)
git format-patch -o /path/to/mihon-harmony/patches v0.21.0..HEAD
# format-patch 生成的文件名是从 Subject 截断的, 重命名回 series 里的名字, 或者同步更新 series.

# 5. 提交推送到本仓库, check_patches 会自动验证; 然后手动触发 harmony_preview (可先 dry_run)
```

每个补丁的意图写在它的 commit message 里，解决冲突前先读一遍。**当前 series 基于官方 v0.21.0**（2026-10-12 rebase；每张补丁正文末尾
的「Rebased from the v0.20.4 series」段写了与 0.20.4 版的差别）。0.21 的大改动：Metro DI 取代 Injekt（`@Inject` 构造注入 / Worker 里 `graph.inject(this)` 字段注入）、
`preview` 构建类型改名 `nightly`、`DownloadJob` / `LibraryUpdateJob` → `DownloadWorker` / `LibraryUpdateWorker`、`AppUpdateDownloadJob` 删除、
`Downloader.queueChapters()` 改 `suspend` 且启动 Worker 的职责挪到 `DownloadManager.downloadChapters()`。
补丁 0001 和 0003 都改 `Downloader.kt`，上游重构下载器时两者通常要一起重做。
~~补丁 0004~~ 已随 v0.21.0 删除（上游 `DatabaseBindings.kt` 自带 `busy_timeout = 3000` + WAL）；编号不复用。
补丁 0005 触及 `DownloadWorker.kt` / `LibraryUpdateWorker.kt` 的 `setForegroundSafely()` 之后一行、`DownloadWorker.getForegroundInfo()` 的服务类型、
`DownloadPreferences.kt`、`SettingsDownloadScreen.kt`、manifest 和三份 strings.xml；`LibraryUpdateWorker` 多一个 `@Inject lateinit var downloadPreferences`
（0.21 用 Metro 字段注入，不再 `Injekt.get()`）；新文件 `BackgroundKeepAlive.kt` 独立无依赖，rebase 时通常只需重新定位那几行插入点。
补丁 0006 改 `DownloadNotifier.onProgressChange()`（正文重写，签名多了 `remaining: Int`；限流沿用 0.21 自带的 500 ms `@Synchronized` 版本，
0.20.4 系列里自带的 700 ms 限流已去掉；暂停通知是 0.21 的独立通知 `ID_DOWNLOAD_CHAPTER_PAUSED`，不动）和 `Downloader.kt` 三处
（`launchDownloaderJob()` 里 `previousJob?.join()` 之后的 1 Hz 定时器、每页完成后的 `notifier.onProgressChange(download, remainingDownloads())`、
`downloadImage()` 里 `countingInto(DownloadSpeedMeter)`），加 `remainingDownloads()` 辅助函数、三份 `strings.xml` / `plurals.xml`；新文件 `DownloadSpeedMeter.kt` 与 anikku-harmony 0010 的
同名文件逐字节相同，改其中一份要同步另一份。上游若再重写通知器，按 README 补丁表里的统一格式重做即可。
补丁 0007 三处：新文件 `data/updater/AppUpdateApkCleaner.kt`（`updateApk(context)` + `deleteInstalledApk(context)`，清理逻辑与 anikku-harmony 0011 逐字相同；
0.20.4 系列时它在 `AppUpdateDownloadJob` companion 里，0.21 删了那个类）、`App.onCreate` 里 `widgetManager.init(scope)` 之后的 `scope.launch(Dispatchers.IO) { ... }`、
`ui/more/NewUpdateScreenModel.kt` 的 `apkFile` 改为 `AppUpdateApkCleaner.updateApk(context)`（上游只在下载失败时删它）。上游若自己加了启动清理，整个补丁可以删掉。
补丁 0008 只改 `ReleaseServiceImpl`：新增 `listReleases(repository)`（镜像 URL `https://raw.githubusercontent.com/$repository/repo/releases.json`，
`networkService.client.newBuilder()` 三个超时都 10 秒；`CancellationException` 直接抛，其他异常 `logcat(WARN)` 后退回原来的 API URL），`latest()` 改调它。
镜像文件必须保持是接口原样返回，`GithubRelease` 的字段（`tag_name` / `body` / `html_url` / `assets[].name` / `assets[].browser_download_url`）一个都不能少。
与 anikku-harmony 0014 的 `listReleases()` 除 API URL 的 `?per_page=30` 外逐字相同，改一处要同步另一处。
~~补丁 0009~~ 已随 v0.21.0 删除（上游已用 Maven Central 的 `eu.davidea:flexible-adapter:5.1.0`）；编号不复用。`prepare-source.sh` 仍保留「能干净反向套用即视为上游已包含而跳过」的逻辑，
以后回移上游提交的补丁都可以靠它自然退役。
补丁 0010 改五处：`core/common/.../UniFileExtensions.kt`（整文件重写，与 anikku-harmony 0016 的同名文件**逐字节相同**，改一处同步另一处；
对应单元测试 `UniFileExtensionsTest` 8 个用例，上游若动 UniFile 封装先跑 `:core:common:testDebugUnitTest`）、`Downloader.kt`
（`stop()` 用 `fail(reason ?: harmony_download_interrupted)`；`downloadChapter()` 三处 `status = ERROR` 改 `fail(message)`，
`isDownloadSuccessful()` 为假时按页错误 / 目录内容拼原因并 `logcat(ERROR)`，收尾 `retryStorageOperation { tmpDir.renameToOrCopy(chapterDirname, context.contentResolver) }`；
新增 `retryStorageOperation()` 3 次 2 s / 4 s）、`model/Download.kt`（`error` 字段 + `fail()`，`status` setter 置非 ERROR 时清空）、
`ui/download/DownloadHolder.kt`（`notifyDownloadedPages()` 在 ERROR 时右侧显示「Error」、章节名下追加「出错：…」且 `maxLines = 3`；`bind()` 总是调用它）
与 `DownloadQueueViewModel.onStatusChange` 的 ERROR 分支多调一次 `onUpdateDownloadedPages`；四条字符串 `harmony_download_*` 在 `i18n` base / zh-rCN / zh-rTW。
CBZ 模式（0003 的 `finalizeArchive`）没有动：它本来就是单文件复制。
补丁 0011 改 `Downloader.kt`（`queueChapters()` 保持 0.21 的 `suspend`，返回新增的 `data class QueueResult(queued, alreadyDownloaded, alreadyQueued, sourceUnavailable, startDownloader)`——
0.21 原本返回 Boolean 让 `DownloadManager` 决定要不要 `startDownloads()`，这个布尔值现在装在 `startDownloader` 里；
「已下载」改用 `withContext(Dispatchers.IO) { cache.isChapterDownloaded(…) }`（0.21 去掉了 `skipCache` 参数，默认即走缓存），不再用上游新加的 `provider.findDownloadedChapterIds()` 磁盘探测；
`alreadyQueued` 用 id 集合判断；`downloadChapter()` **删掉**上游 0.21 新加的「`mangaDir.findFile(<章节>.cbz / <章节>)` 存在就直接 `cache.addChapter` + DOWNLOADED」早退（它不查完整性），
把临时目录的创建挪到 `try` 里、页列表之后，
先调新函数 `reuseOrRemoveExistingChapter(download, mangaDir, chapterDirname, pageCount)`：`provider.getValidChapterDirNames(...)` 逐个 `mangaDir.findFile`，
`countChapterImages()` 数目录文件或用 `archiveReader(context).useEntries` 数 `.cbz` 条目（规则抽成 `isCountedPageFile()`，与 `isDownloadSuccessful()` 共用），
≥ 页数 → `createNoMediaFile` + `cache.addChapter(name.removeSuffix(".cbz"), …)` + 删 `_tmp` / 私有缓存残留 + 返回 true；否则 `existing.delete()`，删不掉抛 `harmony_download_leftover_delete_failed`）、
`DownloadManager.downloadChapters()`（`result.startDownloader` 为真时 `startDownloads()`，再把 `QueueResult` 返回）、`MangaViewModel.downloadChapters()`（0.21 已是 `suspend`，
`result.skipped > 0` 时拼 Snackbar；因为 0.21 把入队放在 `appScope.launch { … }.join()` 里、之后才弹「加入书架」提示，Snackbar 改在 `viewModelScope.launch` 里弹以免阻塞；
`toggleAllSelection(false)` 0.21 已挪到调用方，补丁里不再调）、
五条字符串 `harmony_download_skipped*` / `harmony_download_leftover_delete_failed`（base / zh-rCN / zh-rTW）。`LibraryUpdateWorker` / `LibraryViewModel` / `UpdatesViewModel` / `ReaderViewModel` / `NotificationReceiver` 忽略返回值。
补丁 0012 改 `CrashLogUtil.kt`（`Runtime.exec(arrayOf("logcat", "*:$priority", "-d", "-v", "year", "-v", "zone"))` 读 stdout，`filterNoise()` 按 `HARMONY_NOISE_MARKERS`
六个子串过滤并计数，`logcatHeader()` 写「--- Logcat (N 卓易通 graphics-layer lines filtered: …) ---」，末尾追加「--- App log (last N lines …) ---」+ `HarmonyLogBuffer.snapshot()`）、
新文件 `util/system/HarmonyLogBuffer.kt`（`object : LogcatLogger`，`ArrayDeque` 600 行，`isLoggable(priority) = priority >= DEBUG`；与 anikku-harmony 0019 的同名文件**逐字节相同**）、
`App.kt`（`LogcatLogger.loggers += HarmonyLogBuffer`）。上游若把 `CrashLogUtil.dumpLogs` 的 logcat 命令改掉，只需保留 `filterNoise` 这段管道即可。
噪音特征取自用户 2026-10-12 的导出（HOP-AL10，701 行里 513 行 `BLASTBufferQueue`、82 行 tag 为包名的 `SurfaceDelegator` / `client is nullptr`、44 行 `HwAssetManagerEx`、38 行 `HwViewRootImpl`、6 行 `Display`）；再出现别的刷屏 tag 往 `HARMONY_NOISE_MARKERS` 里加一行即可。
补丁 0013 只改 `queueChapters()`：`alreadyQueued` 再按 `queuedDownloads[it.id]?.status == ERROR` 拆成 `retried` / `stillQueued`，`QueueResult` 多一个 `retried` 字段（不计入 `skipped`）。

补丁 0014 是 Anikku（KMK 血统）「全景封面」功能的精简移植，只保留网格部分，没有 Anikku 的 `usePanoramaCover` 开关——Mihon 直接多一个显示模式 `LibraryDisplayMode.ComfortableGridPanorama`（序列化 `COMFORTABLE_GRID_PANORAMA`，`values` 变 5 个，`LibraryFlagsTest` 的断言同步改 5）。
`MangaCover.kt` 新增 `Panorama(3f / 2f)` 和 `onCoverLoaded`（coil3 `AsyncImage.onSuccess`）；`CommonMangaItem.kt` 的 `MangaComfortableGridItem` 多 `usePanoramaCover` / `coverRatio` 参数，`coverRatio.floatValue <= 0.75f` 时格子按 3:2（`RATIO_SWITCH_TO_PANORAMA`，与 Anikku 常量同值）；
`LibraryComfortableGrid.kt` 全景模式走 `LazyLibraryStaggeredGrid`（`LazyLibraryGrid.kt` 新增，`columns == 0` 时 `StaggeredGridCells.Adaptive(PanoramaGridMinColumnWidth = 168.dp)`），`rememberCoverRatio(mangaId, usePanoramaCover)` 与 Anikku 0020 同一份逻辑（进程级 `ConcurrentHashMap`，全景模式未知封面默认 `9f / 16f`）；
`presentation-core` 的 `LazyGrid.kt` / `VerticalFastScroller.kt` 新增 `FastScrollLazyVerticalStaggeredGrid` / `VerticalStaggeredGridFastScroller`（与 anikku-harmony 0020 同源；唯一差异是拇指淡出：Mihon 这份文件没有 Anikku 的 `FadeOutAnimationSpec`，所以与同文件的 `VerticalGridFastScroller` 一样用 `.sample(0.1.seconds)` + `delay(ScrollBarVisibilityDuration)` + `ImmediateFadeOutAnimationSpec`）。`rememberCoverRatio` / `PanoramaGridMinColumnWidth` 是 internal（Anikku 0020 里是 private，0021 才挪到 `PanoramaGrid.kt` 共用）。
浏览页：`BrowseSourceViewModel` 拆出 `getColumnCount(orientation)`（0 = 自动），`BrowseSourceContent` / `BrowseSourceScreen` / `MigrateSourceSearchScreen` 多传 `columnCount`，`BrowseSourceComfortableGrid` 全景模式用普通 `LazyVerticalStaggeredGrid`（上游浏览页本来没有快速滚动条，保持一致；Anikku 0021 的浏览页是带快速滚动条的，且列数用 `CountedGridCells` 传——两边实现不同、效果相同）。`BrowseSourceToolbar` 的显示模式菜单多一项，图标与松散网格相同。
字符串 `action_display_comfortable_grid_panorama`：base「Panorama comfortable grid」/ zh-rCN「全景松散网格」/ zh-rTW「全景鬆散格狀」。此补丁由子代理（grok-4.7-high-fast）按 `/workspace/.cursor/rules/orchestration.mdc` 流程完成，主代理复核 diff 并独立重跑 `:app:compileNightlyKotlin spotlessCheck :domain:test`。

补丁 0015「全景紧凑网格」是 0014 的姊妹：`LibraryDisplayMode.CompactGridPanorama`（序列化 `COMPACT_GRID_PANORAMA`，`values` 变 6 个，`LibraryFlagsTest` 断言改 6），`MangaCompactGridItem` 多 `usePanoramaCover` / `coverRatio`，`LibraryCompactGrid` 全景模式走 `LazyLibraryStaggeredGrid`（私有 `LibraryCompactGridItem` 把普通 / 瀑布流两条路径的格子画法合在一起），`BrowseSourceCompactGrid` 多 `usePanoramaCover` / `columnCount`、全景时用 `LazyVerticalStaggeredGrid`；菜单项 `action_display_grid_panorama`：base「Panorama compact grid」/ zh-rCN「全景紧凑网格」/ zh-rTW「全景密集格狀」（zh-rTW 的紧凑网格叫「密集格狀」，跟着上游）。与 anikku-harmony 0022 同源（Anikku 还多改 `RelatedMangasCompactGrid` 和 `BrowseSourceSimpleToolbar`，Mihon 没有这两个界面）。

补丁 0016 只改 `presentation-core/.../VerticalFastScroller.kt` 的 `VerticalStaggeredGridFastScroller`：估算段换成 `StaggeredGridMeasurements`（按索引记高度的 `HashMap` + `heightSum` + 单调递增的 `laneCount`）+ `rememberStaggeredGridEstimate(state)`（`remember(state) { derivedStateOf { … } }`）。要点：
① 满行条目（搜索栏、分区头）按**宽度**识别——比屏上最窄格子宽 1.5 倍以上就不计高度（`LazyStaggeredGridItemInfo` 不暴露 span；子代理最初用 `@Suppress("INVISIBLE_REFERENCE")` 强转 `LazyStaggeredGridMeasuredItem.span`，复核时改掉，内部 API 升级 Compose 就断）；
② `visibleItemsInfo[i].offset.y` 是**相对内容起点**的（Compose `LazyStaggeredGridMeasure.kt` 里 `beforeContentPadding` 只在 `place()` 时加到 `contentOffset`），所以 `scrollOffset` 不加 `beforeContentPadding`、只在 `scrollRange` 里算两头 padding——0014 / Anikku 0020 原来的估算加了，静止时拇指不在最顶；
③ 一次循环同时算 `beforeFirst` / `beforeAll`。`private class StaggeredGridEstimate(` 到 `// Harmony <--` 这一段与 anikku-harmony 0023 **逐字相同**（`diff` 校验过），改一处要同步另一处；两边仍只差拇指淡出那段（见 0014 说明）。

补丁 0017 只改 `data/.../ReleaseServiceImpl.kt`：`latest()` 的 `releases.firstOrNull { 频道 }` 改成 `.filter { 频道 }.maxWithOrNull { a, b -> compareHarmonyVersions(a.version, b.version) }`，companion 里加与 `GetApplicationRelease` 同形的 `HARMONY_VERSION_REGEX` / `parseHarmonyVersion` / `compareHarmonyVersions`（解析不了的排最后）。没有把 domain 层的私有函数公开，是为了让这张补丁只碰一个文件、好重做；上游若把 `latest()` 的签名改了，保留「过滤频道 → 取最大」这两步即可。起因见 §9 2026-10-12：上游 v0.21.1 发布后定时任务自动发了 `v0.21.1-harmony-preview.1`，但镜像 `releases.json`（GitHub API 原样）把 `v0.21.0-harmony-preview.2` 排在它前面，用户的 App 只看得到后者。Anikku 的同病在 `GetApplicationRelease.getLatest()`（0024）；Animeko 0002 本来就是排序取最大。

补丁 0018 修全景网格滑动时资源块排版抽搐、掉帧，以及滚动条的残余抽搐。三条根因，上游若重写网格要一起保住：
① 格子第一次出现时不知道封面横竖，先按默认横版（3:2）排，图片解码完才改成 2:3。瀑布流（`LazyVerticalStaggeredGrid`）一个格子变高会把该列下面全部推下去；快速滑动时每秒几十张图加载完，各触发一次整个瀑布流重测。0014 的比例缓存只在进程内，重启全部重来。
② 横/竖切换时 `MangaCover.Panorama(...)` / `MangaCover.Book(...)` 是两个 Compose 调用点，`AsyncImage` 被销毁重建、图片重新请求、`onSuccess` 再触发一次形状变化。
③ 滚动条残余抽搐是同一件事：可见格子高度在滑动中变，0016 的估算就跳。**0016 的滚动条代码这张补丁没动。**

做法：新文件 `app/src/main/java/eu/kanade/presentation/library/components/PanoramaCoverShapes.kt`，与 anikku-harmony 0025 **逐字节相同**（`cmp` 校验过），改一处要同步另一处。`PanoramaCoverShapes` 用 `SnapshotStateMap` 存已学到的高/宽，持久化到 `filesDir/harmony_panorama_cover_shapes.txt`（每行 `id ratio`，3 位小数；写临时文件再 rename；2 秒防抖；上限 20000 条，超出丢最旧）。`App.onCreate` 里 `init` 异步加载。书架两种全景模式后台 `prefetch`：对未知 id 用 `BitmapFactory` `inJustDecodeBounds` 读封面缓存文件的尺寸，并行度 4，不阻塞列表，挂在 `LibraryViewModel`（Anikku 挂在 `LibraryScreenModel`，这是唯一的挂点差异）。`LocalPanoramaGridSettled` 由瀑布流包装层提供 `{ !state.isScrollInProgress }`，`rememberCoverRatio` 只在网格静止时才把新形状写进布局；横竖已经在同一侧（都 ≤ 0.75 或都 > 0.75）则立即写。`onCoverLoaded` 改为写 `PanoramaCoverShapes.put`。封面改成单一调用点：`val cover = if (wide) MangaCover.Panorama else MangaCover.Book; cover(...)`。浏览页 `BrowseSource*Grid` 同样注入静止判断，但没有文件预取（靠已持久化的形状，加上停下来之后学到的）。不改数据库、不加设置项。

已知局限：从没见过的封面仍会在滑动停下时改一次形状（一次性，之后就在文件里）；浏览页第一次进全景没有预取。拖滚动条中途改形状、浏览页没有预取，由 0019 补上（见下）。掉帧是否消失要用户真机确认——VM 模拟器只有软件加速，测不了帧率。模拟器（本地 `assembleNightly` 的 x86_64 包，AVD harmony34）上用 400 个本地源条目看过：切「全景紧凑网格」后横竖格子形状正确，滑动后文件落盘，`am force-stop` 重启后排版一致。Animeko 没有这套全景网格，不适用。

补丁 0019 补 0018 留下的两处（用户：「现在看 mihon 也会抖，是不是无解了？」）。上游若重写网格要一起保住：
① `LocalPanoramaGridSettled` 原来是 `{ !state.isScrollInProgress }`。拖快速滚动条的拇指是一连串很短的 `scrollToItem`，两次之间 `isScrollInProgress` 为假，学到的形状就在拖的过程中写进布局；两下甩动之间的停顿同样。`rememberPanoramaGridSettled { state.isScrollInProgress }` 改为：一旦在滚就立刻不算静止，连续 300 ms（`SETTLE_DELAY_MILLIS`）没有滚动才算静止。书架瀑布流包装层（`LazyLibraryGrid`）和浏览页两种全景网格都改用它。
② 浏览页每个封面要等格子上屏、`onCoverLoaded` 才学形状。`PrefetchPanoramaCoverShapes(itemCount)` 加在 `BrowseSourceComfortableGrid` / `BrowseSourceCompactGrid`：对分页已经加载、还没上屏的条目，用 Coil 按 128 px（`PREFETCH_SIZE_PX`）、`Precision.INEXACT`、内存缓存关掉去要封面，成功后把高/宽写进 `PanoramaCoverShapes`；下载进磁盘缓存，格子后来读同一份；网格离开时取消这些请求。书架仍走 0018 的文件预取（读已有封面缓存的宽高），这张不重复做。

`PanoramaCoverShapes.kt` 与 anikku-harmony 0027 **逐字节相同**（`cmp` 校验过），改一处要同步另一处。Anikku 的相关作品页也改用这个 300 ms 判断，列表短，没有浏览页这种预取。不改数据库、不加设置项。

已知局限：刚打开的浏览页第一屏，你还没滑、网格处于静止时，仍可能翻一次形状；下载失败的封面保持默认横版。额外网络：已加载、还没看见的那一页封面会比以前早一点下载（滑到时本来就要下）。本轮只跑了 `:app:compileNightlyKotlin :app:spotlessCheck`，没上模拟器；共享文件与 Anikku 在 AVD harmony34 上测过的那份逐字节相同。Animeko 不适用。

补丁 0020 修全景网格往下滑时右侧快速滚动条拇指大约每行回跳一下（用户：「好像还是会抖，比如往下滑动的时候，右侧滑动块可能会有一小段丝滑下滑，然后突然抽动一下向上移动一丝，再移动回来，大概频率是每一行抽动一下，是不是没找到根因呢？」Mihon、Anikku 都是）。0019 修的是格子形状，不是这段。上游若重写 `VerticalStaggeredGridFastScroller` 要一起保住：

根因：瀑布流（`LazyVerticalStaggeredGrid`）各列格子高度不同。旧估算以「屏幕上编号最小的可见格子」为锚、按行公式推位置；这个格子一移出屏幕就换成下一个，而公式对每个格子的偏差不一样，所以大约每行拇指往回跳一下；另外滚动中「总长度」的均值也在变。Python 模拟旧公式：100 行内 141 次往回跳，中位数 3.2 px，最大 9.3 px。

做法：只改 `presentation-core/src/main/java/tachiyomi/presentation/core/components/VerticalFastScroller.kt`。位置改为跨帧累加——记住一个两帧之间都还在屏幕上的锚（可见项中间那个），用它的位移推进；第 0 项可见时用精确值；跳转（拖拇指 / `scrollToItem`）后锚不在了才回退行公式。滚动中（`isScrollInProgress`）冻结总长度，条目数变化时才刷新；停下后拇指用 150 ms 动画平滑移到新位置（`RANGE_SETTLE_MILLIS = 150`）；到底（`!canScrollForward`）时比例为 1。

`private class StaggeredGridEstimate(` 到 `// Harmony <--` 这一段与 anikku-harmony 0028 **逐字节相同**，改一处要同步另一处。开发树 `/tmp/mihon-0211-clean` `dev-0211` 提交 `98ff730`。`:presentation-core:spotlessCheck :app:compileNightlyKotlin` 通过。拇指顺不顺模拟器（只有软件加速）测不了，要用户真机确认。Animeko 没有这套瀑布流快速滚动条，不适用。0021 起 `StaggeredGridEstimate` 整段删除，滚动条改读真实内容高度，见下一条。

补丁 0021 与 anikku-harmony 0030 同源，修两件（用户：「最后一个似乎倾向于高度不是最高的位置开始……左边看起来空出来一块」「折叠到打开时 anikku 从两列变成四列……希望在排布变化的那一刻就优化好」）。不是卓易通平台限制，是 Compose `LazyVerticalStaggeredGrid` 的行为，两边 foundation 版本不同、相关代码逐段相同。上游若重写全景网格，不要再换回 `LazyVerticalStaggeredGrid`，保住下面这套。

根因两条：
① 分列零容差。`LazyStaggeredGridMeasure.kt` 用 `indexOfMinValue`：每一项严格放进底边最小的列，并列取左边。右边只低一丝，下一项也挪过去，左边空出一块。列表中部同样生效，末尾最显眼。
② 列数变化。lane 数一变就 `laneInfo.reset()`，把当前可见项当成新网格的起点，新列填入「最大下标 + 1」的连续项。只有滑动触发的 `misalignedStart` 才从第 0 项重排。停在列表顶部看不出，要先滚到中部再改宽度。没有可绕的公开 API：`StaggeredGridItemSpan` 只有 `FullLine` / `SingleLane`；目标已可见时 `scrollToItem` 只平移偏移，不会从头重排。

做法：自建 `LazyLayout` 瀑布流（`presentation-core/.../components/PanoramaMasonry.kt`、`PanoramaMasonryLayout.kt`）。下一项高为 `H` 时，`limit = 最短列底边 + H × 0.5`，在底边 ≤ limit 的列里取最左一列。`FullLine` 不参与容差，放在所有列底边的最大值处，放完后各列对齐到它下面。列宽照抄 `StaggeredGridCells.Adaptive`，同宽度下列数和原来一致（0 = `Adaptive(168.dp)`）。重算前记下视口顶部那一项的 key（没有 key 用 index）和它顶边的偏移；新矩形算完后在同一次测量里设滚动位置，再夹到合法范围。

格子高度不测量，布局和格子读同一份已提交形状：
- 槽宽先减左右各 4dp。
- 高/宽 ≤ 0.75（含未知，未知默认 9/16）为宽封面，封面高 = 列内宽 × 2/3；> 0.75 为高封面，封面高 = 列内宽 × 3/2。
- 格子高 = 封面高 + 上下各 4dp。松散再加标题 4dp×2 + 2×18sp（`minLines = maxLines = 2`）。
- 垂直间距 4dp。浏览加载行 72dp。Anikku 另有相关作品加载行 56dp，Mihon 没有相关作品页。
- 上游若改了封面阈值或标题行数，同步 `panoramaCoverCellHeightPx`。

与 0020 的关系：0020 的 `StaggeredGridEstimate` 是因为 `LazyVerticalStaggeredGrid` 不给出真实内容高度，只能估算拇指位置。0021 换成自建布局之后，快速滚动条直接读真实内容高度和偏移，估算段删除。Mihon 浏览页本来没有快速滚动条，保持没有。

调用点 5 处：书架紧凑 / 松散的 `LazyLibraryGrid`、浏览紧凑 / 松散。Anikku 是 7 处（另加相关作品紧凑 / 松散）。

共享文件：
- `PanoramaMasonry.kt`、`PanoramaMasonryLayout.kt`、`presentation-core/src/test/.../PanoramaMasonryLayoutTest.kt` 与 Anikku 0030 **逐字节相同**，改一处要同步另一处。
- `VerticalFastScroller.kt` 的 `// Harmony -->` 到 `// Harmony <--` 段相同。整文件不同：Anikku 保留原有不规则滚动条淡出。**行为差异**：Mihon 书架拇指停留从原来的 2 秒变为系统默认约 300 ms；Anikku 没有这一处。浏览页 Mihon 仍无快速滚动条。
- `app/.../library/components/PanoramaCoverShapes.kt` 此前（0018 / 0019 对 0025 / 0027）逐字节相同。0021 起只差阈值常量名：本仓 `RATIO_SWITCH_TO_PANORAMA`，Anikku `RatioSwitchToPanorama` 加一行 import，各 App 原有命名，逻辑相同。重做时不要为了 `cmp` 把常量名改成对方的。
- `presentation-core/build.gradle.kts` 只加了 JUnit（给 `PanoramaMasonryLayoutTest`）。

开发树 `/tmp/mihon-verify212` 分支 `dev-0021` 提交 `08bd109`（底座 v0.21.2 + 0001–0020），流水线提交 `e5c6c734e`。本机 `:presentation-core:spotlessCheck` `:app:spotlessCheck` 通过，`:presentation-core:testDebugUnitTest` 16/16，`:app:compileNightlyKotlin` 通过。干净 v0.21.2 树套 21 张成功（versionCode 3803），12 个改动文件 `cmp` 一致。未上模拟器（Anikku 在 AVD harmony34 上测过同一份布局文件）。

已知局限：没有 key 的书架过滤结果，锚点按 index；标题行高写死 18sp，系统字体更大时标题被裁（格子以算出的高度为准，超出裁切）；`scrollToItem(0, 0)` 不计开头 content padding。验收列数变化必须先滚到中部，再改宽度（360 dp 宽为 2 列，约 733 dp 宽为 4 列）。真折叠屏这轮只用 `wm size` 模拟，而且是在 Anikku 上。Animeko 没有这套全景网格，不适用。

补丁 0022 修更新页「点第一下下载失败，再点就可以」（用户 10-14：「mihon每次更新界面，点一第一下下载会失败，后面再点就可以下了」）。不是卓易通平台限制。根因置信度约七成，海外 VM 未复现：`NewUpdateScreenModel.downloadApk()` 对 GitHub 发布资产（302 → `release-assets.githubusercontent.com`）只用共用客户端（读超时 30 秒、整次 2 分钟）发一次请求。大陆网络第一次连 CDN 常在连上后卡住或被重置，OkHttp 不在同一次调用里重试，异常 → 删 `update.apk` → 按钮「重试」；再点是新的一次调用，通常成功。JVM 复刻 OkHttp 5.5 拦截器链在 VM 上连下两次都成功（991 ms / 215 ms）。调研排除了：ViewModel 被清 / 协程取消（取消不会变「重试」）、启动清理器与下载竞态、302 包进度体、进度回调除零、DoH（默认关）。调研子代理 bc-eab8129c，实现子代理 bc-d54ee94b。

做法：新文件 `app/.../data/updater/AppUpdateApkDownloader.kt`。专用客户端读 60 秒 / 整次 10 分钟，全局 NetworkHelper 不变。最多 4 次，间隔 2/4/8 秒。IOException 与 5xx 重试，416 删文件从 0 重来，其它 4xx 直接失败。Range 续传：206 追加、200 重写。中途不删文件，最终失败才删。再次开始时，能读出 versionCode 的完整旧包删掉重下，半截留着续传。失败在更新说明上方用红字显示原因：下载超时 / 网络中断 / 服务器返回 HTTP N / 存储写入失败。字符串 `harmony_update_download_timeout|network|http|storage`，base + zh-rCN + zh-rTW。主代理另加 `AppUpdateApkCleaner.updateApk`：`externalCacheDir` 为 null 时回落 `cacheDir`（`provider_paths.xml` 有 `cache-path`）。

**重做要点**：0022 依赖 `newCachelessCallWithProgress(request, listener, existingSize)` 与 `ProgressResponseBody` 的 existingSize 语义。上游改这两个时要重做这张补丁，保住「已下字节算进进度、续传从 existingSize 接着写」。单测 `AppUpdateApkDownloaderTest` 3 个（半截断开后续传、416 从头、404 不重试），用 JDK HttpServer，不依赖真网络。

开发树 `/tmp/mihon-verify212` 分支 `dev-0022` 提交 `e1a029d`（底座 v0.21.2 + 0001–0021），流水线提交 `779cccafc`。主代理复跑 `:app:spotlessCheck :app:compileNightlyKotlin :app:testDebugUnitTest --tests '*AppUpdateApkDownloaderTest*'` 退出 0，3/3、skipped 0。干净 v0.21.2 以 N=4 套全部 20 张（0001–0022，0004 / 0009 早已删除） → versionCode 3804，与开发树只差版本号。

同病：Anikku **不适用**。更新下载走上游 `NetworkHelper.downloadFileWithResume`（最多 5 次、Range 续传、416 删文件、指数退避）。读超时仍是 30 秒，但失败会在 worker 内重试，页面保持「正在下载」。Animeko **待确认**。上游 `DefaultFileDownloader.tryDownload` 每个地址只下一次、无续传，失败后自动换 `downloadUrlAlternatives` 的下一个（ABI 包 → universal），用户未反馈。验证方法：大陆网络下点更新，看是否先失败后自动成功。

补丁 0023–0029 与 anikku-harmony 0031–0037 一一对应、同源（用户 2026-10-14：①「我在游览时书架时点进一个资源，退出后会回到书架最顶，没有记忆。其他ui界面也要好好排查下」；②「mihon有2000资源书架，滑动的时候……一旦我高速松开，进入惯性滑动就会感觉一卡一卡的」；③「按住滑动条快速下翻，按住后看到滑动条会变透明，然后识别成我在手指按着资源界面下滑，操作变成了上翻」；④「感觉mihon的自动好像默认有点过宽，我手机上折叠情况下，只有两列……横的是不是可以限制下高度」）。不是卓易通平台限制。用户手机：华为 Pura X Max（折叠 / 展开）、直板机 vivo X100 Pro，要兼顾旋转。屏幕估算见归档仓 `docs/设备屏幕参考.md`。

根因四条：
① `rememberPanoramaMasonryState` 用父组合的 `SideEffect` 把滚动锚点拷进 `rememberSaveable`。滑动不会重组父组合，存下的永远是顶部 0。进详情页（Voyager push）后书架组合被拆掉，返回时按 0 恢复。次因：恢复时按下标而不是按 key，短列表时恢复被一次性消费掉。受影响：书架全景、浏览全景。Anikku 另有相关作品全景。
② `PanoramaCoverShapes` 用 `mutableStateMapOf`，整表都被订阅：任一封面加载完成就整屏重组、整表重测，预取还在 IO 线程写快照。另外，布局缓存命中时每帧仍要对 2000 项调用 `heightOf` 并新建 key 列表；滚动条 `LaunchedEffect(scrollOffset)` 每帧重启。
③ 瀑布流滚动条只在拇指可见（alpha>0）时才挂拖动手势。按住不动、还没超过 touch slop 时不算滚动，拇指照常淡出，手势被摘掉后落到内容上。
④ 自动最小列宽 168 dp：360 dp 宽的屏只有 2 列。

做法，按补丁：
- 0023：自动列改为适合竖封面的宽度；横封面在 ≥3 列时跨两列（`PanoramaSpan.TwoLanesWhenRoomy`）。列宽的具体数字由 0028 分档取代，这张留下跨列。
- 0024：`PanoramaMasonryState.Saver` 按 key 存锚点，列表加载完整后再恢复。
- 0025：布局世代 `PanoramaMasonryContentEpoch`，内容不变时跳过逐项计算。基准（2000 项，120 帧）：每帧 0.323 ms → 0.0082 ms，每帧分配 266,776 B → 56 B。
- 0026：封面形状表改为按版本通知，不再整表订阅。跨 0.75 比例档的变化等所有网格静止 300 ms 后一次提交；写快照放回主线程。
- 0027：`startDragImmediately`，按下即抓；按住期间不淡出、不摘手势（`holdOpaqueWhileThumbGrabbed`），触摸区 32 dp。列表、网格、瀑布流三根滚动条都改了。
- 0028：`PanoramaColumns.Tiered`，按网格自身宽度分档：< 600 dp 最小 112 dp，≥ 600 dp 用 140 dp。网格宽 360 / 420 / 459 dp 为 3 列，664 / 672 dp 为 4 列，800 dp 为 5 列，933 / 939 dp 为 6 列。Pura X Max 折叠竖屏约 459 dp → 3 列，展开横屏约 939 dp → 6 列；vivo X100 Pro 竖屏 360 / 420 dp → 3 列。比较的是网格宽度，不是设备屏宽，分屏也适用。
- 0029：瀑布流滚动条改为单个 `LaunchedEffect` + `snapshotFlow`，不再每帧重启。

**重做要点**（rebase 到新上游时这 7 张）：
- `PanoramaMasonry.kt`、`PanoramaMasonryLayout.kt`、`PanoramaMasonryLayoutTest.kt` 与 Anikku 0031–0037 里对应的三份 **逐字节相同**，改一处要同步另一处。
- `PanoramaColumns.Tiered` 的常量在 `LibraryComfortableGrid.kt`（Anikku 在 `PanoramaGrid.kt`）。不要为了 `cmp` 把常量挪到对方的文件。
- 滚动条的 Harmony 改动用 `// Harmony -->` 到 `// Harmony <--` 包住。上游列表 / 网格滚动条的 `LaunchedEffect(firstVisibleItemScrollOffset)` **不要**改成 `snapshotFlow`：它们在书架以外，改了会落后一帧。
- 封面形状阈值常量名仍是本仓 `RATIO_SWITCH_TO_PANORAMA`（Anikku `RatioSwitchToPanorama`）。0026 改的是通知方式，不是这个名字。
- 共享测试不再依赖 `java.awt` / `com.sun.management`（预览用手写 PNG 编码，分配计数用反射）。不要为了测试再去改 Gradle。

子代理（grok-4.7-high-fast）实现。主代理复跑 `:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin --rerun-tasks` 通过（presentation-core 35 个用例，0 失败，2 个门控跳过；app 28 个，0 失败）。干净树 `/tmp/mihon-verify213`（`prepare-source.sh`，v0.21.2，N=5）套用成功，12 个改动文件与开发树 `cmp` 一致。没有真机 / 模拟器手势测试。流水线提交 `0066de0e4`。

同病：Anikku 0031–0037 同轮已修。Animeko：滚动条按住不适用（Android 端是不可拖动的 `LazyListVerticalScrollIndicator`，没有可拖动的快速滚动条）；惯性卡顿 / 自动列宽不适用（没有全景瀑布流，也不学习封面比例）；返回丢位置待确认（另一套导航，要用户在真机上从追番列表进条目再返回看位置）。

补丁 0030–0032 与 anikku-harmony 0038–0040 一一对应、同源（用户 2026-10-14：①「看情况，因为mihon是竖着的漫画多，我偏向展开竖着拿，anikku就是横着的视频多，我偏向横着拿，你看看有没有比较好的逻辑能覆盖一下这个需求，不要生硬写个硬横着几列竖着几列，或者区分mihon，anikku啥的，调研下有没有比较优雅的方案。」②「anikku的默认，我在折叠状态全景紧凑，就只有一列，右边还是空的，是不是算法有些问题，然后mihon的看起来就很不错，但是mihon我发现有时候滑动完惯性滑动消失了，不知道anikku有没有类似问题。」③「我没动滑块，现在有个稳定复现的方法，我在书架界面滑到最下面后，再上滑那一下就会有惯性消失情况」「不只是到底，只是能稳定复现这个现象，只是中间滑是偶尔会这样」）。不是卓易通平台限制。

根因两条：
① 折叠屏 459 dp 按 `Tiered` 分 3 列。横封面跨两列（`TwoLanesWhenRoomy`），两组位置等高时取最左。横封面占多数时，第 3 列永远没有东西可放。与 0023 的跨列规则同源。Mihon 竖封面多，竖封面会填上第 3 列，所以看不出来。
② 0027 把滚动条热区加宽到 32 dp，比画出来的拇指（12 dp）向内容侧多出约 20 dp 的透明区，且 `startDragImmediately` 按下即抓。惯性后拇指仍可见一段时间；到底时拇指停在右下角，正好是右手往回滑的起点，于是被当成拖滚动条：列表按比例跳，松手没有惯性。中间滑时拇指位置不固定，所以偶尔撞上。用户说「没动滑块」，是因为碰到的是透明的那一截。

做法，按补丁：
- 0030：`PanoramaColumns.Shaped`。每张封面的视觉面积大致恒定，列宽由主导形状推出，面积随网格面积的平方根适度放大。`A0 = 23064 dp²`，`refArea = 459 × 552`，`area = A0 × max(1, √(网格面积 / refArea))`，`ideal = clamp(√(area / 高宽比) + 8, 104, 240)`，列数取列宽最接近 ideal 的那个。
- 0031：每个全景网格按自己的条目统计形状。只用已提交的投票；已知数 ≥ min(总数, max(8, 总数/2)) 才判定；宽比例 ≥ 0.60 切 Wide，≤ 0.40 才切回 Tall。只在 settle 时采样；形状文件载入或 `committedShapeVersion` 变化、条目签名（条数 + 五个位置 id 的哈希）变化时重采样。列数变化不 bump `PanoramaMasonryContentEpoch`。Tall → `Shaped(1.5)`，横封面 ≥3 列跨两列；Wide → `Shaped(2/3)`，不跨列；Unknown → 原 `Tiered(112, 140, 600)`。手动固定列数时列数不变，跨列仍按模式。
- 0032：热区改为 `ThumbThickness + endInset`。按在拇指上仍按下即拖。列表、网格、瀑布流三根都改了。

**重做要点**（rebase 到新上游时这 3 张）：
- `PanoramaMasonry.kt`、`PanoramaMasonryLayout.kt`、`PanoramaMasonryLayoutTest.kt` 与 Anikku 0038–0040 里对应的三份 **逐字节相同**，改一处要同步另一处。
- `PanoramaShapeMode.kt` 在 app 层。不要为了 `cmp` 把它挪进上面三个共享文件。
- `committedShapeVersion` 只在主线程写，measure 不读。
- 测试依赖（Robolectric 4.16.1、Compose ui-test、junit-vintage 6.1.3、`isIncludeAndroidResources`、`debugImplementation(ui-test-manifest)`）不进包：发版的 nightly 对库模块回退到 release 变体。manifest 已核对，无 ui-test 的 ComponentActivity。

子代理（grok-4.7-high-fast）实现。主代理复跑 `:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin --rerun-tasks` 通过（presentation-core 51 个用例，0 失败，2 跳过；app 35 个）。干净树 `/tmp/mihon-verify214`（`prepare-source.sh`，v0.21.2，N=6）套用成功，18 个改动文件与开发树 `cmp` 一致。没有真机手势测试。流水线提交 `e8220fba2`。

同病：Anikku 0038–0040 同轮已修。Animeko：列数按形状不适用（没有全景瀑布流）；滚动条热区不适用（Android 端是不可拖动的 `LazyListVerticalScrollIndicator`）；惯性不适用，同一原因。

补丁 0033 与 anikku-harmony 0041 同源（用户 2026-10-14 10:53 UTC：「我感觉不是加宽的原因，mihon书架有时候不在底部的时候还是会滑动完没有惯性，之前应该没有的，要有办法定位吗？」）。preview.6 收回热区（0032），只解释「到底往回滑」那一下。书架中间偶发的问题另有原因。没有真机数据，不能定论，因此先发诊断版，不改滑动行为。

读代码，全景网格的惯性只可能这几种原因提前结束：
- 新的滚动请求或按下，打断惯性；
- 某一帧没吃满位移（滚动范围临时变小）；
- 外层（分页器 / 下拉刷新）吃掉松手速度；
- 网格被重建；
- 松手速度本身是 0。

最可疑的是最后一种：Compose 的 VelocityTracker 在「最后一次 move 到 up 的间隔 > 40 ms」时把速度算成 0。卓易通如果触摸事件投递卡顿，就会这样。

做法：
- 新文件 `presentation-core/.../PanoramaScrollTrace.kt`，并改 `PanoramaMasonry.kt`。这两个文件与 Anikku 逐字节相同。
- `CrashLogUtil.kt`：「转储崩溃日志」末尾附「--- Panorama scroll trace (last N events) ---」，最多 400 条，与 `HarmonyLogBuffer`（0012）分开存。
- 每次触摸记 `down` / `up`（`up` 带 `moves`、`dy`、`gapLastMove`、`trackerV`（Compose 速度）、`recentV`（最后 100 ms 自算速度）、`consumed`）。
- 每次惯性记 `fling start v= offset= max=`，结束为 `fling done|stopped|cancelled left= dist= frames= ms= maxGap=`，吃不满的帧记 `short frame asked= got=`。
- `scrollToItem` / `requestScrollToItem` / `scrollToOffset` 各写一行。正式版经过混淆，看不到调用栈，所以每个入口自己写标签。
- offset 被改时记 `measure reason=request|restore|anchor|clamp`；epoch 变化、滚动中 max 变化也记。
- 网格 `enter` / `leave`，以及 `userScrollEnabled=false`。
- 只覆盖全景（瀑布流）网格，普通紧凑 / 舒适网格不记录。

不改滚动行为：惯性包装逐帧原样转发；触摸只在 Initial 阶段旁听、不消费；测量里读 `isScrollInProgress` 用 `Snapshot.withoutReadObservation`，不额外触发重测。

**重做要点**（rebase 到新上游时这 1 张）：
- `PanoramaScrollTrace.kt`、`PanoramaMasonry.kt` 与 Anikku 0041 **逐字节相同**，改一处要同步另一处。`PanoramaMasonryLayout.kt` / `PanoramaMasonryLayoutTest.kt` 本张没动。
- 轨迹不要塞进 `HarmonyLogBuffer` 的 600 行应用日志，分开存，附在转储末尾，最多 400 条。
- 每个滚动入口自己写标签。正式版混淆后没有调用栈。
- 判读：`trackerV=0` 而 `recentV` 很大、`gapLastMove≥40ms` → 触摸投递卡顿；`fling cancelled` 前一行是 `scrollTo…` / `down` / `leave` → 被它打断；`short frame` 或 `fling stopped` → 滚动范围问题；`up` 的 `trackerV` 很大但 `fling start v` 小 → 外层吃了速度。

新测试 3 个（Robolectric）：
- `the scroll trace records the release and how the fling ended`：顺序为 up → fling start → fling done，dist 4462、frames 132。
- `the scroll trace names a jump that cancels the fling`：`scrollToOffset 1000` 之后紧跟 `fling cancelled`。
- `a pause before lifting reads as zero release velocity`：在 4 次 move 后停 60 ms 再松手，得 `gapLastMove=60ms trackerV=0 recentV=-2215`，`fling start v=0`，惯性 0。这说明「停顿后速度归零」的假设在机制上成立。

`:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin` 通过（presentation-core 54 个用例，0 失败，2 跳过；app 35 个）。干净树 `/tmp/mihon-verify215`（`prepare-source.sh`，v0.21.2，N=7）套用成功，20 个改动文件与开发树 `cmp` 一致。开发树 `dev-0023` 提交 `7b0bddc`。流水线提交 `15289c4df`。

同病：Anikku 0041 同轮已加诊断。Animeko 没有全景瀑布流，这条日志不适用；若「停顿 >40 ms 速度归零」是卓易通触摸投递问题，属于平台层，Animeko 的 LazyColumn 也可能受影响，等这份诊断日志定性后再看。日志已于 0034 定性，见下。

补丁 0034 与 anikku-harmony 0042 同源。用户 2026-10-14 11:37 UTC 发来 `mihon_crash_logs_318b.txt`（preview.7）：「最后一次滑动卡住，一直往下滑很流畅，最后一次往上滑的时候，卡，没惯性了」。11:39 UTC 发来 `mihon_crash_logs_ab65.txt`：「我连续上滑五次卡」。

日志结论：
- 往下翻（finger up）的 fling 全部正常。
- 一次往回甩之后，连续 5 次往回甩都是 `fling start v=0`。
- 同时 `trackerV` 有 6310–13529，`gapLastMove` 7–12 ms。不是触摸投递卡顿。preview.7 时「>40 ms 速度归零」的猜测被否定。
- 其中几次甩之前已经没有在跑的 fling，是一种持续的状态。
- 出事时 offset 在 76194–129371 之间。

根因：`PanoramaMasonryState` 的 `ScrollableState` 把 `next - current` 当作已消费量。offset 是 Float，超过 65536 px 时精度只有 1/128 px，这个差不等于 delta。每个拖动帧会剩下千分之几像素没消费。书架外层是 Material 3 的 `pullToRefresh`（`PullRefresh.kt`，material3 1.5.0-beta01）。它在 `onPostScroll` 里把这点剩余当成下拉，`distancePulled` 变成非 0。松手时 `onPreFling → onRelease`：只要 `distancePulled != 0` 且速度是往下拉方向（往回甩），就吃掉全部速度，再把 `distancePulled` 清 0。下一次往回拖又会积上，所以连续卡住。往下翻的剩余被 `coerceAtLeast(0)` 截掉，所以只坏一个方向。越往下翻 offset 越大，越容易出事。

已排除：Pager 没有 `onPreFling`；overscroll 只在边缘拉伸时才吃速度；Draggable 的速度每次手势重算。preview.6「到底往回滑没惯性」可能也有这个原因（当时归因于热区，热区确实也会抓），把握不足。

做法：没碰到两端时返回精确的 delta，碰到两端才返回 `next - current`。Compose 自带的 Lazy 列表也是这样做的。0033 的诊断日志保留。两个 App 里只有全景网格是自写的 ScrollableState，其它列表用 Compose 自带的，不受影响。

**重做要点**（rebase 到新上游时这 1 张）：
- `PanoramaMasonry.kt` 与 Anikku 0042 **逐字节相同**，改一处要同步另一处。`PanoramaScrollTrace.kt` 仍与 0033 / 0041 那一份逐字节相同，诊断日志不要删。
- 没被两端截断时必须返回这一帧传入的 delta，不要返回 `next - current`。只有碰到两端才返回 `next - current`。
- 回归测试要包一层 `pullToRefresh`，并把 offset 设到远超过 65536。不包下拉刷新的同一手势是正常的，包了才会把回甩速度吃成 0。

新测试 `return flicks under pull to refresh keep their velocity far down the list`：网格包在 `pullToRefresh` 里，offset 设为 70000，先往下翻 3 次，再往回甩 4 次。修前 fling 起速 `[5120, 5120, 5120, 0, 0, 0, 0]`，修后往回甩为 -5120。先用 Robolectric 探针复现：同样手势不包 pullToRefresh 正常，包了就全 0。

`:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin` 通过（presentation-core 55 个用例，0 失败，2 跳过；app 35 个）。干净树 `/tmp/mihon-verify216`（`prepare-source.sh`，v0.21.2，N=8）套用成功，20 个改动文件与开发树 `cmp` 一致。开发树 `dev-0023` 提交 `be7349e`。流水线提交 `00a9ff810`。

同病：Anikku 0042 同轮已修（旧代码上同一条测试同样失败）。Animeko 不适用：它没有自写的 ScrollableState，列表用的是 Compose 的 Lazy 系列，会精确返回 delta。根因不是平台触摸投递。

补丁 0035 与 anikku-harmony 0043 同源。用户 2026-10-14：「好像mihon的惯性消失问题解决了，但是为啥滑动块又很难按到了」。0032 把热区收回到画出来的拇指（12 dp + 边距），误抓往回甩的问题没了，但很难按中。

做法：热区恢复 32 dp + 边距，分两段。
- 画出来的拇指（加边距）：按下即抓，和以前一样，内容收不到这个指针。
- 朝内容一侧的另外 20 dp：`HoldToGrabNode`（`PointerInputModifierNode`，`sharePointerInputWithSiblings() = true`），与内容共享触摸、不消费。手指按住且不超过 touch slop 达 120 ms（`HoldToGrabMillis = 120L`），且内容不在滚动（`contentScrolling` lambda）时才抓。抓住后在 Initial 阶段消费所有变化，y 方向拖拇指，`tryEmit` `DragInteraction` start / stop。
- 快甩先越过 slop，照常滚内容并带惯性；惯性中按下只停住内容，不算抓。
- 重叠的兄弟节点，命中测试到第一个被命中的就停，除非它共享指针输入；所以旁边那段必须 `sharePointerInputWithSiblings() = true`，否则内容收不到事件。原 KDoc 写反了，已更正。
- 列表、网格、瀑布流三根都用同一个 `HarmonyScrollerThumb`。

**重做要点**：
- 两段热区不要合并回一个按下即抓的 32 dp（那就是 0027 / 0035 时代误抓往回甩的原因），也不要只留 12 dp（0032 时代很难按）。
- 120 ms 远小于 500 ms 长按超时。抓住后一移动就取消条目长按；一动不动按满 500 ms 仍会弹长按菜单，这是已知副作用。
- `VerticalFastScroller.kt` 的 Harmony 段与 Anikku 0043 保持一致。

新测试 3 个：`a press and hold beside the thumb grabs it`、`a hold beside the thumb during a coast does not grab it`、`a tap beside the thumb does not move the list`。0032 的 `a downward flick beside the bottom thumb still coasts` 照常通过。

同病：Anikku 0043 同轮已修。Animeko 不适用：Android 上的 `LazyListVerticalScrollbar` / `ScrollStateVerticalScrollbar` 只是 `…ScrollIndicator` 指示器，不能拖。

补丁 0036 与 anikku-harmony 0044 同源。用户 2026-10-14 想记录书架上下滑和惯性时的帧率 / 耗时（「有时候又很丝滑」），要一个临时调试按钮导出脱敏日志，不依赖 IP 或 token。

做法：设置 → 高级 →「滚动性能记录（调试）」，pref `harmony_scroll_perf_recorder`（Mihon 是属性 `scrollPerfRecorder`），默认关。`MainActivity` 里 `HarmonyFramePerf.bind(this, pref.changes())`。打开且 Activity 在前台时，往首次 attach 时分配、关掉就释放的原始类型环形缓冲里写（约 1 MB）：
- FrameMetrics 每帧各阶段，在独立 HandlerThread 上回调；GPU 和 DEADLINE 只在 API 31+ 有，否则写 -1。6000 帧。
- 主线程 Choreographer 帧间隔 6000 个，FrameMetrics 不工作时也有。每个间隔带全景滚动阶段（idle / drag / fling，`PanoramaScrollTrace` 里的 volatile，在 down / up / fling start / fling end 设置），以及 `PanoramaFrameCounters` 的测量次数、测量总耗时和新组合格子数。热路径只有一对 `nanoTime` 和加法，不分配。
- 每 500 ms：GC 次数增量、进程 CPU 增量、刷新率与模式、温控（API 29+）、省电模式。
- attach 后 3 秒没有帧回调（会 invalidate decor 逼一帧）时，导出写「FrameMetrics 未提供」，摘要只用 Choreographer 间隔。

记录时左下角（safeDrawing 内、底栏之上）有 40 dp 半透明「记录」按钮，别处的触摸穿透。点按会在滑动轨迹写 `mark user`，在后台线程生成缓存目录下的 `<app>_scroll_perf_<yyyyMMdd-HHmmss>.txt`，和「转储崩溃日志」一样打开分享面板。

导出由纯函数 `PerfReport` 只用数字生成，末行 `privacy: no titles, urls, extension list or logcat text`。不含 logcat 原文、标题、URL、扩展列表、文件路径、账号和 `HarmonyLogBuffer`。卓易通图形层噪音只按 `HARMONY_NOISE_MARKERS`（`CrashLogUtil` 的 companion 改为 `internal` 以共用）每秒计数。卡顿判据：已知 DEADLINE 时 TOTAL > DEADLINE，否则 > 1.5 个 vsync。

开着时的开销：每帧一次后台 FrameMetrics 回调、每个 vsync 一次 Choreographer 回调（主线程按刷新率唤醒），以及 500 ms 采样。关着时什么都不跑。

**重做要点**：
- 发版时 `HarmonyFramePerf.kt`、`HarmonyFramePerfTest.kt`、`PanoramaFrameCounters.kt`、`PanoramaScrollTrace.kt`、`PanoramaMasonry.kt` 与 Anikku 0044 **逐字节相同**。0037 起 `HarmonyFramePerf.kt` 多了丢帧计数和格式 2，不再逐字节相同，Anikku 待移植；其余几份见 0038 / 0040。
- 字符串在 `i18n` base + zh-rCN + zh-rTW 的 Harmony 段。
- 导出内容只能是数字和固定标签。往里加字段前先想清楚会不会带出书名 / 网址。
- 分析脚本在归档仓 `tools/scroll-perf-analyze/analyze.py`，导出格式变了要一起改。0037 起格式是 `harmony-scroll-perf` 2。

开发树 HEAD 复跑 `:presentation-core:testDebugUnitTest :app:testDebugUnitTest` 通过（presentation-core 59 个用例，0 失败，2 跳过；app 41 个）；发版前另跑了 spotless 和 `:app:compileNightlyKotlin`。

同病：Anikku 0044 同轮已加（仍是格式 1）。Animeko 不适用：用户没报 Animeko 卡顿，它也没有全景网格；需要时可移植 `HarmonyFramePerf`，去掉全景计数器即可。

补丁 0037–0040。用户 2026-10-14 约 14:00 UTC 报告：书架网格顺，浏览页全景网格越甩越卡。记录 `mihon_scroll_perf_20261014-220359`（华为 HOP-AL10，卓易通里的 Android 16，90 Hz）。

记录结论：
- Compose / Choreographer 动画仍约 90 Hz（最长间隔 ≤21 ms）。
- 一次甩动里系统报上来的帧从 22:03:36–38 的 98–99% 掉到 22:03:47 以后的 53–62%。书架甩动仍是 95–100%。
- 报上来的帧都没超过截止时间（p50 6.8→8.9 ms，2560 帧甩动里 0 次 jank）。
- 变卡的那几下进程 CPU 更低（约 43%，顺的时候约 83%）。坏的甩动里没有 GC。温控状态 0。90→60 Hz 只出现在停手的空隙。
- 瀑布流整表重排（布局 16–20 ms）大多发生在还顺或停着的时候，46.774 秒之后就没有了，不是越甩越卡的原因。
- 另外：浏览预取为每一行解码一张 128 px 硬件位图再扔掉，和正在看的封面抢 Coil 仅有的 3 个解码槽。

两种假设本版还分不清，所以 0037 只加测量和对照开关，不把现象标成已修：
- **甲**：合成器 / `BLASTBufferQueue` 回压，HWUI 直接跳帧。22:03:50 之后 BBQ 日志升到每秒 10–41 条。
- **乙**：FrameMetrics 报告被丢（3 个槽的环；旧记录器没写 `dropCountSinceLastInvocation`），看起来像丢帧。

0037 做法：
- 写入 `dropCountSinceLastInvocation`。FrameMetrics 线程优先级 `THREAD_PRIORITY_DISPLAY`。采样挪到独立线程，名字 `HarmonyFramePerfSampler`。
- 每一段滚动和整份记录：全部帧（不只是卡顿帧）的 draw / sync / command / swap / gpu / layout 的 p50 / p90，加上 reported、drops、ticks、missed vsyncs。missed = max(0, round(Δintended / refreshPeriod) − 1 − dropCount)。最近 30 秒另有一行一秒。
- 采样增加：Java heap、native heap、gc-time、blocking-gc；分线程 CPU（main、RenderThread、hwui、`cpu_pool` = DefaultDispatcher 线程池、OkHttp = `cpu_ok`、perf、other）；采样耗时；Coil 计数（data source、硬件位图、errors、starts），经 `App.kt` 里接上的 Coil `EventListener`。
- `BLASTBufferQueue` 拆成三类：max frames / `Faking releaseBufferCallback` / 其它。
- 长按「记录」弹出菜单，循环「封面淡入（开/关）」「硬件位图（开/关）」「预取（读文件头 / 旧解码 / 关闭）」和「导出」。每次改动往轨迹写 `mark toggle crossfade=.. hardware=.. prefetch=..`。文件头在开始和导出时各记一次开关。
- 开关在 `HarmonyPerfToggles.kt`，只在内存里。进程重启回到 crossfade=on、hardware=on、prefetch=bounds。不要写成 DataStore / SharedPreferences。
- 导出格式 `harmony-scroll-perf` 2。

0038 做法：任一网格还在滚时，第一次跨档提交进 `pendingCross`，停稳（300 ms）后一次 epoch bump 提交。刷新合并成主线程 looper 上的一次 post。滑动中用实时 `isScrollInProgress` 探针，不要用可能滞后一帧的快照。

0039 做法：默认 BOUNDS。Coil 把图拉到磁盘；请求级 `decoderFactory` 只读文件头（`imageSource.file()` + `inJustDecodeBounds`），返回 1×1 的 `ColorImage`（`isSampled`，关掉这份请求的内存缓存），跑在 `Dispatchers.IO`，不占那 3 个解码槽，也不做硬件位图。窗口是第一个可见项再往后 30 项，同时最多 2 个，滑动中暂停，落后超过一个窗口就取消，完成的 id 记住，失败重试一次。DECODE 是旧的整图解码路径，OFF 是不预取。`MangaCover` 遵守封面淡入 / 硬件位图开关，并用 `memoryCacheKeyExtra`；两个开关都是默认值时，封面数据与改前一致。

0040 做法：新的一页带着新的 items lambda。形状 epoch 没变、已经排好的 key 前缀对得上，就只追加，并把页脚那一行重新放好；否则整表重建。

**重做要点**（rebase 到新上游时这 4 张）：
- `HarmonyFramePerf.kt` / `HarmonyPerfToggles.kt` 计划与 anikku-harmony 0044 **逐字节相同**。Anikku 本轮没移植，0044 仍是格式 1。
- 0038 与 anikku-harmony 0025 / 0027 同一份做法，0039 与 0027 同一份做法，0040 改的是此前与 anikku-harmony 0030 逐字节相同的 `PanoramaMasonry.kt`。Anikku 本轮没改，同病待修。
- 三个对照开关只放内存。重启必须回到 crossfade=on、hardware=on、prefetch=bounds。
- 导出仍只能是数字和固定标签。`mark toggle` 行只写这三项的开 / 关。
- 分析脚本在归档仓 `tools/scroll-perf-analyze/`，格式 2 的阶段分位数、`mark toggle`、`toggles_at_start`、`cpu_pool`（旧导出写的是 `cpu_coil`）要一起认。
- 独立 grok 复核修过的 8 处不要丢掉：开关的内存缓存 key 附加项（`memoryCacheKeyExtra`）、快照不在主线程读、追加时核对已排版 key 前缀、预取失败重试一次、用 `imageSource.file()` 读文件头、`isSampled`、滑动中的实时 `isScrollInProgress` 探针、`threadCpuBroken` 的作用域和 `cpu_pool`。

作者 Xun2202。分析与实现由 grok-4.7-high 子代理完成，主代理复核，另有一次独立 grok 复核（上面 8 处）。

`spotlessCheck`、`:app:compileNightlyKotlin`、`:presentation-core:testDebugUnitTest`、`:app:testDebugUnitTest` 通过（presentation-core 65 个用例，0 失败，2 跳过；app 49 个，0 失败）。干净树 `/tmp/mihon-verify217`（`prepare-source.sh`，v0.21.2，N=11）套用后，除 `app/build.gradle.kts` 的版本号 / 更新器行外，改动文件与开发树 `cmp` 一致。开发树 `/tmp/mihon-verify212` 分支 `dev-0024` HEAD `005f27b`（0037=`400fd6c`，0038=`6a7156b`，0039=`14f48c5`，0040=`005f27b`）。流水线提交 `33568c567`。

同病：Anikku 的 0038–0040 等价改动同病待修；0037 的 `HarmonyFramePerf.kt` / `HarmonyPerfToggles.kt` 待移植。Anikku 浏览页另外还有调色板解码、400 ms 延迟转圈、每行急切 `stateIn`、浏览页快速滚动条，是否也在拖慢，待确认。Animeko 不适用：没有全景瀑布流网格，也没有 `HarmonyFramePerf`。0041 起导出格式改为 `harmony-scroll-perf` 3，采样线程改为 `HarmonyPerfSmpl`，见下。

补丁 0041–0045。用户在 preview.11 上反馈（2026-10-14 约 16:52 UTC）：浏览页很卡，「像封面一直没加载」；排版怪，格子先占一大块横的，再缩回去。两份记录 `mihon_scroll_perf_20261015-005028`、`mihon_scroll_perf_20261015-005436`，窗口 664×939 dp，展开竖屏。另：展开横屏浏览一排 7 个，竖着 3 个觉得合适。

四路 grok-4.7-high 子代理并行（数据、代码、业界、列数）的结论：
- drops 全是 0。漏掉的 vsync 是真的，0037 要分的「报帧被丢」排除。浏览甩动中位漏 14% 的 vsync，书架 0%。封面淡入 / 硬件位图 / 预取三个开关看不出明显差别。
- 未知封面用 9/16 的宽占位，横跨两列。大约 59 个格子先是这种横块，每次停下后再过大约 310 ms 才翻成竖的。内容高度：20 项 14098→4092，59 项 31008→16957。视口跳 394–1628 px。0038（跨档等停稳）和 0039（滑动中暂停预取）把这件事加重了，是回退。
- 记录器采样大约每 530 ms 花 25–50 ms，约一颗核的 7%。
- 不跳的瀑布流在放下之前就知道宽高：Pinterest、小红书、B站、微博、Unsplash 的接口返回 width/height；Instagram 裁成固定 3:4；Tachiyomi 一家用固定网格。`StaggeredGridLayoutManager` 在 idle 时重排，是同一类问题。
- 结论：形状在第一次放下之前就定死，已经放下的格子不再挪，才有可能不跳。
- 一排 7 个的原因：自动（列数偏好 0）是 `GridCells.Adaptive(128 dp)`，939 dp 横屏 → 7。书架显示表「每行数目」按方向记，浏览页也认，这是已有的手动绕过。

0041 做法：
- `/proc` 每线程 CPU 每 4 次采样读一次（约 2 秒）。tid→类别缓存；新的或复用的 tid 重读 comm。
- 采样线程改名 `HarmonyPerfSmpl`。`cpu_perf` 只含 FrameMetrics 监听线程，`cpu_smpl` 是采样线程。
- segment / stages / 每秒行加上 measures、measure_ms、composed 的合计与 p90。
- 单次 intended-vsync 间隔超过 1 秒记 `idle_holes`，不算 missed。
- 分析脚本把 `fling stopped` 算进去。导出格式 `harmony-scroll-perf` 3。

0042 做法：
- 未知封面默认竖的 3/2、单列占位。占位档在 settle 时跟书架投票 / 多数，宽比例 ≥ 0.60 切宽、≤ 0.40 才切回。Anikku 横封面多时会收到宽档。
- 第一次提交已是同一档：即使还在滑也不重排。
- 跨档而且变的是视口下面的：只重排尾巴。冻结线按当前滚动偏移算。重排范围碰到视口就把锚点放回去。
- 屏幕上和更上面的：比例记下，这一次访问格子留在原槽，格子里裁切。
- 冷启动读形状文件只 bump 一次，不再把排版冻住。
- 预取不再在滑动中暂停。窗口 +60，同时最多 4 个。
- `rememberCoverRatio` 不在组合时写。

0043 做法：自动最小格宽 < 600 dp 用 112 dp，< 840 dp 用 140 dp，≥ 840 dp 用 176 dp。书架和浏览、书形网格和全景都改。459 dp → 3，664 → 4，939 → 5（以前非全景 7、全景 6）。手动 1–10 不变。`PanoramaColumns.Shaped` 的列数被这一档封顶。

0044 做法：浏览格子和加载行带 `contentType`。格子经 `derivedStateOf` 读 `peek`。分页提示走 `SideEffect` 里的 `get()`，另加从 `lastVisibleItemIndex` 来的远端提示。items provider 缓存。`getIndex` 用映射。

0045 做法：新文件 `HarmonyCoverHeaderProbe.kt`。
- `Range: bytes=0-32767`，用图源自己的 OkHttp 客户端和请求头（含 Referer），`Accept-Encoding: identity`，最多读 32 KB。
- 忽略 Range 的 HTTP 200：取消，不把响应体读完。
- JPEG 按段走，跳过 EXIF 缩略图；必要时再跟一次，最多 128 KB。也认 PNG / GIF / WebP / BMP。
- 同时最多 6 个。第一页最多等 400 ms。后面追加的页立刻返回，后台再探（2 秒，列表失效就取消）。
- 只对全景模式和 `HttpSource`。已知 id 跳过。读不出、以及 AVIF / JXL / HEIF，用占位。
- 不记 URL。EXIF orientation 5–8 不应用。

**重做要点**（rebase 到新上游时这 5 张）：
- `HarmonyFramePerf.kt` 计划与 anikku-harmony 0044 **逐字节共用**。Anikku 还没有 0041，0044 仍是格式 1。不要把采样线程改回 `HarmonyFramePerfSampler`，也不要每 500 ms 都读 `/proc`。
- 0042 盖过 0038 / 0039 里加重回退的两处：跨档不要一律等停稳再整表提交；预取不要在滑动中暂停。未知默认是竖的 3/2 单列，不是 9/16 跨两列。屏幕上的格子这一次访问留在原槽。
- 0043 的三档（112 / 140 / 176，分界 600 / 840）书架和浏览、书形和全景一起改。手动 1–10 不要动。`Shaped` 列数被档封顶。
- 0044 的浏览格子不要在组合时读分页状态。`contentType`、`derivedStateOf` 的 peek、`SideEffect` 里的 `get()` 都要留下。
- 0045 只用图源自己的客户端和请求头。不要记 URL。忽略 Range 的 200 取消且不读完。EXIF orientation 5–8 保持不应用。AVIF / JXL / HEIF 保持走占位。
- 导出仍只能是数字和固定标签。格式 3 的 `idle_holes`、`cpu_smpl`、measures / measure_ms / composed 要和归档仓 `tools/scroll-perf-analyze/` 一起认（含 `fixtures/scroll_perf_v3_sample.txt`）。`fling stopped` 要算进甩动结束。
- 独立 grok 复核的 4 个中、3 个低都已修进这 5 张。具体是哪几处，待确认（复核结论只给了严重度计数）。

作者沿用各补丁提交。实现是 grok 子代理，4 个隔离 worktree；独立 grok 复核 0 高 / 4 中 / 3 低，都已修。

本地 `spotlessCheck`、`:app:compileNightlyKotlin`、`:presentation-core:testDebugUnitTest`、`:app:testDebugUnitTest` 通过（presentation-core 71 个用例，69 通过，2 跳过；app 70 个通过）。干净树 `/tmp/mihon-verify219`（`prepare-source.sh`，v0.21.2，N=12）套用后，除 `app/build.gradle.kts` 外，改动文件与开发树 `cmp` 一致。开发树 `/tmp/mihon-verify212` 分支 `dev-0025` HEAD `f1adecd`（0041=`39f004f`，0042=`b25f1fb`，0043=`6122cf3`，0044=`805c66e`，0045=`f1adecd`）。流水线提交 `fcd0c73bb`。

同病：Anikku 0041–0045 待移植（0041 的 `HarmonyFramePerf.kt` 计划逐字节共用；0042 与 0025 / 0027 / 0030 同病；0043 同一条自动列规则）。用户确认后再一起移植。Animeko 不适用：没有全景瀑布流网格，也没有 `HarmonyFramePerf`。漏掉的 14% vsync 在占位不再跳动之后还在不在，待确认。


### 5.2 加新补丁

在套完现有补丁的源码树上直接改代码并 commit（message 写清楚为什么），`git format-patch -1` 导出，
放进 `patches/`，追加到 `series` 末尾，更新 README 的补丁表。

### 5.3 验证改动但不发版

Actions → Harmony Preview → Run workflow，勾选 `dry_run`。构建完成后在该次运行的 Artifacts 里下载 APK，
可以用 `apksigner verify --print-certs` 或任意 APK 签名查看工具确认证书 SHA-256 与现有 Release 一致。

### 5.4 正式出新版

Run workflow，`upstream_tag` 填官方 tag（留空取最新稳定版），`patch_number` 从 1 开始；同一官方版本改了补丁要重发就填 2、3……
同名 Release 已存在会直接跳过。约 7–10 分钟。发版前确认最新上游 tag（定时 run 会自动跟进新上游）。目标 tag 还不存在、且按「上游版本.N」比已发布最高的旧时，workflow 会 `exit 1`（「installs would be a downgrade」），不会发出降级包。

### 5.5 命令行操作（给 AI 助手；token 只放环境变量，不要写进任何文件或 commit）

```bash
export GH_TOKEN='<用户提供的 token>'
gh workflow run harmony_preview.yml --repo Xun2202/mihon-harmony -f upstream_tag=v0.20.4 -f patch_number=4 -f dry_run=true
gh run list --repo Xun2202/mihon-harmony --workflow harmony_preview.yml --limit 3
gh run watch <run_id> --repo Xun2202/mihon-harmony --exit-status
gh run view <run_id> --repo Xun2202/mihon-harmony --log-failed
gh release list --repo Xun2202/mihon-harmony
```

没有 `gh` 时用 REST API：`POST /repos/Xun2202/mihon-harmony/actions/workflows/harmony_preview.yml/dispatches`
（body `{"ref":"main","inputs":{...}}`），`GET /repos/Xun2202/mihon-harmony/actions/runs`。

## 6. 签名密钥

- Secrets：`SIGNING_KEY`（jks 的 Base64）、`KEY_STORE_PASSWORD`、`ALIAS`（`mihon-harmony`）、`KEY_PASSWORD`。
  RSA 4096，有效期 10000 天，2026-09-25 生成。
- 签名证书 SHA-256：`4bd90284699327e1bf135ac394d5e8f9acc6da7257fa0967727ca2bad507ea8a`
  （从 preview.3 和补丁流水线 dry_run 产物的 APK 签名块里读出，两者一致）。验证新产物时对这个值。
- **权威备份**：私有仓库 `Xun2202/keystores` 的 `mihon-harmony/` 目录，含 `signingkey.jks`、
  `signingkey.jks.b64`（即 `SIGNING_KEY` 的值）、`signing.json`（别名、两个密码、证书指纹）和说明 README。
  GitHub Secrets 只能写入不能读出；任何拿到可读该私有仓库 token 的会话都能用仓库里的
  `scripts/set_secrets.py mihon-harmony` 一键恢复四个 Secrets，用 `scripts/verify.py` 校验钥匙。
  旧的单独仓库 `Xun2202/mihon-harmony-keystore` 已于 2026-10-05 归档；
  维护者电脑的本地克隆下另有一份 git 忽略的 `_private/` 副本，非必需。
- **丢失密钥 = 已安装用户无法覆盖升级**。若真的丢了：重新生成密钥、更新四个 Secrets、提醒用户先在 App 内备份数据再卸载重装。

## 7. 已知问题与排错

| 现象 | 原因 / 处理 |
| --- | --- |
| `prepare-source.sh` 报 `Patch 000X ... does not apply` | 官方新版改动了补丁触及的代码。按 §5.1 rebase。先看 zsyou 仓库的 `.github/patches/harmony.patch` 是否已更新，可作参考 |
| 编译报错在 `AppUpdateChecker.kt` / `ReleaseServiceImpl.kt` / `GetApplicationRelease.kt` | 官方改了这几个文件的接口（补丁 0002 是基于 v0.20.4 的近乎整文件改写）。取官方新版文件重新套用 0002 的意图；0008（镜像）/ 0017（取最大版本）也碰 `ReleaseServiceImpl.kt` |
| 「检查更新」拿到的不是最新 tag | 0017 之前 `latest()` 取列表第一项，GitHub / 镜像的顺序不保证按版本。0017 起按 `(主, 次, 补丁, harmony 号)` 取最大；若再现，先 `curl` 镜像 `releases.json` 看 tag 是否符合 `v<x>.<y>.<z>-harmony(-preview).<n>`（不符合的排最后） |
| 编译报错在 `Downloader.kt` | 补丁 0001 / 0003 / 0006 / 0010 / 0011 / 0013 都改它。参考各补丁 commit message 重做；v0.21.0 的 rebase 记录见 §9 2026-10-12 |
| 点「下载」按钮没反应、队列为空也没提示 | 0011 之前的行为：磁盘上已有同名章节目录（收尾被打断的残留）但下载缓存不知道。0011 起会弹「未加入下载队列：…」，残留目录完整则直接登记为已下载，不完整则删掉重下。若仍无提示，看 crash log 末尾的「App log」小节有没有 `Removing incomplete leftover` / `already on disk` |
| 导出的崩溃日志几乎全是 `BLASTBufferQueue` / `SurfaceDelegator` | 卓易通图形层噪音。0012 起会被过滤并在「--- Logcat (N … filtered) ---」里计数；应用自己的日志看末尾「App log」小节。出现新的刷屏 tag 就往 `CrashLogUtil.HARMONY_NOISE_MARKERS` 加子串 |
| `check_patches`「Apply to latest stable」红、每日定时构建失败在 `prepare-source.sh` | 官方出了新稳定版、补丁套不上。需要整体 rebase（§5.1）；在此之前手动发版要指定旧的 `upstream_tag`（例：2026-10-11 v0.21.0 发布后到 10-12 rebase 完成之间，`upstream_tag=v0.20.4`） |
| 闪退 `SQLException: Error code: 5, message: database is locked` | 数据库写入撞锁且无 busy timeout。v0.20.4 系列靠补丁 0004（preview.4 起），v0.21.0 起上游 `DatabaseBindings.kt` 自带；若再现，看上游是否把 `PRAGMA busy_timeout` 去掉了 |
| 升到 v0.21.0 系列后 Release 构建报 `storeFile` 相关错误 / 未签名 | 0.21 的 `app/build.gradle.kts` 读 `storeFile`（文件路径）而不是 `storeFileBase64`。workflow 的 `Decode signing keystore` 步骤负责解码到 `$RUNNER_TEMP/harmony.keystore`，两个变量都注入 |
| `assembleNightly` 找不到 / 产物目录不对 | 构建类型名随上游版本变：v0.21.0+ 是 `nightly`，更早是 `preview`。workflow 的 `Resolve build type` 按 `create("nightly")` 是否存在自动选，产物路径与文件名都带这个名字 |
| 闪退 `ForegroundServiceDidNotStopInTimeException ... type dataSync` | Android 15+ 平台规则：dataSync 前台服务后台累计 6 小时 / 24 小时后系统要求停止。实际触发路径是卓易通把后台进程冻结，下载不走、前台服务却一直挂着，把额度白白耗光。补丁 0005（preview.5 起）用静音音轨 + 唤醒锁阻止冻结，并把下载服务改为 `mediaPlayback` 类型（无时限）；书架更新仍是 dataSync，但不再空转。若用户关闭了「后台保持运行（鸿蒙）」开关则回到官方行为：隔几小时切回前台重置额度 |
| 后台下载停住 / 切回 App 才继续 | 卓易通冻结后台进程。确认 设置 → 下载 →「后台保持运行（鸿蒙）」开着（preview.5 起默认开）；logcat 里应有 `Background keep-alive started`。若鸿蒙后续版本连静音音频也拦，只能等上游 / 系统变化 |
| 下载时其他 App 的音乐被暂停 / 变小声 | 不应发生：keep-alive 不请求音频焦点。若出现，检查 `BackgroundKeepAlive.kt` 是否被改成了 `requestAudioFocus` |
| 更新装完后 `Android/data/app.mihon.debug/cache/update.apk` 还在 | preview.6 及之前的行为，0007 起下次启动会删；若 preview.7+ 仍在，说明文件里的 versionCode 比当前高（下载了新版但还没装），属预期 |
| 下载通知速度一直 0 B/s、或进度不动 | 速度靠 `downloadImage()` 里的 `countingInto(DownloadSpeedMeter)` 计数，进度靠 `Download.progress`（页平均）。上游若改了图片下载路径（不再经 `saveTo`）或页进度模型，0006 要跟着挪；通知本身每秒刷新一次，700 ms 内同章节的重复更新会被丢弃，这是预期行为 |
| 图库里仍能看到漫画图片 | 确认 App「保存为 CBZ」已开启；目录模式无法规避，去图库隐藏该相册。历史遗留的 `_tmp` 目录可手动删除 |
| Release 步骤失败 `refusing to allow a GitHub App to create or update workflow` | 有人把推 tag 的逻辑加回来了。保持 `gh release create --target $GITHUB_SHA`，不要 `git push` tag |
| 定时任务不跑 | 仓库 60 天无提交被 GitHub 暂停，到 Actions 页面手动 Enable |
| App 内检查不到更新 | 确认 Release 不是 draft、tag 含 `-harmony-preview.`、资产文件名含 `-arm64-v8a`，且 `repo` 分支的 `releases.json` 里已有它（0008 起 App 先读镜像，CDN 缓存最多约 5 分钟）；0.20.4 的 `GetApplicationRelease` 没有节流，每次启动都会查一次，也可在「关于」页手动检查 |
| 「检查更新」toast「HTTP error 403」 | 匿名 `api.github.com` 的配额（每个出口 IP 每小时 60 次）被用完，NAT / 代理后面所有人共用；仓库本身公开可访问。等一小时或换网络；preview.8 起先读 `repo` 分支的镜像，一般不会再撞上。仍 403 说明镜像也读不到（被墙 / 超时 10 秒），看 logcat 里的 `Release mirror unavailable` |
| `repo` 分支的 `releases.json` 没更新 / 不存在 | 发版 workflow 的最后一步失败，或 Release 是手动改的而 `release_index.yml` 没跑。到 Actions 手动运行「Release index」；本地也可 `GH_TOKEN=... scripts/write-release-index.sh Xun2202/mihon-harmony` |
| 卓易通里书架不自动更新 | 设置 → 书架 → 智能更新，取消全部限制选项 |
| 通知栏不显示下载进度 | 卓易通通知兼容问题，无解，不影响功能 |
| 本机 `./gradlew` 一直没有输出、`app/build` 不生成，jstack 里 worker 线程全在 `TaskPathProjectEvaluator.scheduleProjectsJustInTime` 等队列 | v0.21.0 起 `gradle.properties` 开了 `org.gradle.isolated-projects=true`，本机加 `--max-workers=2` 时并行配置阶段会空等（10-12 两次复现）。`./gradlew --stop` 后去掉 `--max-workers` 重跑即可；也不要再传 `-Dorg.gradle.jvmargs` 之类覆盖参数 |
| 全景网格滑动时格子高度乱跳、感觉掉帧，滚动条还在抽一下 | preview.2 及之前：比例只在进程内，格子先按 3:2 排、解码完改 2:3，瀑布流整列重测；横竖切换还重建 `AsyncImage`。0018（v0.21.1-harmony-preview.3）起形状写在 `filesDir/harmony_panorama_cover_shapes.txt`，滑动中不把新形状写进布局（同侧立即写），封面单一调用点。0016 的滚动条代码没动，残余抽搐随格子高度稳定而消失。从没见过的封面仍会在停下时跳一次。拖滚动条的间隙和浏览页未上屏封面由 0019 补（下一行）。掉帧要真机确认（模拟器软件加速测不了帧率） |
| 全景网格拖右侧滚动条、或连续甩两下时格子还会跳；浏览页新滑出来的格子第一次形状不对 | preview.3（0018）把「停下」定义成 `isScrollInProgress` 为假。拖拇指是一串 `scrollToItem`，中间为假就把新形状写进布局；浏览页要等上屏才学形状。0019（v0.21.1-harmony-preview.4）起连续 300 ms 不滚动才算停下，浏览页对已加载未上屏的封面按 128 px 提前学形状（`PanoramaCoverShapes.kt` 与 Anikku 0027 逐字节相同）。刚打开的第一屏在静止时仍可能翻一次；下载失败保持默认横版。往下滑时拇指大约每行回跳由 0020 补（下一行） |
| 全景网格往下滑时右侧滑动块大约每一行往回抽一下，再移回来 | preview.4（0019）修的是格子形状，滚动条估算没动。瀑布流各列高度不同，旧公式以「编号最小的可见格子」为锚，这个格子一换，公式偏差就变，大约每行回跳（模拟 100 行 141 次，中位数 3.2 px，最大 9.3 px）；滚动中总长度均值也在变。0020 起位置跨帧累加（可见项中间那个锚），第 0 项可见用精确值，跳转后锚不在才回退行公式；滚动中冻结总长度，停下后 150 ms 平滑；到底比例为 1。可装的是 `v0.21.2-harmony-preview.2`。`v0.21.1-harmony-preview.5` 含同一补丁，被 0.21.2 系取代、不要装。`StaggeredGridEstimate` 段与 Anikku 0028 逐字节相同。0021 起这套估算已删除，滚动条改用真实内容高度（下一行） |
| 全景网格末尾左边空一块；折叠屏展开后最后几项和前面空一格，滑一下才重排 | preview.2 及之前用 Compose `LazyVerticalStaggeredGrid`：零容差放进最短列；列数一变把可见项当新起点，只有再滑才从头排。0021（`v0.21.2-harmony-preview.3`）起自建 `PanoramaMasonryLayout`：放进底边 ≤ 最短列 + 本项高×0.5 的最左列；列数 / 宽度变化同一次测量里重算，用视口顶部项 key 钉住（没有 key 按 index）。快速滚动条用真实内容高度。本轮未上模拟器。与 Anikku 0030 同源。验收要先滚到中部再改宽度 |
| 全景网格格子里的标题被裁掉 | 松散模式标题行高按 2×18sp 写死，另加上下各 4dp。系统字体调大时格子仍按这个高度排，多出来的字被裁。改行高就改 `panoramaCoverCellHeightPx` 里的 18sp，与 Anikku 一起改 |
| 上游改了封面横竖阈值或标题行数，全景格子高矮不对 | 高度不测量、按公式算（`panoramaCoverCellHeightPx`）：槽宽先减左右各 4dp；宽封面 3/2、高封面 2/3；格子高 = 封面高 + 上下各 4dp；松散再加标题 4dp×2 + 2×18sp。阈值常量名本仓是 `RATIO_SWITCH_TO_PANORAMA`，Anikku 是 `RatioSwitchToPanorama`，逻辑相同，不要改成对方的名字 |
| 全景网格右侧拇指松开后很快消失 | 0021 起书架拇指停留从原来的 2 秒改为系统默认约 300 ms。浏览页本来就没有这根滚动条。Anikku 仍是原来的不规则滚动条淡出，没有这一处 |
| 更新页点「下载」失败，按钮变成「重试」 | preview.3 及之前：共用客户端对 GitHub 资产只发一次（读 30 秒、整次 2 分钟），大陆第一次连 CDN 常在连上后卡住或被重置，OkHttp 不在同一次调用里重试，异常就删 `update.apk`。0022（`v0.21.2-harmony-preview.4`）起专用客户端重试最多 4 次并 Range 续传；最终失败在更新说明上方用红字写原因（下载超时 / 网络中断 / 服务器返回 HTTP N / 存储写入失败）。从旧版升到 preview.4 的这一次仍是旧代码在下载，第一下可能还会失败，再点即可；从 preview.4 往后才自动重试。仍失败就看红字。要日志：设置 → 高级打开详细日志，失败后不要划掉进程，设置 → 高级 → 导出崩溃日志，搜 `NewUpdateScreenModel` |
| 全景网格点进条目再返回，回到最顶 | preview.4 及之前：`rememberPanoramaMasonryState` 用父组合 `SideEffect` 把锚点拷进 `rememberSaveable`，滑动不重组父组合，存下的永远是 0；进详情（Voyager push）后组合被拆掉，返回按 0 恢复。次因是按下标恢复，短列表时被一次性消费掉。0024（`v0.21.2-harmony-preview.5`）起 `PanoramaMasonryState.Saver` 按 key 存，列表加载完整后再恢复。书架全景、浏览全景都改了。没有真机手势测试 |
| 2000 项书架高速松开后惯性滑动一卡一卡 | 封面形状表 `mutableStateMapOf` 整表订阅，任一封面加载完就整屏重组、整表重测；布局缓存命中时每帧仍对全部条目 `heightOf` 并新建 key 列表；瀑布流滚动条 `LaunchedEffect(scrollOffset)` 每帧重启。0025 加 `PanoramaMasonryContentEpoch`，内容不变就跳过逐项计算（2000 项、120 帧：每帧 0.323 ms → 0.0082 ms，分配 266,776 B → 56 B）。0026 改为按版本通知，跨 0.75 比例档等所有网格静止 300 ms 后一次提交，写快照放回主线程。0029 把瀑布流滚动条改成单个 `LaunchedEffect` + `snapshotFlow`。可装的是 `v0.21.2-harmony-preview.5`。上游列表 / 网格滚动条的 `LaunchedEffect(firstVisibleItemScrollOffset)` 故意没改：改成 `snapshotFlow` 会落后一帧 |
| 按住滚动条快速下翻时拇指变透明，松手方向变成上翻 | 滚动条只在拇指 alpha>0 时挂拖动手势。按住不动、还没超过 touch slop 时不算滚动，拇指淡出，手势落到内容上。0027（preview.5）起 `startDragImmediately`，按住期间 `holdOpaqueWhileThumbGrabbed`、不摘手势，触摸区 32 dp。列表、网格、瀑布流三根都改了 |
| 全景「自动」在折叠屏只有两列，竖封面过大、横封面过小 | preview.4 及之前自动最小列宽 168 dp，360 dp 宽只有 2 列。0023 起横封面在 ≥3 列时跨两列（`PanoramaSpan.TwoLanesWhenRoomy`）。0028 起 `PanoramaColumns.Tiered`：网格宽 < 600 dp 最小 112 dp，≥ 600 dp 用 140 dp（常量在 `LibraryComfortableGrid.kt`）。360 / 420 / 459 dp → 3 列，664 / 672 dp → 4 列，800 dp → 5 列，933 / 939 dp → 6 列。比较的是网格自身宽度，分屏同样适用。Pura X Max 折叠竖屏约 459 dp → 3 列，展开横屏约 939 dp → 6 列。横封面多时右列空、以及按主导形状定列，见下两行 |
| 横封面多时右列空 | 折叠 459 dp 按 `Tiered` 分 3 列，横封面 `TwoLanesWhenRoomy` 跨两列，等高时取最左，横封面占多数时第 3 列永远空。Mihon 竖封面多所以平时看不出来。0030 / 0031（`v0.21.2-harmony-preview.6`）改为 `Shaped` + 形状模式：折叠竖 + 横书架为 2 列宽封面。形状未学够时先按 Tiered，判定后最多跳一次，锚点保住位置。40–60% 横的混合书架仍按 Tall 处理（跨列），偶尔会有空位。横主导书架里少数竖封面会很高（展开横约 382 dp） |
| 到底往回滑没惯性 | 0027 的热区 32 dp，比画出的拇指（12 dp）向内容侧多约 20 dp 透明区，且按下即抓。到底时拇指停在右下角，右手往回滑的起点被当成拖滚动条，列表按比例跳、松手没有惯性。中间滑偶尔撞上。用户说没动滑块，碰到的是透明的那一截。0032 起热区改为 `ThumbThickness + endInset`。测试：2000 项、40 ms 上滑，修前距右缘 20 dp 起滑 0 px（4 帧），修后 4462 px / 134 帧；滚到底再在拇指高度距右缘 20 dp 向下甩，修前 0 px，修后 247.72 px（中央基线的 100%）。一次 epoch 变化、一次换列表、一次高度变化、`pendingRestore`、外层 HorizontalPager / 下拉刷新都不会让惯性完全停下（各保留 96% 左右或照常衰减）。热区变窄后能否稳稳按住拖，要真机确认。preview.6「到底往回滑没惯性」可能也有下一行的浮点剩余（热区确实也会抓），把握不足。若收回热区之后、不在底部时仍没惯性，见下两行 |
| 书架中间滑完没有惯性 | preview.7 的日志否定了「触摸送慢了、速度被算成 0」。往下翻（finger up）的 fling 全部正常；一次往回甩之后连续 5 次往回甩都是 `fling start v=0`，同时 `trackerV` 有 6310–13529、`gapLastMove` 7–12 ms，不是触摸投递卡顿。其中几次甩之前已经没有在跑的 fling，是持续状态。出事时 offset 在 76194–129371。0033 的轨迹还在「转储崩溃日志」末尾，最多 400 条，只记全景网格。根因与修法见下一行。0034（`v0.21.2-harmony-preview.8`）起没碰到两端时返回精确 delta。若仍复现，立刻转储，最近 400 条会覆盖 |
| 自写 ScrollableState 必须精确返回 delta，否则 pullToRefresh 会吃回甩速度 | `PanoramaMasonryState` 把 `next - current` 当已消费量。offset 是 Float，超过 65536 px 精度只有 1/128 px，差不等于 delta，每帧剩下千分之几像素。外层 Material 3 `pullToRefresh`（`PullRefresh.kt`，material3 1.5.0-beta01）在 `onPostScroll` 里把剩余当下拉，`distancePulled` 非 0；`onPreFling → onRelease` 在 `distancePulled != 0` 且速度往下拉方向时吃掉全部速度，再清 0，下一次往回拖又积上。往下翻的剩余被 `coerceAtLeast(0)` 截掉，所以只坏往回。0034 没碰到两端时返回精确 delta，碰到两端才返回 `next - current`（Compose 自带的 Lazy 列表同样）。新测试 `return flicks under pull to refresh keep their velocity far down the list`：offset 70000，先往下翻 3 次再往回甩 4 次，修前起速 `[5120, 5120, 5120, 0, 0, 0, 0]`，修后往回甩 -5120。两个 App 里只有全景网格是自写的 ScrollableState。以后新写的滚动容器同样要遵守 |
| 发版等待脚本把一次 API 报错当成 dry_run 已完成 | preview.7 的正式 run 38553912820 在 dry_run 38553801784 结束前就触发了。正式 run 在同一并发组里排队，等 dry_run 成功后才执行，结果无影响。等待循环要把取不到 `conclusion` 当作「未完成」。preview.8 的正式 run 38559877474 是在 dry_run 38558925925 成功之后才触发的，等待脚本已修好 |
| 滚动条又很难按到（preview.8 及之前） | 0032 把热区收回为画出来的拇指宽（12 dp + 边距），不再误抓往回甩，但手指很难按中。0035（`preview.9`）起热区恢复 32 dp + 边距，分两段：按在画出来的拇指上立即抓；拇指旁边那 20 dp 与内容共享触摸（`sharePointerInputWithSiblings() = true`，否则重叠的兄弟节点命中测试到第一个就停，内容收不到事件），只有手指按住、不超过 touch slop 达 120 ms，且内容没在滚动时才抓。快甩会更早越过 slop，照常滚内容带惯性；惯性中按下只是停住内容，不会抓。已知副作用：在拇指旁边一动不动按 500 ms 仍可能触发条目长按菜单。与 Anikku 0043 同源 |
| 觉得上下滑 / 惯性时卡，有时又很顺 | 0036（`preview.10`）起：设置 → 高级 →「滚动性能记录（调试）」，默认关。打开后左下角出现半透明「记录」按钮，感觉卡的时候立刻点，分享出来的 `<app>_scroll_perf_<时间>.txt` 发来。文件只有数字：FrameMetrics 各阶段耗时、Choreographer 帧间隔、每帧全景测量次数 / 耗时 / 新组合格子数、每 500 ms 的 GC / CPU / 刷新率 / 温控 / 省电、每秒卓易通图形层噪音行数（只计数）和全景滑动轨迹；不含标题、URL、扩展列表、logcat 原文。分析：归档仓 `tools/scroll-perf-analyze/analyze.py <文件>`。卡顿判据：有 DEADLINE 时 TOTAL > DEADLINE，否则 > 1.5 个 vsync。FrameMetrics 3 秒内没有回调时文件里写「FrameMetrics 未提供」，只看 Choreographer 间隔。开着时每帧一次回调、每个 vsync 唤醒主线程，用完关掉。与 Anikku 0044 同源。0037（`preview.11`）起还会写下被丢掉的报告数、各阶段 p50/p90、封面加载，长按「记录」可以改封面淡入 / 硬件位图 / 预取再各甩一段；当时导出格式 `harmony-scroll-perf` 2，三个对照项只在这次打开 App 期间有效，重启回到淡入开、硬件位图开、预取只读文件头。0041（`preview.12`）起格式改为 `harmony-scroll-perf` 3：每 4 次采样（约 2 秒）才读一次每线程 CPU，采样线程 `HarmonyPerfSmpl`，`cpu_perf` / `cpu_smpl` 分开，segment 行带 measures / measure_ms / composed，间隔超过 1 秒记 `idle_holes` 不算 missed。preview.11 的采样大约每 530 ms 花 25–50 ms（约一颗核的 7%）。浏览页的下一份记录见「浏览页格子先宽后缩」那一行，不用再切三个开关 |
| 浏览页全景网格越甩越卡，书架还顺；格子先占一大块横的再缩 | 2026-10-14 约 14:00 UTC 的 `mihon_scroll_perf_20261014-220359`（华为 HOP-AL10，卓易通 Android 16，90 Hz）里，动画仍约 90 Hz，浏览甩动的已报告帧从 98–99% 掉到 53–62%，书架仍 95–100%；已报告帧都没超时（2560 帧甩动 0 次 jank）；整表重排在 46.774 秒后就没有了。preview.11（0037–0040）加上丢帧计数和三个开关。约 16:52 UTC 的 `mihon_scroll_perf_20261015-005028`、`mihon_scroll_perf_20261015-005436`（窗口 664×939 dp，展开竖屏）：drops 全是 0，报帧被丢排除；浏览甩动中位漏 14% 的 vsync，书架 0%；三个开关看不出差别。未知封面用 9/16 宽占位、跨两列；约 59 个格子先是横块，每次停下后再过约 310 ms 翻成竖的（内容高度 20 项 14098→4092、59 项 31008→16957，视口跳 394–1628 px）。0038 / 0039 把这件事加重了。0042 / 0045（`preview.12`）起未知封面默认竖的 3/2 单列，同一档不重排，屏幕上的格子这次留在原槽，显示前读封面尺寸。漏掉的 14% 在这之后还在不在，待确认。请装 preview.12，按归档仓 README §3 第 44 项看；可选再录一份（书架 10 秒，再进一个没看过的源甩 20 秒），不用切开关。 |
| 展开横屏浏览一排太多（7 个） | 自动（每行数目 0）是 `GridCells.Adaptive(128 dp)`，939 dp 横屏 → 7 列；全景此前约 6 列。竖着 3 个用户觉得合适。已有绕过：书架显示表「每行数目」按方向各记一个数，浏览页也认。0043（`preview.12`）起自动最小格宽 <600 dp 为 112、<840 为 140、≥840 为 176。书架和浏览、书形网格和全景都改。459 dp → 3，664 → 4，939 → 5。手动 1–10 不变。`Shaped` 列数被这一档封顶。展开横屏应看到 5 列。 |
| `repo` 分支 `releases.json` 第一条不是最新版 | GitHub「列出 Releases」接口不按创建时间排序（2026-10-14 mihon-harmony 的 preview.10 排在 preview.9 等 6 个旧版之后）。三个 App 的更新器都按版本号取最大，不受影响；但只取第一页 30 条时，新版可能被挤出去。`write-release-index.sh` 起翻完所有页、按 `created_at` 倒序取 30 条（三个流水线同一改动）。raw CDN 约 5 分钟缓存，要看即时内容用 `gh api "repos/<repo>/contents/releases.json?ref=repo"` |
| 手机提示版本过老 / 降级不给装 | 更新器按版本号取最大。官方 2026-10-13 04:27 UTC 出了 v0.21.2，定时 run 38392710194 自动发了 `v0.21.2-harmony-preview.1`（versionCode 3801）；随后在 0.21.1 上发的 `v0.21.1-harmony-preview.5`（3705）号更小，手机拒装。preview.5 保留未删，更新器不会把它推给已在 0.21.2 的用户。补救是在最新上游上重发：`v0.21.2-harmony-preview.2`（3802，正式 run 38427442080）。workflow「Resolve release version」（提交 `fd1835633`）：非 dry_run 且目标 tag 还不存在时，按「上游版本.N」`sort -V`，比已发布最高的旧就 `exit 1` 报「installs would be a downgrade」。已存在的 tag 仍 skip，定时 run 不会因此变红。发版前先看 Releases 上最新的上游底座。本地用真实 tag 列表测过：0.21.1 的 preview.6 拒绝，0.21.2 的 preview.3、0.21.3 的 preview.1、0.21.10 的 preview.1 放行。CI 上没实际触发过拒绝路径 |

## 8. 不要做的事

- 不要把 token、密钥或密码提交进仓库（这是公开仓库）。
- 不要改 Release tag 格式和资产命名规则（更新器依赖）。
- 不要再往仓库里放 Mihon 源码快照；需要对照源码时在本地或 `$RUNNER_TEMP` 里 clone 官方仓库。
- 不要上传名字里含 `-arm64-v8a` / `-universal` 的非 APK 资产。

## 9. 时间线

- 2026-09-26 fork `zsyou/mihon-harmony`；新增 `harmony_preview.yml`；生成签名密钥并写入 Secrets；发布 preview.1。
- 同日 加入更新器补丁并开启 `-Penable-updater`；发布 preview.2。加入每日定时；禁用作者的其它 workflow。
- 同日 新增 `downloader.py`（CBZ 临时目录移入私有缓存、残留容错）；发布 preview.3。
- 2026-10-03 改为补丁流水线：删除源码快照，旧机制折算为 `patches/0001–0003`，新增 `scripts/prepare-source.sh`、
  `check_patches.yml`、`dry_run` 输入。
- 2026-10-05 签名密钥、密码与恢复说明上传到私有仓库 `Xun2202/mihon-harmony-keystore`；同日所有签名密钥
  统一迁入私有仓库 `Xun2202/keystores`（本项目在 `mihon-harmony/` 目录），旧仓库归档；用迁入后的备份重写
  四个 Secrets 并以 `dry_run` 构建复核签名证书一致（§6）。
- 2026-10-06 用户上报两次闪退（dataSync 前台服务超时、`database is locked`）。前者是平台限制（§7），后者新增补丁 0004
  回移上游 `38e93086c8`（busy_timeout 3000 + 显式 WAL + 1 写 4 读连接池）；`dry_run` 验证后发布 preview.4。
- 同日 用户反馈切后台后下载不走，并推测前者闪退是后台卡住把 6 小时额度耗光所致（成立）。新增补丁 0005 后台保活
  （静音 `AudioTrack` + 唤醒锁，下载服务改 `mediaPlayback`，设置开关）；`dry_run` 验证（versionCode 2905、manifest
  `foregroundServiceType=0x3`）后发布 preview.5。
- 同日 用户要求三个鸿蒙版应用的下载通知统一成 Animeko 的样式（速度 + 进度）。新增补丁 0006（`DownloadSpeedMeter`、
  通知重写、1 Hz 刷新）；`dry_run` 验证（versionCode 2906、新字符串与类都在产物里）后发布 preview.6。
- 同日（晚） 用户问三个 App 更新完的 APK 会不会一直占存储。Mihon / Anikku 此前都不删（Animeko 的 Android 端也不删）。
  新增补丁 0007（启动时删已安装的 `update.apk`，与 anikku-harmony 0011 同一段代码）；`dry_run` 验证后发布 preview.7。
- 同日（深夜） Anikku 用户撞上「检查更新」HTTP 403（匿名 GitHub 接口每 IP 每小时 60 次配额）。三个 App 的更新检查都直接打 `api.github.com`，
  按跨 App 规则统一改：流水线新增 `write-release-index.sh` / `release_index.yml` 把 Releases 接口返回镜像到 `repo` 分支，
  新增补丁 0008 让 App 先读镜像再退回接口；`dry_run` 验证后发布 preview.8（versionCode 2908）。
- 2026-10-11 Anikku 用户反馈「下载 100% 后变 !」，根因是卓易通 SAF 不支持 `renameDocument`、0001 的回退整份复制且失败无提示（anikku-harmony 0016）。
  Mihon 是同一份 `renameToOrCopy`（章节目录改名 = 每页再抄一遍），用户要求「mihon 一块改」。本机冷缓存构建先撞上 JitPack 的 FlexibleAdapter 404
  （CI 一直靠旧缓存）→ 补丁 0009 回迁上游的 Maven Central 坐标，`prepare-source.sh` 加「能反向套用即跳过」；补丁 0010 移植 0016。
  本机 `:core:common:testDebugUnitTest`（8 个用例）与 `:app:assemblePreview` 通过，10 张补丁在干净 v0.20.4 上套用一致；`check_patches` run 38140034698 绿 →
  正式发版 run 38140180515 → `v0.20.4-harmony-preview.9`（versionCode 2909，versionName `0.20.4-harmony.9-7883`，签名 `4bd90284…ea8a`，`repo` 分支 `bb04007`）。
  没跑 `dry_run`（本地整包编译代替）；模拟器（TCG，无 KVM）上 Mihon 走到了 SAF 文件夹 + 下载一章，但界面级的「出错：…」截图没来得及截，用户要求改为真机验证。
- 2026-10-12 用户上报「有个资源点了下载后按钮卡了一下但没开始下载」并附 crash log。日志 701 行只覆盖 5 分钟、690 行是卓易通图形层噪音，Mihon 自己只有 3 行 `PagerPageHolder: JobCancellationException`（正常），
  没有任何 `Downloader` 记录。从代码定位到 `queueChapters()` 对磁盘已有目录的静默过滤（见 §5.1 补丁 0011），用户要求「错误噪音」和下载问题一起修。
  新增补丁 0011 / 0012，本机 `:app:compilePreviewKotlin` 通过，12 张补丁在干净 v0.20.4 上套用后与开发树一致；同一时刻 Mihon 官方发布了 **v0.21.0**（2026-10-11 20:51 UTC，273 个提交），
  `check_patches` 对「最新稳定版」的试套从这次 push 起变红（0001 起就套不上，只有 0012 能套），每日定时构建也会因此失败直到补丁 rebase 到 v0.21.0；preview.10 仍手动指定 `upstream_tag=v0.20.4`。
  `dry_run` run 38205970728 绿 → 正式 run 38206617187 → `v0.20.4-harmony-preview.10`（05:12 UTC，versionCode 2910，versionName `0.20.4-harmony.10-7885`，签名 `4bd90284…ea8a`，
  arm64 26,428,273 B，SHA-256 `8aaf3187…83fe`，`repo` 分支 `02e4861`）。发出后自查：点「!」重试失败章节会被 0011 算成「已在队列中」而弹提示 → 补丁 0013 →
  `dry_run` run 38207395009 绿 → 正式 run 38208441462 → `v0.20.4-harmony-preview.11`（05:38 UTC，versionCode 2911，versionName `0.20.4-harmony.11-7886`，
  arm64 26,428,273 B，SHA-256 `5f73702a…52a5`，签名一致，DEX 含 `HarmonyLogBuffer` / `already on disk as` / `Removing incomplete leftover`，`resources.arsc` 含三种语言的 `harmony_download_skipped*`，`repo` 分支 `0869f50`）。
- 同日（上午） 用户点头「跟」官方 v0.21.0。在 `/tmp/mihon-021`（worktree，`79fc3a0` = v0.21.0）上逐张 `git am -3`：0012 直接套上；0004 / 0009 上游已含，删除；
  0001 / 0003 / 0010 / 0011 / 0013 只改 `Downloader.kt` 的插入点（上游 `queueChapters` 改成 suspend + Boolean，我们改为返回 `QueueResult`，`DownloadManager.downloadChapters` 负责 `startDownloads()`；
  `MangaViewModel.startDownload` 现在在 `appScope` 里 join 入队，Snackbar 改到 `viewModelScope` 里弹）；0002 / 0008 更新器按 Metro 构造注入 + `isNightlyBuildType` 重写；
  0005 保活挂到 `DownloadWorker` / `LibraryUpdateWorker`（字段注入 `graph.inject(this)` 之后）；0006 保留上游 `DownloadNotifier` 自带的 500 ms `@Synchronized` 限流、只加速度 + 进度；
  0007 因上游删了 `AppUpdateDownloadJob` 改成新文件 `AppUpdateApkCleaner`（`NewUpdateScreenModel` 共用其 `updateApk()`）。
  本机验证：`:app:compileNightlyKotlin`、`spotlessCheck`（两处 ktlint 超长行各 fixup 进 0003 / 0010）、`:core:common:testDebugUnitTest` + `:domain:test` 共 104 个用例、`:app:assembleNightly -Penable-updater` 全过；
  干净 v0.21.0 树套 11 张补丁后与开发树只差版本号行。本机 Gradle 9.8.1 + `isolated-projects` 下带 `--max-workers=2` 两次卡死在并行配置阶段（`TaskPathProjectEvaluator.scheduleProjectsJustInTime` 空等），去掉该参数即正常——见 §7。
  推 `main` `9bcbd23f2` → `check_patches` run 38218165595 对最新稳定版（v0.21.0）转绿 → `dry_run` run 38218180863 绿（artifact 解析：`app.mihon.debug`、versionCode 3601、versionName `0.21.0-harmony.1-8157`、签名 `4bd90284…ea8a`、
  manifest 前台服务类型 `0x3` + `0x800`，DEX 含 `HarmonyLogBuffer` / `DownloadSpeedMeter` / `BackgroundKeepAlive` / `renameToOrCopy` / `/repo/releases.json` / `update.apk`，`resources.arsc` 含「未加入下载队列」「正在下载 %1$d 个章节」「后台保持运行」）
  → 正式 run 38219338765 → **`v0.21.0-harmony-preview.1`**（07:48 UTC，target `9bcbd23f2`，非 draft / prerelease；arm64 26,889,289 B，SHA-256 `94c147b4…4344`，universal 67,198,288 B，SHA-256 `88bae6cd…027b`；
  重新下载的 Release 资产包名 / versionCode / 签名复核一致；`repo` 分支 `094ef55`，`releases.json` 第一项即 preview.1，共 12 条）。
- 2026-10-12（晚） 用户：「mihon 能不能也加上全景的选项」+ 要求改用「主代理解析意图、Grok 子代理执行、主代理复核」的流程（`/workspace/.cursor/rules/orchestration.mdc`，本轮首次使用）。
  补丁 0014 由子代理（grok-4.7-high-fast）在 `/tmp/mihon-021` `dev-021` 上写成一个提交 `cdefaae`（19 个文件，+581 / −40，含 i18n 三语）；主代理复核作者 / diff（与 anikku-harmony 0015 + 0020 同源，`// Harmony` 标注完整）并独立重跑 `flock /tmp/gradle.lock ./gradlew :app:compileNightlyKotlin spotlessCheck :domain:test`（不带 `--max-workers`）通过。
  12 张补丁在干净 v0.21.0 上套用后与开发树只差版本号行。推 `main` `f4d55a24f` → `check_patches` run 38270707846 绿 → `dry_run` run 38270706712 绿 → 正式 run 38271885997 → **`v0.21.0-harmony-preview.2`**（15:47 UTC，target `f4d55a24f`，非 draft / prerelease；
  `app.mihon.debug`，versionCode 3602，versionName `0.21.0-harmony.2-8158`，签名 `4bd90284…ea8a`，arm64 26,922,641 B，SHA-256 `0ae2b296…37cc`，universal 67,231,640 B；DEX 含 `ComfortableGridPanorama` / `COMFORTABLE_GRID_PANORAMA` / `VerticalStaggeredGridFastScroller` / `LazyLibraryStaggeredGrid` / `rememberCoverRatio` / `getColumnCount`，
  `resources.arsc` 含「Panorama comfortable grid」「全景松散网格」「全景鬆散格狀」；`repo` 分支 `df4609e`，`releases.json` 第一项即 preview.2，共 14 条）。同轮 Anikku 浏览页 / 相关作品页全景网格为 anikku-harmony 0021（`v0.2.0-harmony-preview.12`）。
- 2026-10-12（深夜） 用户三件事：「能不能加个全景紧凑网络」「上下滑动全景网格时右侧竖列进度条好像会抽搐」「mihon 好像没正常拉到更新，看到最近的版本 12 日下午 8.00 的」。
  第三件的根因：官方 v0.21.1 于 10-12 发布，定时任务 run 38246143227（`schedule`）自动发了 `v0.21.1-harmony-preview.1`（3701），但更新器 `latest()` 取本频道列表第一项，而镜像 `releases.json` 把 `v0.21.0-harmony-preview.2` 排在前面（GitHub `/releases` 顺序不保证按版本）→ 补丁 0017。
  0015 / 0016 由子代理（grok-4.7-high-fast）在 `/tmp/mihon-021` `dev-021` 写成；主代理复核：0016 的「满行条目」判断从 `@Suppress("INVISIBLE_REFERENCE")` 强转内部 `LazyStaggeredGridMeasuredItem.span` 改为宽度启发式，并按 Compose 源码（`LazyStaggeredGridMeasure.kt`：`beforeContentPadding` 只在 `place()` 时加进 `contentOffset`）把 `scrollOffset` 里多加的顶部 padding 去掉，估算段与 Anikku 0023 `diff` 一致；0017 主代理自己写。`flock /tmp/gradle.lock ./gradlew :app:compileNightlyKotlin spotlessCheck :domain:test` 通过。
  17 张补丁在干净 v0.21.1 上套用后与开发树只差上游 0.21.0 → 0.21.1 的改动和版本号行。推 `main` `93c8cbd63`（+ `940acfa51` 改 0016 提交说明）→ `dry_run` run 38280545014（14 张）/ 38283415443（17 张）绿 → 正式 run 38284349214 → **`v0.21.1-harmony-preview.2`**（17:33 UTC，target `940acfa51`，非 draft / prerelease；
  `app.mihon.debug`，versionCode 3702，versionName `0.21.1-harmony.2-8176`，签名 `4bd90284…ea8a`，arm64 26,940,089 B，SHA-256 `85156a26…`，universal 67,249,088 B；DEX 含 `CompactGridPanorama` / `COMPACT_GRID_PANORAMA` / `StaggeredGridMeasurements`，`-harmony(?:-preview)?` 正则出现 2 次（domain + data），`resources.arsc` 含「Panorama compact grid」「全景紧凑网格」「全景密集格狀」；`repo` 分支 `releases.json` 第一项即 preview.2，共 15 条）。同轮 Anikku 0022 / 0023 / 0024 → `v0.2.0-harmony-preview.13`。
- 2026-10-13 用户：「滚动条还是会有些抽搐，我有时候也发现上下滑动的时候，各个资源块的排版也会出现轻微抽搐」「全景下，滑动时也有比较明显的掉帧的感觉」。根因见 §5.1 补丁 0018（格子先按默认横版排、解码完改竖版，瀑布流整列重测；横竖两个 Compose 调用点拆掉重建图片；滚动条残余抽搐是同一件事，0016 没动）。
  子代理（grok-4.7-high-fast）在开发树 `/tmp/mihon-0211-clean` `dev-0211`（v0.21.1 + 17 张）写成提交 `999bfa3`；主代理定根因与方案并复核。`:app:compileNightlyKotlin spotlessCheck :domain:test` 通过。导出 `patches/0018-library-panorama-stable-cell-shapes.patch`（`PanoramaCoverShapes.kt` 与 Anikku 0025 逐字节相同）。干净 v0.21.1 树 `/tmp/mihon-verify18` 套 18 张成功（versionCode 3703），4 个关键文件 `cmp` 一致。
  模拟器（本地 `assembleNightly` 的 x86_64 包，AVD harmony34，TCG 软件加速）：本地源 400 个条目（每 3 个 1 竖 2 横，合成 PNG），浏览页切「全景紧凑网格」后横竖格子形状全部正确；滑动后 `files/harmony_panorama_cover_shapes.txt` 落盘（18 行，竖 `1.500` / 横 `0.563`）；`am force-stop` 重启后再进，排版一致。掉帧测不了（软件加速），要用户真机确认。
  推 `main` `fa0dc1020` → `dry_run` run 38369348892 绿 → 正式 run 38370403634 → **`v0.21.1-harmony-preview.3`**（08:41 UTC，target `fa0dc1020`，非 draft / prerelease；
  `app.mihon.debug`，versionCode 3703，versionName `0.21.1-harmony.3-8177`，签名 `4bd90284…ea8a`（与 preview.2 相同），arm64 26,940,089 B，SHA-256 `8b85d3f0…`，universal 67,249,088 B。**体积与 preview.2 逐字节相同**：APK 有对齐填充，连续几版大小都一样，分辨版本看 SHA-256 / versionCode，不看体积。DEX 含 `PanoramaCoverShapes`（`classes.dex` 1 处 + `classes2.dex` 8 处）；`repo` 分支 `releases.json` 第一项即 preview.3，共 16 条）。同轮 Anikku 0025 → `v0.2.0-harmony-preview.14`。Animeko 不适用。
- 2026-10-13 用户先说 Anikku 全景紧凑仍卡（见 anikku-harmony 0026），接着「现在看 mihon 也会抖，是不是无解了？」。根因见 §5.1 补丁 0019：0018 的静止判断在 `scrollToItem` 的间隙当成已经停下；浏览页要等格子上屏才学形状。
  开发树 `/tmp/mihon-0211-clean` `dev-0211` 提交 `6606b27`。`:app:compileNightlyKotlin :app:spotlessCheck` 通过。导出 `patches/0019-library-panorama-settle-debounce-browse-prefetch.patch`（`PanoramaCoverShapes.kt` 与 Anikku 0027 逐字节相同）。干净 v0.21.1 树 `/tmp/mihon-verify19` 套 19 张成功（versionCode 3704），关键文件 `cmp` 与开发树一致。本轮没上模拟器（共享文件与 Anikku 已测的那份相同）。
  推 `main` `6d70f6e8d` → `check_patches` run 38381657802 绿 → `dry_run` run 38381668615。计划发 **`v0.21.1-harmony-preview.4`**（versionCode 3704）。已发布并核对：正式 run 38382851640（10:28 UTC，target `6d70f6e8d`），`app.mihon.debug` versionCode 3704、versionName `0.21.1-harmony.4-8178`，签名 `4bd90284…ea8a` 不变，arm64 26,940,089 B（体积又与上一版相同，是对齐填充）、SHA-256 `b0c03b8f…`，DEX 含 `PrefetchPanoramaCoverShapes` / `rememberPanoramaGridSettled`；`repo` 分支 `releases.json` 第一项即 preview.4（共 17 条）。同轮 Anikku 0026 / 0027 → `v0.2.0-harmony-preview.15`。Animeko 不适用。
- 2026-10-13（再稍后）用户：「好像还是会抖，比如往下滑动的时候，右侧滑动块可能会有一小段丝滑下滑，然后突然抽动一下向上移动一丝，再移动回来，大概频率是每一行抽动一下，是不是没找到根因呢？mihon，anikku都是」。根因见 §5.1 补丁 0020：0019 修的是格子形状；旧滚动条以编号最小的可见格子为锚，换格时公式偏差变，大约每行回跳。
  开发树 `/tmp/mihon-0211-clean` `dev-0211` 提交 `98ff730`。`:presentation-core:spotlessCheck :app:compileNightlyKotlin` 通过。导出 `patches/0020-presentation-staggered-scroller-stable-thumb.patch`（`private class StaggeredGridEstimate(` 到 `// Harmony <--` 与 Anikku 0028 逐字节相同）。干净 v0.21.1 树 `/tmp/mihon-verify20` 套 20 张（`prepare-source.sh … v0.21.1 5`）成功，关键文件 `cmp` 与开发树一致。拇指顺不顺模拟器（只有软件加速）测不了。
  推 `main` `3d89a0796` → `check_patches` run 38421701462 绿 → `dry_run` run 38421777350 绿 → 正式 run 38424091586 → **`v0.21.1-harmony-preview.5`**（15:47 UTC，target `3d89a0796`），`app.mihon.debug` versionCode 3705、versionName `0.21.1-harmony.5-8179`，签名 `4bd90284…ea8a` 不变，arm64 26,940,093 B、SHA-256 `d9639da6…`，DEX 含新滚动条字段；发出时 `repo` 分支 `releases.json` 第一项即 preview.5（共 19 条）。同轮 Anikku 0028 / 0029 → `v0.2.0-harmony-preview.16`。Animeko 没有这套瀑布流快速滚动条，不适用。这一版随后被 0.21.2 系取代，见下一条。
- 2026-10-13（16:09 UTC）用户：「为啥mihon没在0.21.2继续更新？现在手机提示装的0.21.2那个，0.21.1显示版本过老不给装了」。上游 Mihon 当天 04:27 UTC 发了 v0.21.2，定时 run 38392710194（11:47 UTC，target `f32a21972`，含 0001–0019）已自动发 **`v0.21.2-harmony-preview.1`**（versionCode 3801），用户手机升到了它。15:47 在 0.21.1 上发的 preview.5（3705）号更小，被当成降级。补救：同一套 20 张补丁在干净 v0.21.2 树 `/tmp/mihon-verify212` 套用成功（`prepare-source.sh … v0.21.2 2`，versionCode 3802），跳过单独 dry_run（preview.1 已用前 19 张编过，0020 只改 `VerticalFastScroller.kt`，正式 run 编译失败不会发布）。正式 run 38427442080 → **`v0.21.2-harmony-preview.2`**（16:09 UTC，target `3d89a0796`），versionCode 3802、versionName `0.21.2-harmony.2-8191`，签名 `4bd90284…ea8a` 不变，arm64 26,956,473 B、SHA-256 `1a9cd9d5…`，DEX 含新滚动条字段。`releases.json` 前三项为 preview.2、preview.1、`v0.21.1-harmony-preview.5`（共 20 条）。preview.5 保留未删。
  防降级：`harmony_preview.yml`「Resolve release version」在非 dry_run 且目标 tag 还不存在时，按「上游版本.N」`sort -V`，比已发布最高的旧就 `exit 1`（「installs would be a downgrade」）。已存在的 tag 仍 skip。本地用真实 tag 列表测过（0.21.1 preview.6 拒绝；0.21.2 preview.3、0.21.3 preview.1、0.21.10 preview.1 放行）。CI 上没实际触发过拒绝路径。提交 `fd1835633`（已推 main）。这是发版时没先看最新上游底座的疏漏。
- 2026-10-13（发版）用户两件：① 全景网格末尾一项总进最短列，右边只短一丝也放右边，左边空一块；② 折叠屏展开从两列变四列，最后几项和前面空一格，滑一下才重排。根因见 §5.1 补丁 0021：Compose `LazyVerticalStaggeredGrid` 零容差最短列，列数变化 `laneInfo.reset()` 把可见项当新起点。做法：自建 LazyLayout，放进底边 ≤ 最短列 + 本项高×0.5 的最左列；列数 / 宽度变化同一次测量里重算并用视口顶部项 key 钉住；快速滚动条用真实内容高度，0020 的 `StaggeredGridEstimate` 删除。
  开发树 `/tmp/mihon-verify212` `dev-0021` 提交 `08bd109`（底座 v0.21.2 + 0001–0020）。`:presentation-core:spotlessCheck` `:app:spotlessCheck` 通过，`:presentation-core:testDebugUnitTest` 16/16，`:app:compileNightlyKotlin` 通过。导出 `patches/0021-presentation-panorama-masonry-reading-order.patch`（`PanoramaMasonry.kt` / `PanoramaMasonryLayout.kt` / `PanoramaMasonryLayoutTest.kt` 与 Anikku 0030 逐字节相同；`PanoramaCoverShapes.kt` 起只差阈值常量名 `RATIO_SWITCH_TO_PANORAMA` / `RatioSwitchToPanorama`）。干净 v0.21.2 树套 21 张成功（versionCode 3803），12 个改动文件 `cmp` 一致。未上模拟器。
  推 `main` `e5c6c734e` → `check_patches` run 38453485932 绿 → `dry_run` run 38453484931 绿 → 正式 run 38454541710 → **`v0.21.2-harmony-preview.3`**（target `e5c6c734e`），`app.mihon.debug` versionCode 3803、versionName `0.21.2-harmony.3-8192`，签名 `4bd90284…ea8a` 不变，arm64 26,940,089 B（SHA-256 前缀 `58ea2694f782`），universal 67,249,088 B，DEX 含 `PanoramaMasonryLayout`；`repo` 分支 `releases.json` 第一条即此版（共 21 条）。同轮 Anikku 0030 → `v0.2.0-harmony-preview.17`。Animeko 没有这套网格，不适用。行为差异：Mihon 浏览页仍无快速滚动条；Mihon 书架拇指停留从 2 秒变为系统默认约 300 ms。
- 2026-10-14 用户：「mihon每次更新界面，点一第一下下载会失败，后面再点就可以下了」。根因见 §5.1 补丁 0022：更新页对 GitHub 发布资产（302 → `release-assets.githubusercontent.com`）只用共用客户端发一次（读超时 30 秒、整次 2 分钟）；大陆第一次连 CDN 常在连上后卡住或被重置，OkHttp 不在同一次调用里重试，异常就删 `update.apk`，按钮变「重试」。置信度约七成，海外 VM 未复现（JVM 复刻 OkHttp 5.5 拦截器链连下两次成功，991 ms / 215 ms）。排除 ViewModel 取消、清理器竞态、302 包进度体、进度回调除零、DoH（默认关）。调研子代理 bc-eab8129c，实现子代理 bc-d54ee94b。
  做法：新文件 `AppUpdateApkDownloader.kt`。专用客户端读 60 秒 / 整次 10 分钟（全局 NetworkHelper 不变）；最多 4 次，间隔 2/4/8 秒；IOException 与 5xx 重试，416 删文件从 0 重来，其它 4xx 直接失败；206 追加、200 重写；中途不删文件，最终失败才删；能读出 versionCode 的完整旧包删掉重下，半截续传。失败红字：下载超时 / 网络中断 / 服务器返回 HTTP N / 存储写入失败。`AppUpdateApkCleaner.updateApk` 在 `externalCacheDir` 为 null 时回落 `cacheDir`。重做时保住 `newCachelessCallWithProgress(request, listener, existingSize)` 与 `ProgressResponseBody` 的 existingSize 语义。
  开发树 `/tmp/mihon-verify212` `dev-0022` 提交 `e1a029d`（底座 v0.21.2 + 0001–0021）。`:app:spotlessCheck :app:compileNightlyKotlin :app:testDebugUnitTest --tests '*AppUpdateApkDownloaderTest*'` 退出 0，3/3、skipped 0（JDK HttpServer：半截断开后续传、416 从头、404 不重试）。导出 `patches/0022-updater-retry-and-resume-the-update-download.patch`。干净 v0.21.2 以 N=4 套全部 20 张（0001–0022，0004 / 0009 早已删除） → versionCode 3804，与开发树只差版本号。
  推 `main` `779cccafc` → `check_patches` run 38512243044 绿 → `dry_run` run 38512260459 绿 → 正式 run 38513011212 → **`v0.21.2-harmony-preview.4`**（非 draft、非 prerelease，target `779cccafc`），`app.mihon.debug` versionCode 3804、versionName `0.21.2-harmony.4-8193`，签名 `4bd90284…ea8a` 不变，arm64 26,942,369 B（SHA-256 前缀 `fbcf9c960068`），universal 67,251,368 B，DEX 含 `Update download attempt`、`update.apk`，资源含 `harmony_update_download_timeout`；`repo` 分支 `releases.json` 22 条，第一条即此版。Anikku 不适用（上游 `downloadFileWithResume` 已在 worker 内重试）。Animeko 待确认（每个地址只下一次，失败后自动换 universal；大陆网络点更新看是否先失败后自动成功）。从旧版升到 preview.4 的这一次仍是旧代码在下载，第一下可能还会失败，再点即可。
- 2026-10-14（07:39 UTC）用户四件：① 书架点进资源再退出回到最顶；② 2000 项书架高速松开后惯性滑动一卡一卡（Anikku 同样）；③ 按住滑动条快速下翻，滑动条变透明，被识别成按着内容下滑，变成上翻；④ 自动列在折叠情况下只有两列，横封面偏小。根因见 §5.1 补丁 0023–0029，与 anikku-harmony 0031–0037 一一对应、同源。
  子代理（grok-4.7-high-fast）实现。主代理复跑 `:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin --rerun-tasks` 通过（presentation-core 35 个用例，0 失败，2 个门控跳过；app 28 个，0 失败）。干净树 `/tmp/mihon-verify213`（v0.21.2，N=5）套用成功，12 个改动文件与开发树 `cmp` 一致。`PanoramaMasonry.kt` / `PanoramaMasonryLayout.kt` / `PanoramaMasonryLayoutTest.kt` 与 Anikku 逐字节相同。共享测试不再依赖 `java.awt` / `com.sun.management`。没有真机 / 模拟器手势测试。上游列表 / 网格滚动条的 `LaunchedEffect(firstVisibleItemScrollOffset)` 没改。
  推 `main` `0066de0e4` → `check_patches` run 38527739609 绿 → `dry_run` run 38527787706 绿 → 正式 run 38529020510 → **`v0.21.2-harmony-preview.5`**（07:39 UTC），`app.mihon.debug` versionCode 3805、versionName `0.21.2-harmony.5-8200`，签名 `4bd90284…ea8a` 不变，arm64 26,942,369 B（SHA-256 前缀 `1f52f85fbac7`），universal 67,251,368 B，DEX 含 `PanoramaColumns$Tiered`、`holdOpaqueWhileThumbGrabbed`、`PanoramaMasonryContentEpoch`；`repo` 分支 `releases.json` 23 条，第一条即此版。series 27 张（0001–0029，0004 / 0009 已删）。同轮 Anikku 0031–0037 → `v0.2.0-harmony-preview.18`。Animeko：滚动条按住、惯性卡顿、自动列宽不适用；返回丢位置待确认。
- 2026-10-14（10:31 UTC）用户两件：横封面多时全景右列空，以及滑到底再往回甩惯性消失（「我没动滑块」）。根因见 §5.1 补丁 0030–0032，与 anikku-harmony 0038–0040 一一对应、同源。0030 `PanoramaColumns.Shaped`；0031 形状模式（`PanoramaShapeMode.kt` 在 app 层，`committedShapeVersion` 只在主线程写、measure 不读，列数变化不 bump epoch）；0032 热区收回为 `ThumbThickness + endInset`。三个共享文件与 Anikku 逐字节相同。测试依赖不进包（nightly 对库模块回退 release 变体）。
  子代理（grok-4.7-high-fast）实现。主代理复跑 `:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin --rerun-tasks` 通过（presentation-core 51 个用例，0 失败，2 跳过；app 35 个）。干净树 `/tmp/mihon-verify214`（v0.21.2，N=6）套用成功，18 个改动文件与开发树 `cmp` 一致。没有真机手势测试。
  推 `main` `e8220fba2` → `check_patches` run 38548385048 绿 → `dry_run` run 38548395586 绿 → 正式 run 38549485379 → **`v0.21.2-harmony-preview.6`**（10:31 UTC），`app.mihon.debug` versionCode 3806、versionName `0.21.2-harmony.6-8203`，签名 `4bd90284…ea8a` 不变，arm64 26,958,753 B（SHA-256 前缀 `e7233bbfcd39`），universal 67,267,752 B，DEX 含 `PanoramaColumns$Shaped`、`PanoramaShapeMode`、`committedShapeVersion`；manifest 无 ui-test 的 ComponentActivity；DEX 里 `robolectric` 字符串 5 处，与上一版相同。`repo` 分支 `releases.json` 24 条，第一条即此版。series 30 张（0001–0032，0004 / 0009 已删）。同轮 Anikku 0038–0040 → `v0.2.0-harmony-preview.19`。Animeko：列数按形状、滚动条热区、惯性都不适用。
- 2026-10-14（11:15 UTC）用户：「我感觉不是加宽的原因，mihon书架有时候不在底部的时候还是会滑动完没有惯性，之前应该没有的，要有办法定位吗？」（10:53 UTC）。preview.6 收回热区（0032）只解释「到底往回滑」那一下。书架中间偶发另有原因。读代码，全景网格的惯性只可能这几种原因提前结束：新的滚动请求或按下打断；某一帧没吃满位移；外层吃掉松手速度；网格被重建；松手速度本身是 0。最可疑的是最后一种：Compose 的 VelocityTracker 在「最后一次 move 到 up 的间隔 > 40 ms」时把速度算成 0。没有真机数据，不能定论，因此先发诊断版，不改滑动行为。根因与做法见 §5.1 补丁 0033，与 anikku-harmony 0041 同源。`PanoramaScrollTrace.kt` / `PanoramaMasonry.kt` 与 Anikku 逐字节相同。轨迹最多 400 条，与 `HarmonyLogBuffer`（0012）分开，附在「转储崩溃日志」末尾。只记全景网格。
  `:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin` 通过（presentation-core 54 个用例，0 失败，2 跳过；app 35 个）。干净树 `/tmp/mihon-verify215`（v0.21.2，N=7）套用成功，20 个改动文件与开发树 `cmp` 一致。开发树 `dev-0023` 提交 `7b0bddc`。新测试 3 个：顺序 up → fling start → fling done，dist 4462、frames 132；`scrollToOffset 1000` 之后紧跟 `fling cancelled`；4 次 move 后停 60 ms 再松手，得 `gapLastMove=60ms trackerV=0 recentV=-2215`，`fling start v=0`，惯性 0。
  推 `main` `15289c4df` → `check_patches` run 38553790858 绿 → `dry_run` run 38553801784 绿 → 正式 run 38553912820 → **`v0.21.2-harmony-preview.7`**（11:15 UTC），`app.mihon.debug` versionCode 3807、versionName `0.21.2-harmony.7-8204`，签名 `4bd90284…ea8a` 不变，arm64 26,958,753 B（SHA-256 前缀 `9f97e5d14716`；体积与 preview.6 相同，是对齐填充），universal 67,267,752 B，DEX 含 `Panorama scroll trace`、`gapLastMove=`、`fling start v=`；manifest 无 ui-test。`repo` 分支 `releases.json` 25 条，第一条即此版。series 31 张（0001–0033，0004 / 0009 已删）。正式 run 在 dry_run 结束前就触发了（等待脚本把一次 API 报错当成完成）；同一并发组里排队，等 dry_run 成功后才执行，结果无影响。同轮 Anikku 0041 → `v0.2.0-harmony-preview.20`。Animeko 没有全景瀑布流，这条日志不适用；若是触摸投递卡顿，LazyColumn 也可能受影响，等日志定性后再看。
- 2026-10-14（12:01 UTC）用户 11:37 UTC 发来 `mihon_crash_logs_318b.txt`（preview.7）：「最后一次滑动卡住，一直往下滑很流畅，最后一次往上滑的时候，卡，没惯性了」。11:39 UTC 发来 `mihon_crash_logs_ab65.txt`：「我连续上滑五次卡」。往下翻的 fling 全部正常；一次往回甩之后连续 5 次 `fling start v=0`，同时 `trackerV` 6310–13529、`gapLastMove` 7–12 ms。preview.7「>40 ms 速度归零」的猜测被否定。根因与做法见 §5.1 补丁 0034，与 anikku-harmony 0042 同源。`PanoramaMasonry.kt` 与 Anikku 逐字节相同。没碰到两端时返回精确 delta。0033 的诊断日志保留。
  `:presentation-core:spotlessCheck :app:spotlessCheck :presentation-core:testDebugUnitTest :app:testDebugUnitTest :app:compileNightlyKotlin` 通过（presentation-core 55 个用例，0 失败，2 跳过；app 35 个）。干净树 `/tmp/mihon-verify216`（v0.21.2，N=8）套用成功，20 个改动文件与开发树 `cmp` 一致。开发树 `dev-0023` 提交 `be7349e`。新测试 `return flicks under pull to refresh keep their velocity far down the list`：offset 70000，修前起速 `[5120, 5120, 5120, 0, 0, 0, 0]`，修后往回甩 -5120。
  推 `main` `00a9ff810` → `check_patches` run 38558901975 绿 → `dry_run` run 38558925925 绿 → 正式 run 38559877474 → **`v0.21.2-harmony-preview.8`**（12:01 UTC），`app.mihon.debug` versionCode 3808、versionName `0.21.2-harmony.8-8205`，签名 `4bd90284…ea8a` 不变，arm64 26,958,753 B（SHA-256 前缀 `79476a3a4758`；体积与 preview.7 相同，是对齐填充），universal 67,267,752 B；manifest 无 ui-test。`repo` 分支 `releases.json` 26 条，第一条即此版。series 32 张（0001–0034，0004 / 0009 已删）。这次 dry_run 成功后才触发正式 run，等待脚本已修好。同轮 Anikku 0042 → `v0.2.0-harmony-preview.21`。Animeko 不适用（没有自写的 ScrollableState）。
- 2026-10-14（12:51 UTC）用户：「好像mihon的惯性消失问题解决了，但是为啥滑动块又很难按到了」。精确 delta 已确认修好惯性；收回热区后只剩画出来的 12 dp 拇指可按。补丁 0035（与 anikku-harmony 0043 同源）：热区恢复 32 dp + 边距，拇指本体按下即抓，旁边 20 dp 按住 120 ms 不动才抓，快甩照常滚内容。推 `main` `143b93517` → `check_patches` run 38564906465 绿 → `dry_run` run 38564985618 绿 → 正式 run 38566077398 → **`v0.21.2-harmony-preview.9`**（12:51 UTC），`app.mihon.debug` versionCode 3809、versionName `0.21.2-harmony.9-8206`，签名 `4bd90284…ea8a` 不变，arm64 26,958,757 B（SHA-256 前缀 `01b7d412a7a6`）。dry_run 成功后才触发正式 run。
- 2026-10-14 用户：解锁后第一下滑不动，随后说「要不不加这个解锁后第一下不动了，好像又没有问题了」，诊断提交已撤掉，没有发版。
- 2026-10-14（13:35 UTC）用户：想记录上下滑 / 惯性时的帧率或耗时，「有时候又很丝滑」，要一个调试按钮导出脱敏日志，不依赖 IP 或 token。补丁 0036（与 anikku-harmony 0044 同源）：设置 → 高级 →「滚动性能记录（调试）」，左下角「记录」按钮经分享面板导出只含数字的文件；归档仓新增 `tools/scroll-perf-analyze/analyze.py`。推 `main` `bdcc008e0` → `check_patches` run 38570494789 绿 → `dry_run` run 38570546143 绿 → 正式 run 38572070546 → **`v0.21.2-harmony-preview.10`**（13:35 UTC），`app.mihon.debug` versionCode 3810、versionName `0.21.2-harmony.10-8207`，签名 `4bd90284…ea8a` 不变，arm64 26,976,657 B（SHA-256 前缀 `0df8d7c4aea7`），DEX 含 `harmony_scroll_perf_recorder`、`privacy: no titles`。开发树 HEAD 复跑 `:presentation-core:testDebugUnitTest :app:testDebugUnitTest` 通过（presentation-core 59 个用例，0 失败，2 跳过；app 41 个）。
- 2026-10-14（13:43 UTC）`repo` 分支索引按 `created_at` 倒序（`1db0e3620`，`release_index` run 38574198250）：GitHub 列表接口把 mihon-harmony preview.10 排在 6 个旧版之后，App 按版本号取最大所以不受影响，但只取第一页时新版可能被挤出。三个流水线同一改动。同时更正补丁 0035 正文里的同源编号（原写成 anikku-harmony 0044），只改提交信息，代码不变。
- 2026-10-14（约 14:00 UTC）用户：书架网格顺，浏览页全景网格越甩越卡。记录 `mihon_scroll_perf_20261014-220359`（华为 HOP-AL10，卓易通里的 Android 16，90 Hz）：动画仍约 90 Hz（最长间隔 ≤21 ms），浏览甩动的已报告帧从 22:03:36–38 的 98–99% 掉到 22:03:47 以后的 53–62%，书架仍 95–100%；已报告帧都没超时（p50 6.8→8.9 ms，2560 帧甩动 0 次 jank）；变卡时进程 CPU 约 43%（顺时约 83%），坏的甩动没有 GC，温控 0，90→60 Hz 只在停手空隙；整表重排（布局 16–20 ms）大多在还顺或停着时，46.774 秒后就没有了。两种假设还没分开：合成器 / `BLASTBufferQueue` 回压（22:03:50 后日志每秒 10–41 条），或 FrameMetrics 3 槽报告被丢（旧记录器没写 `dropCountSinceLastInvocation`）。浏览预取还在为每一行解码 128 px 硬件位图再扔掉，和可见封面抢 Coil 的 3 个解码槽。
- 2026-10-14（约 16:25 UTC）补丁 0037–0040（作者 Xun2202；grok-4.7-high 子代理实现，主代理复核，另有一次独立 grok 复核修了 8 处）。0037 记录器补丢帧计数、各阶段 p50/p90、封面加载、分线程 CPU，长按「记录」切换封面淡入 / 硬件位图 / 预取（只在内存，重启回到淡入开、硬件位图开、预取只读文件头），导出格式 `harmony-scroll-perf` 2。0038 滑动中第一次跨档等停稳 300 ms 再一次提交。0039 浏览预取默认只读文件头。0040 翻页追加、不再整表重排。推 `main` `33568c567` → `check_patches` run 38595775346 绿 → `dry_run` run 38595854992 绿 → 正式 run 38597112426 → **`v0.21.2-harmony-preview.11`**（约 16:25 UTC），`app.mihon.debug` versionCode 3811、versionName `0.21.2-harmony.11-8211`，签名 `4bd90284…ea8a` 不变，arm64 27,009,425 B（SHA-256 前缀 `544cefae3f39`），universal 67,318,424 B，DEX 含 `harmony-scroll-perf`、`HarmonyPerfToggles`、`HarmonyFramePerfSampler`、`mark toggle`、`harmony_fade`、`cpu_pool`、`privacy: no titles`。开发树 `/tmp/mihon-verify212` `dev-0024` HEAD `005f27b`。干净树 `/tmp/mihon-verify217`（v0.21.2，N=11）除版本号行外与开发树 `cmp` 一致。本地 `spotlessCheck`、`:app:compileNightlyKotlin`、presentation-core 65 个用例（0 失败，2 跳过）、app 49 个用例（0 失败）。series 38 张（0001–0040，0004 / 0009 已删）。`repo` 分支 `releases.json` 29 条、第一条 preview.11（索引提交 SHA 待确认）。Anikku 本轮没改：0038–0040 同病待修，0037 待移植；Anikku 浏览页另外的调色板解码、400 ms 延迟转圈、每行急切 `stateIn`、浏览页快速滚动条待确认。Animeko 不适用。越甩越卡是否修好，要等按归档 README §3 第 43 项录的对照文件。
- 2026-10-14（约 16:52 UTC）用户在 preview.11 上：浏览页很卡，「像封面一直没加载」；格子先占一大块横的再缩。记录 `mihon_scroll_perf_20261015-005028`、`mihon_scroll_perf_20261015-005436`（窗口 664×939 dp，展开竖屏）。drops 全是 0，漏掉的 vsync 是真的（浏览甩动中位 14%，书架 0%）；三个开关看不出差别。未知封面 9/16 跨两列；约 59 格在每次停下约 310 ms 后翻成竖的（20 项高度 14098→4092，59 项 31008→16957，视口跳 394–1628 px）。0038 / 0039 加重了这件事。采样大约每 530 ms 花 25–50 ms。另：展开横屏浏览一排 7 个（自动 = `Adaptive(128 dp)`，939 dp → 7），竖着 3 个觉得合适。根因与做法见 §5.1 补丁 0041–0045。
- 2026-10-14（约 19:10 UTC）补丁 0041–0045（grok 子代理在 4 个隔离 worktree 里实现；独立 grok 复核 0 高 / 4 中 / 3 低，都已修）。0041 记录器少读线程、统计已组合格子，导出 `harmony-scroll-perf` 3，采样线程 `HarmonyPerfSmpl`。0042 未知封面默认竖的 3/2 单列，占位档跟书架（0.60 / 0.40），已放下的格子留在原槽，预取滑动中不暂停（窗口 +60，同时 4 个）。0043 自动最小格宽 112 / 140 / 176 dp（分界 600 / 840），939 dp → 5 列。0044 浏览格子不再每帧读分页。0045 `HarmonyCoverHeaderProbe` 在显示前读封面尺寸。推 `main` `fcd0c73bb` → `check_patches` run 38618709323 绿 → `dry_run` run 38618768446 绿 → 正式 run 38619981541 → **`v0.21.2-harmony-preview.12`**（约 19:10 UTC），`app.mihon.debug` versionCode 3812、versionName `0.21.2-harmony.12-8216`，签名 `4bd90284…ea8a` 不变，arm64 27,009,425 B（与 preview.11 相同，是对齐填充；SHA-256 前缀 `3e2012802777`），universal 67,318,424 B，DEX 含 `HarmonyCoverHeaderProbe`、`idle_holes`、`cpu_smpl`、`HarmonyPerfSmpl`、`PanoramaMasonryTailEpoch`。开发树 `/tmp/mihon-verify212` `dev-0025` HEAD `f1adecd`。干净树 `/tmp/mihon-verify219`（v0.21.2，N=12）除 `app/build.gradle.kts` 外与开发树 `cmp` 一致。本地 `spotlessCheck`、`:app:compileNightlyKotlin`、presentation-core 71 个用例（69 通过，2 跳过）、app 70 个通过。series 43 张（0001–0045，0004 / 0009 已删）。`repo` 分支 `releases.json` 30 条、第一条 preview.12（索引提交 SHA 待确认）。Anikku 0041–0045 同病待移植，本轮没改。Animeko 不适用。真机看归档 README §3 第 44 项。

## 2026-10-25：紧凑导航与浏览时收起

- 顶栏普通字号采用 56dp，大字号保留 64dp；底部改用官方 64dp 最小高度的短导航组件，文字需要时可增长，保留系统安全区与至少 48dp 触控尺寸。
- 书架、更新、历史、来源/扩展页和源内容列表的标题用 Material3 `enterAlwaysScrollBehavior`，分类/筛选行仍可操作；搜索、多选、屏幕朗读时不自动收起标题。
- 底栏复用既有显示动画，只观察真实用户纵向滚动：向后累计 24dp 收起，反向 8dp 显示；横向切页、惯性与无法滚动的空/短列表不会触发隐藏，不消费位移或惯性。切换标签、选择模式复位，更多页和侧边导航保持可用。
- Mihon 0046 复用 Anikku 0046 的宽度分列算法，避免收起导航改变视口高度时换列；保留 Mihon 的 minLane 限制、局部重排与缓存。Mihon 0047 / Anikku 0048 的 `NavigationChrome.kt`、`NavigationChromeScrollTracker.kt` 及对应测试逐字节相同。
- 组件差异：Mihon 保留 NavigationSuiteScaffold，手机改用 ShortNavigationBarCompact；Anikku 用 ShortNavigationBar/ShortNavigationBarItem，隐藏未选中标签的旧偏好仍保留，投屏连接期间底栏不自动收起；Anikku 相关推荐页也接入标题收起。
- 机器检查覆盖方向阈值、边界/短列表、复位、不吞滚动/惯性以及列数不随高度变化。双应用签名构建与更新索引见归档仓现状；实际手感、字体与系统安全区由用户安装反馈。Animeko 使用独立 AniTopAppBar/多平台导航，不直接移植本次 Tachiyomi 组件。
- 依据：[华为 Pura X Max 官方比例](https://consumer.huawei.com/cn/phones/pura-x-max/specs/)、[Material3 顶栏行为](https://developer.android.com/reference/kotlin/androidx/compose/material3/TopAppBarDefaults)。不根据手机型号或物理像素写死 dp。

## 2026-10-25：整块导航收起、透明系统区域与快速恢复

- Mihon 0048 / Anikku 0049 跟进用户对 preview.13 / preview.26 的反馈：标题、分类、底栏统一使用 surface，标题滚动后也不变色；移除 MainActivity 手工底部遮罩，Android 10+ 关闭系统导航栏对比遮罩。保留时钟、状态图标和系统手势条。
- 浏览 Scaffold 用共同高度与折叠比例收起标题、顶部系统 inset、分类及源筛选行；完全收起后正文可画到透明状态栏下。底部安全 inset 仍作为列表末项滚动空间，避免最后一项被手势条遮住。普通详情/设置页不启用整块收起；搜索、多选和触摸探索仍复位并禁用自动隐藏。
- 底栏在 onPreScroll 首次反向用户拖动就恢复，不再等顶栏消费后的 8dp；仍不消费滚动或惯性。Mihon 用官方 NavigationSuiteScaffoldState.snapTo(Visible)，Anikku 显示 120ms / 隐藏 180ms，保留投屏和标签偏好。
- NavigationChrome.kt 及新增回滑/布局回归在两仓同源；布局回归检查完整收起无顶部空条以及展开恢复。版本、构建和真机状态以档案仓现状为准。
- 一手依据：[Android edge-to-edge](https://developer.android.com/develop/ui/views/layout/edge-to-edge)、[Compose Insets](https://developer.android.com/develop/ui/compose/system/insets-ui)、[Material3 顶栏滚动](https://developer.android.com/develop/ui/compose/components/app-bars)。

## 2026-10-25：同步悬浮导航与阔屏紧凑尺寸

- Mihon 0049 / Anikku 0050 跟进 preview.14 / preview.27 真机反馈：标题和分类不再各自压缩，二者在同一 topBar 容器整体平移；上下导航共用显隐状态和 140ms 动画。
- 首个真实用户向上滚动即收起，首个反向拖动即恢复；去掉隐藏24dp等待，监听不消费滚动/惯性，横向切页、惯性和短列表未消费的拖动不触发隐藏。搜索、多选、触摸探索、更多页及 Anikku 投屏的保护仍保留。
- 导航是悬浮层：Home 手机正文不再因底栏加减 padding，顶部整体平移保持测量高度；书架/分页顶部余量放进列表 contentPadding，可随正常滚动离开。收放动画不改视口或列表 padding，不替用户拖动漫画；末项保留实际导航/投屏和系统区域的滚动余量。
- 通用紧凑规则：字号比例≤1.3，窗口宽高比≥0.65或高度≤480dp时，标题48dp、底部48dp触控行；普通窗口保持56/64dp，大字号顶栏64dp并用官方底栏。分类保持48dp触控，不按设备型号写死。Mihon tablet NavigationSuite rail 保留，Anikku 投屏/标签/徽标保留。
- NavigationChrome.kt、NavigationChromeScrollTracker.kt、CompactNavigationBar.kt 及纯逻辑测试两仓一致；布局回归仅按 Compose 版本选择旧包或 v2 runComposeUiTest，按0/0.5/1确定进度验证正文边界/封面坐标不变、标题与分类距离不变、上下移动进度一致，并独立验证真实动画完成隐藏与恢复；不依赖固定80ms取样。版本和构建结果以归档现状为准。

## 2026-10-25：手势内锁定导航、滑块避让与统一留白

- Mihon 0050 / Anikku 0051 跟进 preview.15 / preview.28：轻微来回拖动不再反复收放。父 Scaffold 在 Initial 阶段只观察触摸，不消费事件；一次按住最多改变一次显隐，所有手指松开或取消后允许下一次手势切换；6dp同向位移确认意图，惯性和横向手势不触发。
- 恢复共用225ms缓出动画；隐藏随触摸速度从175ms缩至100ms，上下仍共用同一进度。保留系统动画缩放、无障碍/搜索/选择保护，正文视口和滚动padding不随动画变。
- List/Grid/Masonry快速滑块轨道与宿主内容padding取最大值，避开固定展开头部/底部安全区，去掉底部重复预留。轨道在导航收放时保持不变，短窗口不足放滑块时隐藏；Anikku独有不规则网格同步处理。
- 新的共享 browsingContentVerticalPadding 沿用窗口/字号规则：紧凑4dp、其他8dp，统一书架、浏览、Anikku相关推荐。48dp标题/分类触控与系统安全区保持；未发现重复顶部inset。Mihon相关推荐宿主不同，保留原有结构。
- 参考：Android [每次手势生命周期](https://developer.android.com/develop/ui/compose/touch-input/pointer-input/understand-gestures)、Material [175/225ms隐藏/恢复](https://github.com/material-components/material-components-android/blob/master/lib/java/com/google/android/material/behavior/HideViewOnScrollBehavior.java)、[Headroom方向容差](https://github.com/WickyNilliams/headroom.js/blob/master/src/Headroom.js)。一次手势锁定是依据用户小红书实测反馈设计，没有声称取得小红书源码。
- 共享NavigationChrome与tracker/spacing两仓一致；回归覆盖同手势反向锁定、松手后再切换、小幅容差、真实触摸事件和正文坐标稳定。版本、构建、产物和真机状态见归档现状。

## 2026-10-26：紧凑单行导航、磨砂背景与滑块联动

- Mihon 0051 / Anikku 0052 跟进 preview.16/29：阔/矮窗口把书架分类或浏览分页放进标题行下拉选择，保留左右Pager和搜索/多选入口；普通窗口保持两行。标题触控48dp，底栏在48dp行上方增加16dp徽标空间。
- 首屏顶部留白未滑走时，导航收起进度受实际第0项位移约束，不先飞走露空条；List/Grid使用含padding区域的第0项offset，避免矮行提前失去首项。中部仍悬浮，不改正文视口/滚动padding；保留一次触摸一次显隐与225ms恢复/速度感知收起。
- 快速滑块随可见导航调整轨道，系统区/FAB额外间距分开保留；按下/拖动冻结直到松手。视觉16dp、直接命中28dp，额外侧区仍短按住抓取，不扩大整条边缘热区。首末钉0/1并实际到达；修规则网格过期范围缓存及Anikku不规则网格先返回导致高度无法初始化。
- 两款列表导航复用Haze 1.7.2（Anikku原已使用）：18dp背景模糊、深浅色半透明tint和轻噪点，正文作为source，图标文字保持清晰。非硬件加速/API<31自动用可读半透明底色；磨砂观感和性能待真机。详情MangaToolbar显式Color.Transparent，不加入磨砂、不随滚动或选择状态变色。
- NavigationChrome/BrowsingGlass/BrowsingScrollInsets/BrowsingScrollGeometry/BrowsingTabSelector/CompactNavigationBar两仓同源。回归覆盖首屏短行对齐、正文不被推拉、气泡原始坐标、分类菜单可达及系统/FAB轨道边界。Anikku独有IrregularGrid与源码Scaffold保留差异。版本/构建/签名/索引以归档现状为准。

## 2026-10-26：标题内横滑分类、底栏与刷新层级

- Mihon 0052 / Anikku 0053 跟进preview.17/30真机反馈：用户认可导航动画；阔屏保留书架/浏览标题，中间恢复14sp横滑分类与2dp选中条。分类视口独立裁剪，两端10dp渐隐，标题和右侧按钮不随分类移动；Pager、计数、搜索/选择及普通窗口两行布局保留。
- 紧凑浏览标题行48→40dp，系统WindowInsets保留，详情顶栏尺寸与始终透明规则不改；大字号沿用宽松高度。
- 底栏总内容高度64→56dp：8dp徽标余量+48dp视觉行均可点击；选中背景覆盖图标和文字，左右各4dp。徽标独立布局，10sp/12sp行高、最大99+，完整数量仍用于无障碍，五项窄窗口与1.3字号检查原始四边坐标及图标/标签居中。
- 书架/扩展/Feed默认刷新指示器原来从y=0绘制，被顶栏盖住。共享Scaffold提供窗口坐标下的可见顶栏下缘，PullRefresh据自身位置避让，并裁剪入场动画；保留更大显式padding，详情/更新等调用一起覆盖。首次测量前不画，防止首帧闪到顶栏后；不抬高整个列表或改变正文padding。
- 用户追加滑块消失太快：统一列表/网格/全景/Anikku不规则网格的停留为2.5秒，随后沿用系统淡出时长；按住保持及再次滚动重置计时不变。FastScrollerVisibility.kt两仓逐字节相同。
- 用户继续追加贴边与窄缝：屏幕左右仅1dp，网格实际封面横纵间距从约12dp收至3dp，列表上下各1.5dp；移除格内重复padding并同步全景高度合同，保留系统横向安全区、标题padding/行高与选中描边。书架/浏览/相关推荐及横向搜索封面行保持一致。
- 滑块使用独立列表兄弟节点作为Haze背景，12dp模糊/浅色高光/细轮廓；避免从包含滑块自身的祖先source采样，老系统或软件绘制回退半透明底。
- 共享组件两仓同源；Anikku自定义Scaffold/侧栏/consumed insets、独有徽标偏好/投屏和其他导航样式保留。回归覆盖横滑选择不移标题按钮、五项气泡边界、内移容器刷新避让与详情显式inset，复用原导航手势/正文稳定测试。Animeko为独立AniTopAppBar，不直接移植；版本与签名证据见归档现状。
