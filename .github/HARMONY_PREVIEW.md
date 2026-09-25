# Mihon Harmony Preview —— 维护手册

> 本文档面向后续接手维护的人或 AI 助手。读完本文并拿到一个有 `repo` + `workflow` 权限的
> GitHub token，就应能完整理解现状并继续维护本仓库的全部功能。
>
> 仓库：`https://github.com/Xun2202/mihon-harmony`（fork 自 `zsyou/mihon-harmony`）
> 维护者 GitHub 账号：`Xun2202`

---

## 1. 背景与目标

- [Mihon](https://github.com/mihonapp/mihon) 是安卓漫画阅读器。用户在华为 HarmonyOS NEXT 设备上通过
  **卓易通**（安卓兼容层）运行它。
- [zsyou/mihon-harmony](https://github.com/zsyou/mihon-harmony) 是作者 zsyou 的非官方分支，修复了卓易通下
  章节下载失败的问题（SAF 文件提供方不支持 `renameDocument`，改名失败时回退为"复制 + 删除"）。
  作者向官方提的 PR 为 [mihonapp/mihon#3446](https://github.com/mihonapp/mihon/pull/3446)，截至 2026-09 仍未合并。
- 用户想使用 Mihon 的 **Private（私有）扩展安装器**（把扩展装进 App 自己的目录，绕开卓易通对安装第三方 APK
  的限制）。但 Mihon 上游代码在 `release` 构建类型里隐藏了该选项，只有 `preview` 构建类型才显示：

  ```kotlin
  // app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsAdvancedScreen.kt
  .filter {
      // TODO: allow private option in stable versions once URL handling is more fleshed out
      if (isReleaseBuildType) it != BasePreferences.ExtensionInstaller.PRIVATE else true
  }
  ```

- 作者只发布 `release` 构建，官方 Mihon Beta 又没有下载修复。因此本 fork 的目标是：
  **基于作者的补丁，编译 `preview` 构建类型，并让 App 能从本仓库自动检查更新。**

## 2. 现状总览

| 项目 | 内容 |
| --- | --- |
| 产物 | 每个官方稳定版对应一个 Release，tag 形如 `v0.20.4-harmony-preview.N` |
| 包名 | `app.mihon.debug`（preview 构建类型自带后缀，可与作者的 `app.mihon` 正式版并存） |
| 推荐安装文件 | `mihon-<tag>-arm64-v8a.apk`（华为设备均为 arm64） |
| 构建方式 | GitHub Actions，workflow 文件 `.github/workflows/harmony_preview.yml` |
| 触发 | 每天 UTC 04:17（北京 12:17）定时 + 手动 `workflow_dispatch` |
| 签名 | 自建密钥，存放于仓库 Secrets；本地备份见 §6 |
| 应用内更新 | 已启用，指向本仓库 Release（见 §4） |
| 作者的其它 workflow | `build.yml`、`harmony_release.yml`、`release.yml`、`update_website.yml` 已在本 fork 中禁用 |

已发布版本（截至 2026-09-26）：

- `v0.20.4-harmony-preview.1` —— 首个 preview 构建，**没有**应用内更新器。
- `v0.20.4-harmony-preview.2` —— 加入应用内更新器。用户应安装此版本及之后的版本。

## 3. 构建流程（`harmony_preview.yml` 做了什么）

本仓库 `main` 分支上的源码**不是**被编译的对象，它只是作者 fork 时的旧快照（0.19.9）。
真正编译的源码是在 Actions 运行时动态拼出来的，步骤与作者的 `harmony_release.yml` 一致，只是构建类型不同：

1. **解析版本**：输入 `upstream_tag`（为空则调用 GitHub API 取 `mihonapp/mihon` 最新稳定版 tag）和
   `patch_number`（默认 `1`）。生成 `release_tag = <upstream_tag>-harmony-preview.<patch_number>`。
2. **跳过已存在的 Release**：若同名 Release 已存在则直接结束（这是定时任务不重复编译的关键）。
3. **准备源码**：
   - 把 `.github/patches/harmony.patch`（作者的下载修复）和 `.github/patches/harmony-preview/`
     （本 fork 的更新器补丁）复制到临时目录；
   - `git fetch` 官方仓库的 `upstream_tag` 并 checkout；
   - `git apply --3way` 作者的 patch，再用内嵌 Python 脚本改 `Downloader.kt`（这段脚本原样复制自作者的 workflow）；
   - 改 `app/build.gradle.kts`：`versionCode = 官方versionCode * 100 + patch_number`，
     `versionName = "<官方版本>-harmony.<patch_number>"`；
   - 把 `harmony-preview/` 目录下的文件整体覆盖到源码树（见 §4）。
4. **编译**：`./gradlew assemblePreview -Penable-updater`
   - `assemblePreview`：preview 构建类型 → Private 安装器可见，包名 `app.mihon.debug`，
     `versionName` 自动追加 `-<commitCount>` 后缀。
   - `-Penable-updater`：把 `BuildConfig.UPDATER_ENABLED` 置为 true，否则 App 根本不检查更新。
   - 签名：`app/build.gradle.kts` 里当环境变量 `MIHON_GITHUB_RELEASE=true` 时，从
     `storeFileBase64 / storePassword / keyAlias / keyPassword` 四个环境变量读取密钥（由 Secrets 注入）。
5. **发布**：APK 重命名为 `mihon-<release_tag>-{arm64-v8a,universal}.apk`，同时上传为 Actions artifact，
   并 `gh release create <release_tag> --target $GITHUB_SHA`。
   - 注意：**不推送 tag 到源码**。默认 `GITHUB_TOKEN` 无权推送包含 workflow 文件改动的提交，
     第一次尝试因此失败，所以改成让 `gh release create` 在 `main` 当前提交上直接建 tag。

## 4. 应用内更新机制

Mihon 原生更新逻辑：启动时请求 `https://api.github.com/repos/<repo>/releases/latest`，比较版本号，
有新版本则弹通知并下载 APK。原实现写死 `mihonapp/mihon`，且版本比较只认 `v0.1.2` / `r1234` 两种格式，
遇到 `0.20.4-harmony.1` 会抛异常。

`.github/patches/harmony-preview/` 下三个文件在编译前整体覆盖对应源码文件：

| 文件 | 改动 |
| --- | --- |
| `app/.../data/updater/AppUpdateChecker.kt` | `GITHUB_REPO` 固定为 `Xun2202/mihon-harmony`；`RELEASE_TAG` 由 `VERSION_NAME` 解析生成 `v<ver>-harmony-preview.<N>`，供"关于"页链接使用 |
| `data/.../release/ReleaseServiceImpl.kt` | 改为请求 `/releases?per_page=30` 列表，preview 构建只挑 tag 含 `-harmony-preview.` 的，release 构建只挑含 `-harmony.` 且不含 preview 的；其余逻辑（按 ABI 选 APK）不变 |
| `domain/.../release/interactor/GetApplicationRelease.kt` | 版本比较改为解析 `(\d+)\.(\d+)\.(\d+)-harmony(?:-preview)?\.(\d+)` 得到四元组逐位比较；解析失败才退回上游逻辑（并把 `toInt()` 改为 `toIntOrNull()` 防崩） |

这三个文件是**整文件覆盖**，基于 Mihon v0.20.4 的版本编写。若官方大改这几个文件导致编译失败，
需要拉取新版官方文件重新套用上述改动。

APK 文件名必须保留 `-arm64-v8a` / `-universal` 片段，`ReleaseServiceImpl.getDownloadLink` 靠它匹配设备 ABI。

## 4a. 卓易通 / 鸿蒙图库适配（`harmony-preview-scripts/downloader.py`）

在作者补丁和更新器覆盖之后，workflow 还会运行 `.github/patches/harmony-preview-scripts/downloader.py`，
用与作者相同的 `replace_once` 方式改 `Downloader.kt`（找不到锚点会直接失败，便于发现上游变动）：

| 问题 | 处理 |
| --- | --- |
| 鸿蒙图库会索引卓易通共享存储（"兼容应用数据"）下的所有图片，且**不认 `.nomedia`**。下载中的 `章节名_tmp` 目录里有裸露的 jpg，会在图库里短暂出现 | CBZ 模式下把临时目录改到 App 私有缓存 `context.cacheDir/harmony_download_tmp/<mangaId>/<章节>_tmp`，只有最终的 `.cbz` 写入用户选择的下载目录。**目录模式（不打包 CBZ）无法规避**，只能在图库里隐藏相册 |
| 某次失败留下 `章节.cbz` 残留后，作者的 `renameToOrCopy` 因"目标已存在"永远失败，下载卡死 | 新增 `finalizeArchive()`：先删残留目标；改名失败就复制；复制后删不掉 `.cbz_tmp` 只记 WARN 不报错 |

用户实测：目录模式下作者补丁工作正常；CBZ 模式需要上述容错。

## 5. 日常操作

### 5.1 手动出新版

Actions → **Harmony Preview** → Run workflow：

- `upstream_tag`：官方 tag，如 `v0.20.5`；留空取最新稳定版。
- `patch_number`：同一官方版本的第几次构建，从 `1` 开始；改了补丁想重编就填 `2`、`3`……

约 7–10 分钟完成。同名 Release 已存在会直接跳过，需要重编时必须换补丁号或先删掉旧 Release。

### 5.2 定时任务

每天自动跑一次，只会为"尚未发布过 `-harmony-preview.1`"的官方新版本构建。
GitHub 会在仓库 60 天无提交时自动暂停定时任务，届时到 Actions 页面点 Enable 即可。

### 5.3 用命令行操作（给 AI 助手）

```powershell
# 环境：Windows，已安装 git、gh、OpenJDK 17（均通过 winget）
$env:GH_TOKEN = '<用户提供的 token>'
gh auth status
gh workflow run harmony_preview.yml --repo Xun2202/mihon-harmony -f upstream_tag=v0.20.5 -f patch_number=1
gh run list --repo Xun2202/mihon-harmony --workflow harmony_preview.yml --limit 3
gh run watch <run_id> --repo Xun2202/mihon-harmony --exit-status
gh run view <run_id> --repo Xun2202/mihon-harmony --log-failed
gh release list --repo Xun2202/mihon-harmony

# 推送改动（在本地克隆目录内执行，目录位置见维护者本机的私有备忘）
git push "https://x-access-token:$env:GH_TOKEN@github.com/Xun2202/mihon-harmony.git" HEAD:main
```

注意：从国内网络用 `gh run download` 拉 artifact 可能长时间卡住，直接让用户从 Release 页下载即可。

## 6. 签名密钥

- Secrets（仓库 Settings → Secrets and variables → Actions）：
  `SIGNING_KEY`（jks 的 Base64）、`KEY_STORE_PASSWORD`、`ALIAS`（值为 `mihon-harmony`）、`KEY_PASSWORD`。
- 本地备份：保存在维护者电脑上（不在本仓库内），含 `mihon-harmony.jks` 与记录密码的文本文件。
  具体位置写在维护者本机的私有备忘里，不要写进本仓库。
- 密钥 RSA 4096，有效期 10000 天，2026-09-25 生成。
- **丢失密钥 = 已安装用户无法覆盖升级**，只能卸载重装。若需换密钥，重新生成并更新四个 Secrets，
  同时提醒用户先在 App 内备份数据。

## 7. 已知问题与排错

| 现象 | 原因 / 处理 |
| --- | --- |
| "Prepare official source" 步骤失败：`git apply` 冲突或 Python 脚本报 `Missing Downloader.kt patch pattern` | 官方新版改动了被补丁触及的代码。先看作者仓库是否已更新 `harmony.patch`（可直接同步他的 `.github/patches/`），否则手动重做补丁 |
| 编译报错，位置在 `AppUpdateChecker.kt` / `ReleaseServiceImpl.kt` / `GetApplicationRelease.kt` | 官方改了这些文件的接口。取官方新版文件，重新套用 §4 的改动 |
| `downloader.py` 报 `Missing Downloader.kt pattern (harmony-preview)` | 官方改了 `Downloader.kt` 里被我们替换的代码段，按 §4a 的意图更新脚本里的锚点字符串 |
| 图库里仍能看到漫画图片 | 确认 App 设置里"保存为 CBZ 格式"已开启；目录模式无法规避，去图库隐藏该相册。历史遗留的 `_tmp` 目录可手动删除 |
| Release 步骤失败 `refusing to allow a GitHub App to create or update workflow` | 有人把推 tag 的逻辑加回来了。保持用 `gh release create --target $GITHUB_SHA`，不要 `git push` tag |
| 定时任务不跑 | 仓库 60 天无提交被 GitHub 暂停，手动 Enable |
| App 内检查不到更新 | 确认 Release 不是 draft、tag 含 `-harmony-preview.`、资产文件名含 `-arm64-v8a`；App 最多每 3 天自动查一次，可在"关于"页手动检查 |
| 卓易通里书架不自动更新 | 设置 → 书架 → 智能更新，取消全部限制选项（作者与论坛用户实测） |
| 通知栏不显示下载进度 | 卓易通通知兼容问题，无解，不影响功能 |

## 8. 不要做的事

- 不要把 token、密钥或密码提交进仓库（fork 是公开仓库）。
- 不要在 fork 里启用作者的 `harmony_release.yml`：它会往同一个仓库发 `release` 类型的 Release，
  虽然 App 端已按 tag 过滤，但会造成混乱且浪费 Actions 时长。
- 不要改 Release 资产的命名规则。

## 9. 本地环境（维护者电脑）

- 本地有一份克隆，remote `origin` 指向 fork，另有 `upstream` 指向官方仓库
  （仅浅拉取了 `v0.20.4` tag，用于对照源码）。
- 克隆目录内有一个 `_private/` 子目录，存放签名密钥备份和私有备忘 `_private/LOCAL.md`（含本机路径、
  操作命令）。该目录通过 `.git/info/exclude` 在本机被忽略，**不会**也不应出现在远端。
  接手维护的人或 AI 应先读 `_private/LOCAL.md`。不要在该仓库运行 `git clean -x`。
- 已安装工具：Git、GitHub CLI、OpenJDK 17（含 `keytool`）。
- 未安装 Android SDK，本地不编译；全部编译在 GitHub Actions 完成。

## 10. 时间线

- 2026-09-26 fork 仓库；新增 `harmony_preview.yml`；生成签名密钥并写入 Secrets；发布 `v0.20.4-harmony-preview.1`。
- 同日 新增 `.github/patches/harmony-preview/` 更新器补丁，开启 `-Penable-updater`；发布 `v0.20.4-harmony-preview.2`。
- 同日 加入每日定时触发；禁用作者的其它 workflow。
- 同日 新增 `downloader.py`：CBZ 临时目录移入私有缓存（规避鸿蒙图库索引）、CBZ 收尾容错；发布 `v0.20.4-harmony-preview.3`。
