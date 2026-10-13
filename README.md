> [!IMPORTANT]
> ## Mihon Harmony Preview（非官方 HarmonyOS / 卓易通 兼容构建）
>
> 本仓库**不再是** [Mihon](https://github.com/mihonapp/mihon) 的源码 fork，而是一组补丁加一条自动发布流水线：
> 每天检查 Mihon 官方最新稳定版，拉取官方源码、套用 [`patches/`](./patches) 下的补丁、编译签名 **nightly** 构建类型（官方 v0.21.0 起的叫法，之前叫 preview）的 APK，
> 发布到本仓库的 [Releases](../../releases)。tag 形如 `v0.21.0-harmony-preview.1`。
>
> 目标是改善 Mihon 在 HarmonyOS 卓易通（Android 兼容容器）中的可用性，并提供官方 release 构建里隐藏的 **Private 扩展安装器**。
> 本项目不隶属于、也不受 Mihon Open Source Project 官方支持；与本构建相关的问题请提到本仓库，不要向 Mihon 上游反馈。
> 本构建沿用上游的 [Apache-2.0](./LICENSE) 许可，原始项目与绝大部分代码归功于 [Mihon 及其贡献者](https://github.com/mihonapp/mihon/graphs/contributors)。
> 下载改名回退补丁来自 [zsyou/mihon-harmony](https://github.com/zsyou/mihon-harmony)（上游 PR [mihonapp/mihon#3446](https://github.com/mihonapp/mihon/pull/3446)）。
> 本仓库不提供、不托管任何漫画或内容源。

## 下载与安装

- 到 [Releases](../../releases) 下载最新的 `mihon-<tag>-arm64-v8a.apk`（华为设备均为 arm64）。
- 包名为 `app.mihon.debug`（nightly / 旧称 preview 构建类型自带的后缀），与官方正式版 `app.mihon` 是两个独立应用，可以共存；harmony-preview 版本之间可直接覆盖安装（含从 v0.20.4 系列升到 v0.21.0 系列）。
- **从 v0.20.4-harmony 系列升到 v0.21.0-harmony 系列前先在 App 里做一次备份**：官方 0.21 第一次启动会自动合并书架里重复的条目 / 章节，合并后不可逆；0.21 也是最后一个还能直接恢复 Tachiyomi 旧格式备份（`.tachibk`）的大版本。首次启动的向导里「内容偏好」选「保留已安装扩展」（或「混合 / 18+」），成人图源才会继续显示。0.21 对扩展库 1.4 / 1.6 都支持，已装扩展照常；官方预告再下一个大版本才会放弃 1.4。
- 安装后到 设置 → 高级 → **扩展安装器** 选「**Private**」：扩展会装进 App 自己的目录，不再受卓易通对安装第三方 APK 的限制。
- 建议开启 设置 → 下载 →「**保存为 CBZ**」。目录模式下，下载中的图片会被鸿蒙图库索引（见补丁 0003）。
- 应用内「检查更新」已改为检查本仓库的 Release，不会再提示安装官方 APK。更新流程是上游原样：更多 → 关于 → 「检查更新」→ 新版本页面点「下载」，页面留在原地显示进度，下载完点「安装」交给系统安装器。装完后留在缓存里的 `update.apk` 会在下次启动时自动删除（preview.7 起）。
- **「检查更新」报「HTTP error 403」**：不是仓库权限问题。更新检查以前直接请求 `api.github.com`，GitHub 对匿名请求的配额是**每个出口 IP 每小时 60 次**，手机走运营商 NAT 或代理时这 60 次是和同一出口的所有人共用的，用完就是 403，一小时后自动恢复（换个网络即换 IP 也行）。preview.8 起更新器优先读本仓库 `repo` 分支上由流水线生成的 Release 索引（`raw.githubusercontent.com/Xun2202/mihon-harmony/repo/releases.json`，普通 CDN，没有这个配额），读不到再退回 GitHub 接口。索引有最多约 5 分钟的 CDN 缓存，刚发版就点「检查更新」可能要等几分钟。
- APK 被交给「出境易」而提示「暂不支持安装该应用」时，把 APK 复制到本机存储后用系统「文件管理」打开即可由卓易通安装（详细步骤见 [animeko-harmony 的说明](https://github.com/Xun2202/animeko-harmony#安装步骤鸿蒙-next--6--7)，两者相同）。
- 后台下载：卓易通会在 App 切到后台几秒后冻结进程，下载队列、书架更新都会停住，直到再次打开 App。preview.5 起默认开启 设置 → 下载 →「**后台保持运行（鸿蒙）**」：下载 / 更新期间播放一段静音音轨并持有唤醒锁（补丁 0005），卓易通就不会冻结进程；不影响其他 App 的声音，不用时可关闭。
- 已知限制：Android 15+ 规定「数据同步」类前台服务在后台累计只能跑 6 小时 / 24 小时，超时会被系统强制停止，在卓易通里表现为一次闪退（`ForegroundServiceDidNotStopInTimeException`）。preview.5 起下载服务改为声明「媒体播放」类（无时限），书架更新仍是数据同步类但不再会被冻结卡住；若关闭了上面的开关，就回到官方行为，大批量下载时建议隔几小时打开一次 App（切回前台会重置额度）。
- 下载通知（preview.6 起）与 Animeko / Anikku 的鸿蒙版统一：标题「正在下载 N 个章节」，正文「下载：<速度>/s · <进度>%」+ 进度条，下拉展开显示当前的「漫画 - 章节」（开启「隐藏通知内容」时不显示）。
- **下载到 100% 后变成「!」、队列里只写「Error」**（preview.8 及之前，目录模式下）：卓易通的文件夹不支持改名，章节收尾时 `<章节>_tmp/` → `<章节>/` 的改名回退是把每一页再抄一遍，任何一步失败都没有提示。preview.9 起：目录改名优先用系统的「移动文档」（不经 App 复制），都失败才复制，残留的旧目录会被合并而不是报「已存在」，复制后核对大小并自动重试两次；下载队列里出错的章节会在章节名下面直接显示原因（哪一页为什么失败 / 目录里多了什么 / 「下载被中断」），不用再导日志。与 anikku-harmony preview.8（补丁 0016）同一份代码。
- **「检查更新」一直停在旧版本、没提示新的**（v0.21.1-harmony-preview.1 及之前）：更新器取的是 Release 列表里本频道的第一项，而 GitHub 的列表顺序不保证按版本，上游出补丁版（0.21.0 → 0.21.1）时旧系列的预览版会排在前面。v0.21.1-harmony-preview.2（补丁 0017）起按版本号比大小取最新。装着旧版的用户这一次需要手动到 [Releases](../../releases) 下载安装，之后的更新检查就正常了。
- 书架 / 浏览页显示模式新增「**全景松散网格**」（v0.21.0-harmony-preview.2，补丁 0014）和「**全景紧凑网格**」（v0.21.1-harmony-preview.2，补丁 0015）：横版封面按 3:2 画、瀑布流排布、自动列宽 168 dp；右侧快速滚动条在瀑布流里不再抽搐（补丁 0016）。
- **全景网格滑动时格子抽搐、有掉帧、滚动条还在跳一下**（v0.21.1-harmony-preview.2 及之前）：格子第一次出现时还不知道封面是横是竖，先按默认横版（3:2）排，图片解码完才改成竖版（2:3）。瀑布流里一个格子变高，会把这一列下面的全部推下去；快速滑动时每秒几十张图加载完，各触发一次整个瀑布流重新测量。横竖比例只记在内存里，重启 App 就忘了，于是每次打开都再抖一轮。横版和竖版封面还是两段不同的界面代码，一切换就把图片拆掉重新请求。滚动条用的是屏幕上看得见的格子高度，高度在滑的时候变，估算就跟着跳（补丁 0016 的滚动条算法本身没改）。v0.21.1-harmony-preview.3（补丁 0018）起：学到的高/宽写进 App 自己的文件，下次启动直接用；正在滑动时不把新学到的形状写进排版（已经能确定是横还是竖的，马上用）；横版和竖版走同一个封面组件，不再拆掉重建。从没见过的封面仍会在你手指停下的那一下改一次形状，改完就记住了。滑动还掉不掉帧，要在真机上滑一下确认。
- **拖快速滚动条、两下甩动之间全景格子还会跳一下，浏览页新格子第一次出现也会改形状**（v0.21.1-harmony-preview.3）：上一版把「网格算不算停下来」写成「手指没在滑」。拖右侧快速滚动条时，程序是一连串很短的跳动，两下之间它以为已经停下，刚学到的横竖就写进排版；连续甩两下、中间停一下，也一样。浏览某一图源时，封面要等格子出现在屏幕上才去学横竖，下一页还没滑到就仍是默认横版。v0.21.1-harmony-preview.4（补丁 0019）起：要连续 300 毫秒没有任何滚动，才把新形状写进排版；浏览页对已经加载、还没出现在屏幕上的封面提前要一张 128 像素的小图（不放进内存缓存），记下高/宽，图片进磁盘缓存，等格子出现时直接用。刚打开浏览页、你还没滑的第一屏，仍可能改一次形状；某张封面下载失败就一直是默认横版。多出来的流量，是把你滑下去本来就会下载的下一页封面提前一点下。拖滚动条和滑动还抖不抖，要在真机上确认。

## 包含的补丁

| 补丁 | 作用 |
| --- | --- |
| [`0001-downloads-rename-fallback-for-saf-without-renamedocument.patch`](./patches/0001-downloads-rename-fallback-for-saf-without-renamedocument.patch) | 卓易通的文件提供方不支持 SAF `renameDocument`，下载的图片会停在 `.tmp`、章节下载失败。新增 `UniFile.renameToOrCopy()`：改名失败时回退为「复制到目标后删除源」。正常支持改名的设备仍走原流程。 |
| [`0002-updater-use-harmony-fork-releases.patch`](./patches/0002-updater-use-harmony-fork-releases.patch) | 应用内更新改查本仓库的 GitHub Releases：nightly（旧称 preview）构建只认 tag 含 `-harmony-preview.` 的，版本号按 `(x, y, z, N)` 四元组比较。否则官方更新逻辑会推送官方 APK（签名不同无法安装）或因解析不了 `0.21.0-harmony.1` 而崩溃。 |
| [`0003-downloads-cbz-temp-in-private-cache.patch`](./patches/0003-downloads-cbz-temp-in-private-cache.patch) | 鸿蒙图库会索引卓易通共享存储里的所有图片且不认 `.nomedia`。CBZ 模式下把下载临时目录移到 App 私有缓存，只有最终 `.cbz` 写入用户选择的目录；并增加 `finalizeArchive()`，清理上次失败残留的 `.cbz`，避免下载队列卡死。 |
| ~~`0004-database-busy-timeout-and-room-like-connection-setup.patch`~~ | **已随 v0.21.0 删除**：它回移的上游提交 [mihonapp/mihon@38e93086c8](https://github.com/mihonapp/mihon/commit/38e93086c8)（`PRAGMA busy_timeout = 3000` + WAL，修启动闪退 `database is locked`）已包含在官方 v0.21.0 里（`DatabaseBindings.kt`）。编号保留不复用。 |
| [`0005-downloads-background-keep-alive-silent-audio.patch`](./patches/0005-downloads-background-keep-alive-silent-audio.patch) | 卓易通在 App 退到后台几秒后就冻结进程，dataSync 前台服务、唤醒锁、电池优化白名单都拦不住（Animeko 上验证过，只有音频输出能让容器继续跑）。下载停住不说，空转的前台服务还会把 Android 15 的 6 小时 dataSync 额度耗光，最后以 `ForegroundServiceDidNotStopInTimeException` 闪退。新增 `BackgroundKeepAlive`：下载队列 / 书架更新运行期间循环播放一段静音 PCM（`AudioTrack` MODE_STATIC，不占 CPU，不抢音频焦点）并持有部分唤醒锁；下载服务改为声明 `mediaPlayback` 类型（无 6 小时限制）。设置 → 下载 →「后台保持运行（鸿蒙）」可关闭。 |
| [`0006-downloads-notification-speed-and-progress.patch`](./patches/0006-downloads-notification-speed-and-progress.patch) | 三个鸿蒙版应用的下载通知统一成 Animeko 的样式：标题「正在下载 N 个章节」（排队 + 进行中），正文「下载：<速度>/s · <进度>%」，确定型进度条，展开后第二行显示当前「漫画 - 章节」（「隐藏通知内容」开启时省略）。新增 `DownloadSpeedMeter`（近 3 秒滑动平均，包装每页响应流计数；与 anikku-harmony 0010 同一份文件），下载器每秒刷新一次通知。v0.21.0 起限流用上游自带的（500 ms、加锁、每章最后一页必发），不再自带 700 ms 限流；暂停通知沿用上游的独立通知。 |
| [`0007-updater-delete-installed-apk.patch`](./patches/0007-updater-delete-installed-apk.patch) | 应用内更新下载到 `Android/data/<包名>/cache/update.apk` 的安装包此前没人删（v0.21.0 也只在下载失败时删），一直留到下次更新被覆盖。`App.onCreate` 里调用新增的 `AppUpdateApkCleaner.deleteInstalledApk()`（v0.20.4 系列时放在 `AppUpdateDownloadJob` 里，0.21 删掉了那个类）：用 `getPackageArchiveInfo` 读出它的 versionCode，不高于当前版本（或文件读不出来）就删除；`NewUpdateScreenModel` 的下载路径改为共用同一处定义。与 anikku-harmony 0011 的清理逻辑逐字相同；Animeko 则在 harmony.8 里让 Android 端也调用上游已有的 `deleteInstalledFiles()`。 |
| [`0008-updater-release-mirror.patch`](./patches/0008-updater-release-mirror.patch) | 修复「检查更新」报「HTTP error 403」：匿名 `api.github.com` 每个出口 IP 每小时只有 60 次，NAT / 代理后面是所有人共用。`ReleaseServiceImpl.listReleases()` 优先读 `https://raw.githubusercontent.com/<repo>/repo/releases.json`（流水线写的接口原样镜像，连接 / 读取 / 整体超时各 10 秒），失败再退回 `api.github.com/repos/<repo>/releases?per_page=30`；`latest()` 其余逻辑（按 tag 后缀挑频道、按 ABI 挑 APK）不变。与 anikku-harmony 0014、animeko-harmony 0009 同一轮。 |

| ~~`0009-build-flexible-adapter-from-maven-central.patch`~~ | **已随 v0.21.0 删除**：官方 v0.21.0 已把 FlexibleAdapter 切到 Maven Central 的 `eu.davidea:flexible-adapter:5.1.0`（JitPack 坐标早已 404）。编号保留不复用。 |
| [`0010-downloads-finalize-with-fewer-saf-copies-and-error-reasons.patch`](./patches/0010-downloads-finalize-with-fewer-saf-copies-and-error-reasons.patch) | 移植 anikku-harmony 0016：`renameToOrCopy(targetName, resolver)` 目录改名先逐项 `DocumentsContract.moveDocument`（provider 侧移动，不经 App 复制），不行再复制，目标目录已存在（上次中断的残留）则合并、同大小文件跳过，复制后核对大小，源删不掉也不丢数据（`UniFileExtensions.kt` 与 Anikku 逐字节相同，单元测试 8 个）；章节目录收尾改名重试 3 次；`Download.error` + `fail()`，下载不完整时记录「N 页下载失败，例如第 X 页：<原因>」或目录内容列表，`stop()` 记「下载被中断」；下载队列行在章节名下显示「出错：<原因>」，右侧状态「Error」。每页 `.tmp` → `.jpg` 的改名不变（扩展名要等响应才知道，而且图片小）。 |
| [`0011-downloads-never-skip-silently-reuse-or-replace-leftover-folders.patch`](./patches/0011-downloads-never-skip-silently-reuse-or-replace-leftover-folders.patch) | 点「下载」没反应的修复。原来 `Downloader.queueChapters` 发现磁盘上已有同名章节目录 / `.cbz` 就直接丢掉、不进队列也不提示；卓易通里收尾阶段被冻结 / 杀进程会留下这种目录，而章节列表读的是下载缓存（最多一小时刷新一次），于是界面显示「未下载」、点了却什么都不发生。现在：①「已下载」改按下载缓存判断（与列表一致），并返回 `QueueResult`（入队 / 已下载 / 已在队列 / 图源未安装 各多少，外加 `startDownloader` 告诉 `DownloadManager` 要不要起 `DownloadWorker`——0.21 把启动 Worker 挪到了调用方）；②`downloadChapter` 拿到页列表后先看磁盘：目录或 `.cbz` 里的页数 ≥ 页列表则直接登记为已下载（不重下，顺手清掉 `_tmp` 残留），不够则删掉残留从头下——这一步**替代**了 0.21 新加的「磁盘上有目录就直接登记为已下载」（上游不查完整性，半截目录会被当成已下载）；③漫画页面在有章节没入队时弹 Snackbar「未加入下载队列：N 章已下载 · N 章已在队列中 · N 章的图源未安装」（0.21 的入队在 `appScope` 里并被 `join()`，所以 Snackbar 改在 `viewModelScope` 里弹，不阻塞「加入书架」提示）。与 anikku-harmony 0018 同源。 |
| [`0012-crash-log-filter-harmony-noise-and-keep-app-log.patch`](./patches/0012-crash-log-filter-harmony-noise-and-keep-app-log.patch) | 崩溃日志去噪。卓易通会往应用自己的 logcat 里每分钟写几百条图形层错误（`BLASTBufferQueue` `Faking releaseBufferCallback`、`SurfaceDelegator client is nullptr`、`HwViewRootImpl`、`HwAssetManagerEx`、`Display : result is null`），几分钟就把缓冲区挤满，导出的日志里几乎看不到 Mihon 自己的任何一行。现在 `CrashLogUtil` 改为读 logcat 管道、按已知特征过滤并在小节标题写明过滤了多少条；新增 `HarmonyLogBuffer`（`LogcatLogger` 实现，内存里保留应用自己最近 600 行 `logcat {}` 输出，DEBUG 及以上、带时间戳），导出时作为「App log」小节附在末尾。与 anikku-harmony 0019 同一份文件。 |
| [`0013-downloads-retried-failed-chapters-are-not-skipped.patch`](./patches/0013-downloads-retried-failed-chapters-are-not-skipped.patch) | 0011 的补充：点一个下载失败（「!」）的章节重试时走的是同一条入队路径，0011 把它算成「已在队列中」、每次重试都弹一次提示。现在队列里处于 ERROR 状态的章节记为 `retried`、不算跳过（真正的重启由调用方 `startDownloads()` 完成，行为不变）。anikku-harmony 0018 已把这一点合在里面。 |
| [`0014-library-panorama-comfortable-grid-display-mode.patch`](./patches/0014-library-panorama-comfortable-grid-display-mode.patch) | 新增显示模式「全景松散网格」（书架的显示设置和浏览页的显示模式菜单里各多一项）。封面高宽比 ≤ 0.75 的横版封面按 3:2 的格子画、竖版仍按 2:3；格子用瀑布流（`LazyVerticalStaggeredGrid`）排，横竖混排时不留空；每行数量「自动」时列宽下限 168 dp（手机两列、约 530 dp 起三列），手动固定列数不变；封面横竖比按作品缓存到进程生命周期，滚回视野时不跳形状。从 anikku-harmony 0015 + 0020 移植（Anikku 的「全景封面」功能精简成一个显示模式）。Harmony 独有：上游 Mihon 没有这个功能，Animeko 没有这种网格。 |
| [`0015-library-panorama-compact-grid-display-mode.patch`](./patches/0015-library-panorama-compact-grid-display-mode.patch) | 新增显示模式「全景紧凑网格」：标题压在封面上的紧凑网格，套用 0014 同一套全景规则（横版封面 3:2、瀑布流、自动列宽 168 dp、封面横竖比按作品缓存）。序列化 `COMPACT_GRID_PANORAMA`，排在紧凑网格之后；浏览页显示模式菜单同步多一项。与 anikku-harmony 0022 同源。 |
| [`0016-presentation-staggered-fast-scroller-steady-thumb.patch`](./patches/0016-presentation-staggered-fast-scroller-steady-thumb.patch) | 修复全景网格上下滑动时右侧快速滚动条「抽搐」：0014 的瀑布流滚动条用当前屏上条目的平均高度估算位置，3:2 与 2:3 格子换进换出时平均值跟着变、拇指来回跳。现在按条目索引记住量过的高度（没见过的用累计平均），满行条目（搜索栏等，按比单格宽判断）不计入，列数取见过的最大值；`offset.y` 相对内容起点，顶部 padding 只算进总长度。与 anikku-harmony 0023 的估算段逐字相同。 |
| [`0017-updater-pick-highest-harmony-version.patch`](./patches/0017-updater-pick-highest-harmony-version.patch) | 修复「检查更新」拉不到最新版：`ReleaseServiceImpl.latest()` 原来取本频道列表里的**第一项**，GitHub 的列表顺序并不保证按版本（镜像 `releases.json` 里 `v0.21.0-harmony-preview.2` 排在 `v0.21.1-harmony-preview.1` 前面），于是 App 一直提示旧版本。现在把本频道候选按 `(主, 次, 补丁, harmony 号)` 四元组比较取最大，解析不了的 tag 排最后。anikku-harmony 0024 同病同修；animeko-harmony 0002 本来就是排序取最大，不适用。 |
| [`0018-library-panorama-stable-cell-shapes.patch`](./patches/0018-library-panorama-stable-cell-shapes.patch) | 修复全景网格滑动时资源块排版抽搐、掉帧，以及滚动条的残余抽搐（0016 的滚动条代码没动，跳的是格子高度）。新文件 `PanoramaCoverShapes.kt`：学到的封面高/宽记在 `filesDir/harmony_panorama_cover_shapes.txt`（每行 `id ratio`，重启还在）；正在滑动时不把新形状写进瀑布流布局（横竖已经同侧则立即写）；封面横竖改成同一个 Compose 调用点，不再拆掉重建 `AsyncImage`。书架两种全景模式会在后台读封面缓存的宽高（不解码整张图）。与 anikku-harmony 0025 的 `PanoramaCoverShapes.kt` 逐字节相同。不改数据库、不加设置项。从没见过的封面仍会在滑动停下时改一次形状。Animeko 没有这套网格，不适用。 |
| [`0019-library-panorama-settle-debounce-browse-prefetch.patch`](./patches/0019-library-panorama-settle-debounce-browse-prefetch.patch) | 0018 之后还剩两处：拖快速滚动条时 `isScrollInProgress` 在两次 `scrollToItem` 之间为假，学到的形状中途写进布局；浏览页要等格子上屏才学形状。`rememberPanoramaGridSettled` 改为连续 300 ms 没有滚动才算静止（书架瀑布流、浏览页舒适 / 紧凑全景网格）。浏览页 `PrefetchPanoramaCoverShapes` 对已加载未上屏的条目按 128 px、`Precision.INEXACT`、关掉内存缓存去要封面并记下高/宽（下载进磁盘缓存，格子后来读同一份；离开网格就取消）。`PanoramaCoverShapes.kt` 与 anikku-harmony 0027 逐字节相同。已知局限：刚打开的浏览页第一屏在静止时仍可能翻一次；下载失败的封面保持默认横版。Animeko 没有这套网格，不适用。 |

补丁按 [`patches/series`](./patches/series) 的顺序套用。

## 版本号规则

- `versionName` = `<官方版本>-harmony.<N>`，例如 `0.21.0-harmony.1`；nightly（旧称 preview）构建类型会再自动追加 `-<上游提交数>` 后缀，这是 Mihon 自己的行为。
- `versionCode` = `<官方 versionCode> × 100 + N`（如 `36 × 100 + 1 = 3601`；v0.20.4 系列是 `29 × 100 + N`），保证新官方版本的任意 harmony 构建都高于旧版本的，覆盖安装不会被拒。
- Release tag = `<官方 tag>-harmony-preview.<N>`。`N` 是同一官方版本的第几次打包，改了补丁需要重发时递增。**不要改这个格式**，更新器靠它识别渠道。

## 构建机制

流水线定义在 [`.github/workflows/harmony_preview.yml`](./.github/workflows/harmony_preview.yml)，每天 UTC 04:17（北京 12:17）定时运行，也可以在 Actions 里手动触发并指定 `upstream_tag` / `patch_number`，或勾选 `dry_run` 只编译不发布：

1. 取官方最新稳定版 tag（或手动指定），若对应 Release 已存在则直接结束。
2. `git clone --branch <tag> --single-branch` 官方源码（保留完整历史，nightly 构建用提交数做版本后缀）。
3. [`scripts/prepare-source.sh`](./scripts/prepare-source.sh)：按 `series` 顺序 `git apply --3way` 补丁、改写 `versionCode` / `versionName`，每一步各提交一次。
4. 按官方 `.github/.java-version` 装 JDK；源码树里有 `create("nightly")` 就 `./gradlew assembleNightly -Penable-updater`（v0.21.0 起），否则 `assemblePreview`（v0.20.4 及更早）。签名密钥来自仓库 Secrets：`SIGNING_KEY` 先 base64 解码成 `$RUNNER_TEMP/harmony.keystore`，`MIHON_GITHUB_RELEASE=true` 时 `app/build.gradle.kts` 读取 `storeFile`（v0.21.0 起是文件路径；更早的版本读 `storeFileBase64`，两个都给）等环境变量。
5. 产物重命名为 `mihon-<tag>-{arm64-v8a,universal}.apk`，上传为 Actions artifact 并 `gh release create`，Release 说明里附 SHA-256。
6. [`scripts/write-release-index.sh`](./scripts/write-release-index.sh) 把 `GET /repos/<repo>/releases?per_page=30` 的返回原样写到孤儿分支 **`repo`** 的 `releases.json`（另附 `latest.json`），应用内更新器（0008 起）优先从 `raw.githubusercontent.com/Xun2202/mihon-harmony/repo/releases.json` 读它。`GITHUB_TOKEN` 创建的 Release 不会触发别的 workflow，所以发版流程自己调用这个脚本；手动增删改 Release 时由 [`.github/workflows/release_index.yml`](./.github/workflows/release_index.yml)（`release` 事件，也可手动触发）重新生成。`repo` 分支只放这三个自动生成的文件，不要手改。

[`.github/workflows/check_patches.yml`](./.github/workflows/check_patches.yml) 在补丁改动时和每周一，把补丁分别试套到官方最新稳定版和 `main`，上游一变就能提前知道要 rebase。

## Secrets

| 名称 | 内容 |
| --- | --- |
| `SIGNING_KEY` | 签名密钥库（`.jks`）的 Base64 |
| `KEY_STORE_PASSWORD` | 密钥库密码 |
| `ALIAS` | 密钥别名（`mihon-harmony`） |
| `KEY_PASSWORD` | 密钥密码 |

**丢失密钥 = 已安装用户无法覆盖升级**，只能卸载重装。密钥备份位置与维护流程见 [`docs/MAINTENANCE.md`](./docs/MAINTENANCE.md)。

## 维护

补丁套不上、编译失败、如何改补丁、如何验证：见 [`docs/MAINTENANCE.md`](./docs/MAINTENANCE.md)。
