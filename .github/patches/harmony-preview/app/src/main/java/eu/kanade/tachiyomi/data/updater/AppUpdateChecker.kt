package eu.kanade.tachiyomi.data.updater

import eu.kanade.tachiyomi.BuildConfig
import eu.kanade.tachiyomi.util.system.isFossBuildType
import eu.kanade.tachiyomi.util.system.isPreviewBuildType
import tachiyomi.core.common.util.lang.withIOContext
import tachiyomi.domain.release.interactor.GetApplicationRelease
import uy.kohesive.injekt.injectLazy

class AppUpdateChecker {

    private val getApplicationRelease: GetApplicationRelease by injectLazy()

    suspend fun checkForUpdate(forceCheck: Boolean = false): GetApplicationRelease.Result {
        return withIOContext {
            val result = getApplicationRelease.await(
                GetApplicationRelease.Arguments(
                    isFossBuildType,
                    isPreviewBuildType,
                    BuildConfig.COMMIT_COUNT.toInt(),
                    BuildConfig.VERSION_NAME,
                    GITHUB_REPO,
                    forceCheck,
                ),
            )

            result
        }
    }
}

/**
 * Mihon Harmony fork: both the stable and the preview channel are published as
 * GitHub releases of the fork repository. The channel is told apart by the tag
 * suffix (`-harmony.N` vs `-harmony-preview.N`).
 */
const val GITHUB_REPO: String = "Xun2202/mihon-harmony"

private val HARMONY_VERSION_REGEX = Regex("""^(\d+\.\d+\.\d+)-harmony\.(\d+)""")

val RELEASE_TAG: String by lazy {
    val match = HARMONY_VERSION_REGEX.find(BuildConfig.VERSION_NAME)
    if (match == null) {
        "v${BuildConfig.VERSION_NAME}"
    } else {
        val (base, patch) = match.destructured
        if (isPreviewBuildType) {
            "v$base-harmony-preview.$patch"
        } else {
            "v$base-harmony.$patch"
        }
    }
}

val RELEASE_URL = "https://github.com/$GITHUB_REPO/releases/tag/$RELEASE_TAG"
