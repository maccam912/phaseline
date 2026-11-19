#!/usr/bin/env bash
set -euo pipefail
package=dev.maccam912.phaseline
adb install -r "$RUNNER_TEMP/android-test/Phaseline-Android.apk"
adb logcat -c
adb shell am start -W -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p "$package"
for _ in {1..45}; do
  pid=$(adb shell pidof -s "$package" | tr -d '\r' || true)
  if [[ -n "$pid" ]]; then
    adb logcat --pid="$pid" -d > "$RUNNER_TEMP/phaseline-android.log"
    if grep -q 'Godot Engine v4.7.2' "$RUNNER_TEMP/phaseline-android.log"; then
      sleep 4
      adb logcat --pid="$pid" -d > "$RUNNER_TEMP/phaseline-android.log"
      if grep -E 'SCRIPT ERROR|Parse Error|FATAL EXCEPTION| E godot *: ERROR:' "$RUNNER_TEMP/phaseline-android.log"; then
        exit 1
      fi
      [[ "$(adb shell pidof -s "$package" | tr -d '\r')" == "$pid" ]]
      adb shell dumpsys activity activities | grep -E "mResumedActivity|topResumedActivity" > "$RUNNER_TEMP/phaseline-activity.log"
      grep -F "$package" "$RUNNER_TEMP/phaseline-activity.log"
      exit 0
    fi
  fi
  sleep 1
done
adb logcat -d -t 300
exit 1
