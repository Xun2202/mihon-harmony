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
2. **跳过已存在的 Release**（`dry_run` 时不跳过）。这是定时任务不重复编译的关键。
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
8. **Release 索引**：`scripts/write-release-index.sh` 把 `gh api repos/<repo>/releases?per_page=30` 原样存成 `releases.json`、`jq` 取最新正式版存成 `latest.json`，
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

### 5.2 加新补丁

在套完现有补丁的源码树上直接改代码并 commit（message 写清楚为什么），`git format-patch -1` 导出，
放进 `patches/`，追加到 `series` 末尾，更新 README 的补丁表。

### 5.3 验证改动但不发版

Actions → Harmony Preview → Run workflow，勾选 `dry_run`。构建完成后在该次运行的 Artifacts 里下载 APK，
可以用 `apksigner verify --print-certs` 或任意 APK 签名查看工具确认证书 SHA-256 与现有 Release 一致。

### 5.4 正式出新版

Run workflow，`upstream_tag` 填官方 tag（留空取最新稳定版），`patch_number` 从 1 开始；同一官方版本改了补丁要重发就填 2、3……
同名 Release 已存在会直接跳过。约 7–10 分钟。

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
| 全景网格拖右侧滚动条、或连续甩两下时格子还会跳；浏览页新滑出来的格子第一次形状不对 | preview.3（0018）把「停下」定义成 `isScrollInProgress` 为假。拖拇指是一串 `scrollToItem`，中间为假就把新形状写进布局；浏览页要等上屏才学形状。0019（v0.21.1-harmony-preview.4）起连续 300 ms 不滚动才算停下，浏览页对已加载未上屏的封面按 128 px 提前学形状（`PanoramaCoverShapes.kt` 与 Anikku 0027 逐字节相同）。刚打开的第一屏在静止时仍可能翻一次；下载失败保持默认横版。真机确认拖拇指和滑动 |

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
