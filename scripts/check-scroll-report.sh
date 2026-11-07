#!/usr/bin/env bash
# Exercise the exact Android-free report model without compiling a second app variant.
set -euo pipefail
source_root="${1:?usage: check-scroll-report.sh <prepared-source>}"
report_root="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/scroll-report.XXXXXX")"
trap 'rm -rf "$report_root"' EXIT
python3 - "$source_root" "$report_root" <<'PY_REPORT_MODEL'
from pathlib import Path
import hashlib, json, re, shutil, sys
source, root = map(Path, sys.argv[1:])
main = root / 'src/main/kotlin'
test = root / 'src/test/kotlin'
main.mkdir(parents=True)
test.mkdir(parents=True)
report = source / 'app/src/main/java/eu/kanade/tachiyomi/util/system/HarmonyFramePerf.kt'
counter = source / 'presentation-core/src/main/java/tachiyomi/presentation/core/components/PanoramaFrameCounters.kt'
trace = source / 'presentation-core/src/main/java/tachiyomi/presentation/core/components/PanoramaScrollTrace.kt'
suite = source / 'app/src/test/java/eu/kanade/tachiyomi/util/system/HarmonyFramePerfTest.kt'
model = 'class PerfHeader(' + report.read_text().split('class PerfHeader(', 1)[1]
prefix = '''package eu.kanade.tachiyomi.util.system
import tachiyomi.presentation.core.components.PanoramaScrollTrace
import java.text.SimpleDateFormat
import java.util.*
import kotlin.math.*
'''
(main / 'PerfModel.kt').write_text(prefix + model)
shutil.copyfile(counter, main / counter.name)
constants = []
for name in ('PHASE_IDLE', 'PHASE_DRAG', 'PHASE_FLING'):
    match = re.search(r'const val ' + name + r'\s*=\s*(\d+)', trace.read_text())
    assert match, name
    constants.append('const val ' + name + '=' + match.group(1))
(main / 'PanoramaScrollTrace.kt').write_text('package tachiyomi.presentation.core.components\nobject PanoramaScrollTrace { ' + '; '.join(constants) + ' }\n')
shutil.copyfile(suite, test / suite.name)
(root / 'settings.gradle.kts').write_text('pluginManagement { repositories { gradlePluginPortal(); mavenCentral() } }\nrootProject.name="scroll-report-check"\n')
(root / 'build.gradle.kts').write_text('''plugins { kotlin("jvm") version "2.4.10" }
repositories { mavenCentral() }
kotlin { jvmToolchain(21) }
dependencies { testImplementation("org.junit.jupiter:junit-jupiter:5.13.4"); testRuntimeOnly("org.junit.platform:junit-platform-launcher") }
tasks.test { useJUnitPlatform(); testLogging { events("passed", "failed"); exceptionFormat=org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL } }
''')
print('Scroll report model binding:', json.dumps({
    'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest(),
    'model_suffix_sha256': hashlib.sha256(model.encode()).hexdigest(),
    'counter_sha256': hashlib.sha256(counter.read_bytes()).hexdigest(),
    'test_sha256': hashlib.sha256(suite.read_bytes()).hexdigest(),
    'phase_constants_from_source': constants,
}))
PY_REPORT_MODEL
flock /tmp/gradle.lock "$source_root/gradlew" -p "$report_root" test --no-daemon
