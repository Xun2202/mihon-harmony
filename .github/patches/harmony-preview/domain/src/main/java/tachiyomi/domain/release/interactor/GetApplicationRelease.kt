package tachiyomi.domain.release.interactor

import tachiyomi.domain.release.model.Release
import tachiyomi.domain.release.service.ReleaseService

class GetApplicationRelease(
    private val service: ReleaseService,
) {
    suspend fun await(arguments: Arguments): Result {
        val release = service.latest(arguments) ?: return Result.NoNewUpdate

        // Check if latest version is different from current version
        val isNewVersion = isNewVersion(
            arguments.isPreview,
            arguments.commitCount,
            arguments.versionName,
            release.version,
        )
        return when {
            isNewVersion -> Result.NewUpdate(release)
            else -> Result.NoNewUpdate
        }
    }

    private fun isNewVersion(
        isPreview: Boolean,
        commitCount: Int,
        versionName: String,
        versionTag: String,
    ): Boolean {
        // Mihon Harmony fork: versions look like "0.20.4-harmony.1" (versionName,
        // optionally followed by "-<commitCount>" in preview builds) and release tags
        // look like "v0.20.4-harmony.1" or "v0.20.4-harmony-preview.1".
        val newHarmony = parseHarmonyVersion(versionTag)
        val oldHarmony = parseHarmonyVersion(versionName)
        if (newHarmony != null && oldHarmony != null) {
            return compareVersions(newHarmony, oldHarmony) > 0
        }

        // Fallback to the upstream Mihon logic.
        // Removes prefixes like "r" or "v"
        val newVersion = versionTag.replace("[^\\d.]".toRegex(), "")
        return if (isPreview) {
            // Preview builds: based on releases in "mihonapp/mihon-preview" repo
            // tagged as something like "r1234"
            newVersion.toIntOrNull()?.let { it > commitCount } ?: false
        } else {
            // Release builds: based on releases in "mihonapp/mihon" repo
            // tagged as something like "v0.1.2"
            val oldVersion = versionName.replace("[^\\d.]".toRegex(), "")

            val newSemVer = newVersion.split(".").mapNotNull { it.toIntOrNull() }
            val oldSemVer = oldVersion.split(".").mapNotNull { it.toIntOrNull() }

            compareVersions(newSemVer, oldSemVer) > 0
        }
    }

    /**
     * Returns `[major, minor, patch, harmonyPatch]` or null when the string is not
     * a Mihon Harmony version.
     */
    private fun parseHarmonyVersion(value: String): List<Int>? {
        val match = HARMONY_VERSION_REGEX.find(value) ?: return null
        return match.groupValues.drop(1).map { it.toInt() }
    }

    private fun compareVersions(a: List<Int>, b: List<Int>): Int {
        val size = maxOf(a.size, b.size)
        for (index in 0 until size) {
            val x = a.getOrElse(index) { 0 }
            val y = b.getOrElse(index) { 0 }
            if (x != y) return x.compareTo(y)
        }
        return 0
    }

    data class Arguments(
        val isFoss: Boolean,
        val isPreview: Boolean,
        val commitCount: Int,
        val versionName: String,
        val repository: String,
        val forceCheck: Boolean = false,
    )

    sealed interface Result {
        data class NewUpdate(val release: Release) : Result
        data object NoNewUpdate : Result
        data object OsTooOld : Result
    }

    private companion object {
        val HARMONY_VERSION_REGEX = Regex("""(\d+)\.(\d+)\.(\d+)-harmony(?:-preview)?\.(\d+)""")
    }
}
