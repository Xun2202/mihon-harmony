> [!IMPORTANT]
> ## Mihon Harmony Preview（非官方 HarmonyOS / 卓易通 兼容构建）
>
> 本仓库**不再是** [Mihon](https://github.com/mihonapp/mihon) 的源码 fork，而是一组补丁加一条自动发布流水线：
> 每天检查 Mihon 官方最新稳定版，拉取官方源码、套用 [`patches/`](./patches) 下的补丁、编译签名 **preview** 构建类型的 APK，
> 发布到本仓库的 [Releases](../../releases)。tag 形如 `v0.20.4-harmony-preview.1`。
>
> 目标是改善 Mihon 在 HarmonyOS 卓易通（Android 兼容容器）中的可用性，并提供官方 release 构建里隐藏的 **Private 扩展安装器**。
> 本项目不隶属于、也不受 Mihon Open Source Project 官方支持；与本构建相关的问题请提到本仓库，不要向 Mihon 上游反馈。
> 本构建沿用上游的 [Apache-2.0](./LICENSE) 许可，原始项目与绝大部分代码归功于 [Mihon 及其贡献者](https://github.com/mihonapp/mihon/graphs/contributors)。
> 下载改名回退补丁来自 [zsyou/mihon-harmony](https://github.com/zsyou/mihon-harmony)（上游 PR [mihonapp/mihon#3446](https://github.com/mihonapp/mihon/pull/3446)）。
> 本仓库不提供、不托管任何漫画或内容源。

## 下载与安装

- 到 [Releases](../../releases) 下载最新的 `mihon-<tag>-arm64-v8a.apk`（华为设备均为 arm64）。
- 包名为 `app.mihon.debug`（preview 构建类型自带的后缀），与官方正式版 `app.mihon` 是两个独立应用，可以共存；harmony-preview 版本之间可直接覆盖安装。
- 安装后到 设置 → 高级 → **扩展安装器** 选「**Private**」：扩展会装进 App 自己的目录，不再受卓易通对安装第三方 APK 的限制。
- 建议开启 设置 → 下载 →「**保存为 CBZ**」。目录模式下，下载中的图片会被鸿蒙图库索引（见补丁 0003）。
- 应用内「检查更新」已改为检查本仓库的 Release，不会再提示安装官方 APK。
- APK 被交给「出境易」而提示「暂不支持安装该应用」时，把 APK 复制到本机存储后用系统「文件管理」打开即可由卓易通安装（详细步骤见 [animeko-harmony 的说明](https://github.com/Xun2202/animeko-harmony#安装步骤鸿蒙-next--6--7)，两者相同）。
- 已知限制：Android 15+ 规定「数据同步」类前台服务在后台累计只能跑 6 小时 / 24 小时。下载队列或书架更新在后台连续跑满 6 小时后会被系统强制停止，在卓易通里可能表现为一次闪退（`ForegroundServiceDidNotStopInTimeException`），重新打开即可，下载会从断点继续。把 Mihon 切回前台会重置这 6 小时额度，大批量下载时建议隔几小时打开一次 App。

## 包含的补丁

| 补丁 | 作用 |
| --- | --- |
| [`0001-downloads-rename-fallback-for-saf-without-renamedocument.patch`](./patches/0001-downloads-rename-fallback-for-saf-without-renamedocument.patch) | 卓易通的文件提供方不支持 SAF `renameDocument`，下载的图片会停在 `.tmp`、章节下载失败。新增 `UniFile.renameToOrCopy()`：改名失败时回退为「复制到目标后删除源」。正常支持改名的设备仍走原流程。 |
| [`0002-updater-use-harmony-fork-releases.patch`](./patches/0002-updater-use-harmony-fork-releases.patch) | 应用内更新改查本仓库的 GitHub Releases：preview 构建只认 tag 含 `-harmony-preview.` 的，版本号按 `(x, y, z, N)` 四元组比较。否则官方更新逻辑会推送官方 APK（签名不同无法安装）或因解析不了 `0.20.4-harmony.1` 而崩溃。 |
| [`0003-downloads-cbz-temp-in-private-cache.patch`](./patches/0003-downloads-cbz-temp-in-private-cache.patch) | 鸿蒙图库会索引卓易通共享存储里的所有图片且不认 `.nomedia`。CBZ 模式下把下载临时目录移到 App 私有缓存，只有最终 `.cbz` 写入用户选择的目录；并增加 `finalizeArchive()`，清理上次失败残留的 `.cbz`，避免下载队列卡死。 |
| [`0004-database-busy-timeout-and-room-like-connection-setup.patch`](./patches/0004-database-busy-timeout-and-room-like-connection-setup.patch) | 修复启动时闪退 `SQLException: Error code: 5, message: database is locked`。官方 v0.20.4 打开数据库没有设置 busy timeout，崩溃页面所在的 `:error_handler` 进程与主进程同时开着数据库、或上次被系统杀掉后要恢复 WAL 时，写入一遇到锁就直接崩。回移上游 [mihonapp/mihon@38e93086c8](https://github.com/mihonapp/mihon/commit/38e93086c8)：每条连接 `PRAGMA busy_timeout = 3000`，显式 WAL（低内存设备用 TRUNCATE），1 写 + 4 读连接池。 |

补丁按 [`patches/series`](./patches/series) 的顺序套用。

## 版本号规则

- `versionName` = `<官方版本>-harmony.<N>`，例如 `0.20.4-harmony.3`；preview 构建类型会再自动追加 `-<上游提交数>` 后缀，这是 Mihon 自己的行为。
- `versionCode` = `<官方 versionCode> × 100 + N`（如 `29 × 100 + 3 = 2903`），保证新官方版本的任意 harmony 构建都高于旧版本的，覆盖安装不会被拒。
- Release tag = `<官方 tag>-harmony-preview.<N>`。`N` 是同一官方版本的第几次打包，改了补丁需要重发时递增。**不要改这个格式**，更新器靠它识别渠道。

## 构建机制

流水线定义在 [`.github/workflows/harmony_preview.yml`](./.github/workflows/harmony_preview.yml)，每天 UTC 04:17（北京 12:17）定时运行，也可以在 Actions 里手动触发并指定 `upstream_tag` / `patch_number`，或勾选 `dry_run` 只编译不发布：

1. 取官方最新稳定版 tag（或手动指定），若对应 Release 已存在则直接结束。
2. `git clone --branch <tag> --single-branch` 官方源码（保留完整历史，preview 构建用提交数做版本后缀）。
3. [`scripts/prepare-source.sh`](./scripts/prepare-source.sh)：按 `series` 顺序 `git apply --3way` 补丁、改写 `versionCode` / `versionName`，每一步各提交一次。
4. 按官方 `.github/.java-version` 装 JDK，`./gradlew assemblePreview -Penable-updater`，签名密钥来自仓库 Secrets（`MIHON_GITHUB_RELEASE=true` 时 `app/build.gradle.kts` 读取 `storeFileBase64` 等环境变量）。
5. 产物重命名为 `mihon-<tag>-{arm64-v8a,universal}.apk`，上传为 Actions artifact 并 `gh release create`，Release 说明里附 SHA-256。

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
