#!/usr/bin/env bash
set -euo pipefail
package=dev.maccam912.phaseline
log="$RUNNER_TEMP/phaseline-android.log"

adb install -r "$RUNNER_TEMP/android-test/Phaseline-Android.apk"
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard
adb shell settings put secure immersive_mode_confirmations confirmed
adb shell am force-stop "$package"
adb logcat -c
# Stream from before launch: a fresh emulator can rotate its log buffers during startup.
adb logcat -v threadtime godot:I Godot:I AndroidRuntime:E libc:F DEBUG:E ActivityManager:I ActivityTaskManager:I '*:S' > "$log" &
logger_pid=$!
trap 'kill "$logger_pid" 2>/dev/null || true' EXIT
adb shell am start -W -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p "$package"

for _ in {1..120}; do
  if grep -qE 'Godot Engine v4\.7\.2' "$log" && grep -q 'OpenGL API' "$log"; then
    sleep 5
    if grep -qE 'SCRIPT ERROR|Parse Error|FATAL EXCEPTION| E godot *: ERROR:' "$log"; then
      tail -n 150 "$log"
      exit 1
    fi
    adb shell pidof "$package"
    adb shell dumpsys activity activities > "$RUNNER_TEMP/phaseline-activity.log"
    grep -E "(mResumedActivity|topResumedActivity).*$package/" "$RUNNER_TEMP/phaseline-activity.log"
    grep -E 'Godot Engine|OpenGL API' "$log"
    exit 0
  fi
  sleep 1
done
tail -n 200 "$log"
adb logcat -b crash -d
exit 1
