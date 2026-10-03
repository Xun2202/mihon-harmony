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
| 包名 | `app.mihon.debug`（preview 构建类型自带后缀，可与官方 `app.mihon` 并存） |
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

## 3. 仓库结构

```
patches/series                 # 套用顺序, 每行一个文件名, # 开头为注释
patches/0001-*.patch           # git format-patch 格式, 基于官方 v0.20.4 生成
patches/0002-*.patch
patches/0003-*.patch
scripts/prepare-source.sh      # 官方源码 → 套补丁 → 改版本号, 每步一个 commit
.github/workflows/harmony_preview.yml   # 每日构建发布
.github/workflows/check_patches.yml     # 补丁可套用性检查
docs/MAINTENANCE.md            # 本文
README.md                      # 面向用户的说明 + 补丁一览
LICENSE                        # Apache-2.0 (沿用上游)
```

旧 fork 布局（`.github/patches/harmony.patch` + workflow 内嵌 Python + 整文件覆盖目录 + `downloader.py`）
已全部折算进上面三个标准补丁，不再有「字符串锚点替换」这种脆弱机制。

## 4. 构建流程（`harmony_preview.yml` 做了什么）

1. **解析版本**：`upstream_tag`（为空则调 GitHub API 取 `mihonapp/mihon` 最新稳定版）、`patch_number`（默认 1）。
   `release_tag = <upstream_tag>-harmony-preview.<N>`。
2. **跳过已存在的 Release**（`dry_run` 时不跳过）。这是定时任务不重复编译的关键。
3. **校验四个签名 Secrets 非空**。
4. **拉官方源码**：`git clone --branch <tag> --single-branch`（完整历史，约 80 MB、几秒钟）。preview 构建的
   `versionNameSuffix` 和 `BuildConfig.COMMIT_COUNT` 来自 `git rev-list --count HEAD`，浅克隆会让它变成个位数。
   同时读出官方 `.github/.java-version` 作为 JDK 版本。
5. **`scripts/prepare-source.sh <src> <tag> <N>`**：
   - 逐个 `git apply --3way patches/<file>` 并 commit；任何一个套不上就失败退出，并打印是哪个补丁。
   - `FORK_REPO` 环境变量（workflow 传 `github.repository`）与默认值 `Xun2202/mihon-harmony` 不同时，
     把更新器指向的仓库改掉——方便别人 fork 本仓库后直接用。
   - `versionCode = 官方 versionCode × 100 + N`，`versionName = "<官方版本>-harmony.<N>"`，提交。
6. **编译**：`./gradlew assemblePreview -Penable-updater`
   - `assemblePreview`：preview 构建类型 → Private 安装器可见，包名 `app.mihon.debug`。
   - `-Penable-updater`：`BuildConfig.UPDATER_ENABLED = true`，否则 App 不检查更新。
   - 签名：`MIHON_GITHUB_RELEASE=true` 时 `app/build.gradle.kts` 从 `storeFileBase64 / storePassword / keyAlias / keyPassword`
     读取密钥（由 Secrets 注入）。
7. **发布**：APK 重命名为 `mihon-<tag>-{arm64-v8a,universal}.apk`，上传 artifact；非 `dry_run` 时
   `gh release create <tag> --target $GITHUB_SHA`，说明里列出补丁 Subject 和 SHA-256。
   - **不推送 tag 到源码**。默认 `GITHUB_TOKEN` 无权推送含 workflow 文件改动的提交，所以让 `gh release create` 直接在 `main` 当前提交上建 tag。
   - **不要**把 `.sha1` / `.sha256` 之类的文件当作 Release 资产上传：更新器用「文件名含 `-arm64-v8a`」挑 APK，
     `mihon-xxx-arm64-v8a.apk.sha1` 会把下载链接顶掉。校验值只写进 Release 说明。

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

每个补丁的意图写在它的 commit message 里，解决冲突前先读一遍。补丁 0001 和 0003 都改 `Downloader.kt`，
上游重构下载器时两者通常要一起重做。

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
- **备份现状（2026-10-03 核查）**：密钥文件 `mihon-harmony.jks` 和密码只保存在维护者本人电脑上
  （当时的本地克隆目录下的 `_private/` 子目录，由另一台机器上的 AI 会话生成）。GitHub Secrets 只能写入不能读出，
  所以云端 AI 会话**拿不到**这把钥匙。
- **待办**：请维护者把 `mihon-harmony.jks`、Base64 文本和密码上传到一个 **private** 仓库
  `Xun2202/mihon-harmony-keystore`（与 `mihon-repo-keystore`、`animeko-harmony-keystore` 的做法一致），
  之后任何会话都能恢复 Secrets。
- **丢失密钥 = 已安装用户无法覆盖升级**。若真的丢了：重新生成密钥、更新四个 Secrets、提醒用户先在 App 内备份数据再卸载重装。

## 7. 已知问题与排错

| 现象 | 原因 / 处理 |
| --- | --- |
| `prepare-source.sh` 报 `Patch 000X ... does not apply` | 官方新版改动了补丁触及的代码。按 §5.1 rebase。先看 zsyou 仓库的 `.github/patches/harmony.patch` 是否已更新，可作参考 |
| 编译报错在 `AppUpdateChecker.kt` / `ReleaseServiceImpl.kt` / `GetApplicationRelease.kt` | 官方改了这几个文件的接口（补丁 0002 是基于 v0.20.4 的近乎整文件改写）。取官方新版文件重新套用 0002 的意图 |
| 编译报错在 `Downloader.kt` | 补丁 0001 / 0003 的改动点被上游重构。参考两个补丁的 commit message 重做 |
| 图库里仍能看到漫画图片 | 确认 App「保存为 CBZ」已开启；目录模式无法规避，去图库隐藏该相册。历史遗留的 `_tmp` 目录可手动删除 |
| Release 步骤失败 `refusing to allow a GitHub App to create or update workflow` | 有人把推 tag 的逻辑加回来了。保持 `gh release create --target $GITHUB_SHA`，不要 `git push` tag |
| 定时任务不跑 | 仓库 60 天无提交被 GitHub 暂停，到 Actions 页面手动 Enable |
| App 内检查不到更新 | 确认 Release 不是 draft、tag 含 `-harmony-preview.`、资产文件名含 `-arm64-v8a`；App 最多每 3 天自动查一次，可在「关于」页手动检查 |
| 卓易通里书架不自动更新 | 设置 → 书架 → 智能更新，取消全部限制选项 |
| 通知栏不显示下载进度 | 卓易通通知兼容问题，无解，不影响功能 |

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
