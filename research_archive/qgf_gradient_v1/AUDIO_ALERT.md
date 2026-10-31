# Human Intervention Audio Alert

CURRENT STATUS: DISABLED BY USER on2026-10-26 after the30second alarm was too
loud. This supersedes all earlier audio instructions below. The active heartbeat
now uses text only. audio_alert_disabled.flag and an early guard in
alert_user.ps1 prevent playback and volume changes,including test calls.
Do not remove the guard/flag or replay sound without new explicit user request.
The last alarm had already ended and restored original volume/mute; no alert
process remains. A disabled-script verification returned played=false.

The remainder is retained historical setup evidence only.

User authorization2026-10-26CST: play a loud sound on their computer when the
QGF experiment requires human intervention while they sleep. The user heard a
two-second test and confirmed the volume is suitable.

Automation qgf-wam-rl remains ACTIVE every45minutes. Its prompt now calls the
local alert_user.ps1 only for an unresolved condition requiring human action.
Normal progress and automatically repaired failures do not sound an alarm.
Checking is periodic, so this is not an instantaneous remote failure alarm.

Playback directly targets the active Realtek Speaker through WASAPI; the
Windows default output remains the H27T22S-3 Pro monitor. The selected Speaker
was muted at approximately51.01888% before the test. The successful test
temporarily unmuted it at85% for2seconds, then restored both level and mute.
The user independently confirmed hearing it. No ongoing test loop was started.

Production defaults:30seconds,85% endpoint volume, alternating740/1050Hz tones,
120minute cooldown for the same incident,maximum3repeats,local mutex to avoid
overlapping alarms. Use a stable incident identifier; do not rotate IDs to
circumvent the cooldown. The script restores the prior endpoint level/mute in
finally and does not change the default device. Logs are audio_alert_events.jsonl
and audio_alert_state.json alongside the script, local to this computer.

Run on the Windows host, not login1:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\SEU student\Documents\Codex\2026-07-10\new-chat\qgf_gradient_v1\alert_user.ps1" -IncidentId "stable-incident-id" -Reason "What failed and what the user must do" -Seconds 30 -Volume 0.85
```

Check for PLAYBACK_API_COMPLETED and restored volume/mute. Do not claim the user
heard a future alarm merely because the playback API succeeded. If playback
fails, report that and the required intervention in chat. Computers must remain
awake, Codex running, and speakers connected/powered. This setup does not wake a
sleeping/off PC, change its power plan, or bypass the operating-system session.

Read-only endpoint check uses the same script with -Probe. Do not keep replaying
test sounds after the user has already confirmed the setup.
