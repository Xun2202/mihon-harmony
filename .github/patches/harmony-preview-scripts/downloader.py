"""
Harmony Preview: extra Downloader.kt edits applied after the author's harmony patch.

1. CBZ mode: keep the per-chapter temporary directory in the app's private cache
   instead of the user's SAF download folder. On HarmonyOS the system gallery
   indexes everything under the ZhuoyiTong shared storage and ignores `.nomedia`,
   so images must never be written there as loose files. Only the final `.cbz`
   touches the shared folder.

2. CBZ finalisation: tolerate SAF providers that cannot rename or delete.
   A stale `<chapter>.cbz` from an earlier failed attempt is removed first, and a
   failure to delete the `.cbz_tmp` source after a successful copy only logs a
   warning instead of failing the whole chapter.

Run from the repository root of the checked-out upstream tag *after* the
author's patch has been applied.
"""
from pathlib import Path

path = Path("app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt")
text = path.read_text()


def replace_once(old: str, new: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f"Missing Downloader.kt pattern (harmony-preview): {old!r}")
    text = text.replace(old, new, 1)


# --- imports -----------------------------------------------------------------
import_anchor = "import java.io.File\n"
if "import java.io.IOException\n" not in text:
    replace_once(import_anchor, import_anchor + "import java.io.IOException\n")

# --- 1. temporary directory location ------------------------------------------
replace_once(
    "        val tmpDir = mangaDir.createDirectory(chapterDirname + TMP_DIR_SUFFIX)!!\n",
    "        // Harmony: in CBZ mode download pages into private app cache so the\n"
    "        // HarmonyOS gallery (which ignores .nomedia) never sees loose images.\n"
    "        val tmpDir = if (downloadPreferences.saveChaptersAsCBZ.get()) {\n"
    "            val cacheTmpDir = File(\n"
    "                context.cacheDir,\n"
    "                \"harmony_download_tmp/${download.manga.id}/$chapterDirname$TMP_DIR_SUFFIX\",\n"
    "            )\n"
    "            cacheTmpDir.mkdirs()\n"
    "            UniFile.fromFile(cacheTmpDir)!!\n"
    "        } else {\n"
    "            mangaDir.createDirectory(chapterDirname + TMP_DIR_SUFFIX)!!\n"
    "        }\n",
)

# --- 2. CBZ finalisation --------------------------------------------------------
replace_once(
    '        zip.renameToOrCopy("$dirname.cbz")\n'
    "        tmpDir.delete()\n",
    '        finalizeArchive(mangaDir, zip, "$dirname.cbz")\n'
    "        tmpDir.delete()\n",
)

replace_once(
    "    /**\n"
    "     * Creates a ComicInfo.xml file inside the given directory.\n"
    "     */\n",
    "    /**\n"
    "     * Harmony: moves the finished `.cbz_tmp` archive to its final name, tolerating\n"
    "     * SAF providers that support neither renaming nor reliable deletion.\n"
    "     */\n"
    "    private fun finalizeArchive(mangaDir: UniFile, zip: UniFile, targetName: String) {\n"
    "        // A leftover target from a previous failed attempt would block us forever.\n"
    "        mangaDir.findFile(targetName)?.let { stale ->\n"
    "            if (!stale.delete()) {\n"
    "                throw IOException(\"Failed to remove stale archive '$targetName'\")\n"
    "            }\n"
    "        }\n"
    "\n"
    "        if (zip.renameTo(targetName)) return\n"
    "\n"
    "        val target = mangaDir.createFile(targetName)\n"
    "            ?: throw IOException(\"Failed to create archive '$targetName'\")\n"
    "        try {\n"
    "            zip.openInputStream().use { input ->\n"
    "                target.openOutputStream().use { output ->\n"
    "                    input.copyTo(output)\n"
    "                }\n"
    "            }\n"
    "        } catch (e: Exception) {\n"
    "            target.delete()\n"
    "            throw IOException(\"Failed to copy archive to '$targetName'\", e)\n"
    "        }\n"
    "\n"
    "        if (!zip.delete()) {\n"
    "            logcat(LogPriority.WARN) { \"Archive copied to '$targetName' but temporary '${zip.name}' could not be deleted\" }\n"
    "        }\n"
    "    }\n"
    "\n"
    "    /**\n"
    "     * Creates a ComicInfo.xml file inside the given directory.\n"
    "     */\n",
)

path.write_text(text)
print("Downloader.kt harmony-preview edits applied")
