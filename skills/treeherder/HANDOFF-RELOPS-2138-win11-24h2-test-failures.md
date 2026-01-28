# Handoff - RELOPS-2138: Windows 11 24H2 Test Failures Investigation

## Reference
- Jira: https://mozilla-hub.atlassian.net/browse/RELOPS-2138
- Bug: 2012615
- PR: https://github.com/mozilla-platform-ops/ronin_puppet/pull/1028
- Try Push: https://treeherder.mozilla.org/jobs?repo=try&revision=2444e20d52efee64c6ce58c09352b0fea0afa73e

## Status
In Progress / Blocked - Initial MinimizeAll fix didn't resolve all failures

## What Was Done
- Created branch `RELOPS-2138` off `windows` in ronin_puppet
- Restored MinimizeAll for Windows 11 24H2 using documented COM method:
  ```powershell
  (New-Object -ComObject Shell.Application).MinimizeAll()
  ```
- Created PR #1028 with the fix
- Investigated Windows KB updates between image 1.0.8 and 1.0.9:
  - Image 1.0.8: Build 26100.6584 (KB5065426, Sept 9, 2025)
  - Image 1.0.9: Build 26100.6899 (KB5066835, Oct 14, 2025)
  - KB5065789 (Sept 29) and KB5066835 (Oct 14) both update core DLLs: user32.dll, shell32.dll, twinui.dll, dwm*.dll
- Analyzed try push failures - found 18 failures across multiple categories:
  - Timeouts (focus-related): browser_popup_keyNav.js, browser_fullscreen_newwindow.js, test_non_8bit_video.html
  - Non-timeout failures: storage quota issues, vsync issues, HTTP2/3 network issues
- Attempted to create Azure VMs to reproduce locally (cleaned up after RDP issues)

## Files Changed
- `ronin_puppet/modules/win_taskcluster/files/task-user-init.ps1` - Uncommented and updated MinimizeAll for win_11_2009

## What's Left
- [ ] Test MinimizeAll fix on actual worker image (not just try push)
- [ ] Investigate if failures are caused by Windows KB updates vs MinimizeAll
- [ ] Consider testing with image 1.0.8 build (26100.6584) to isolate cause
- [ ] May need to file Firefox bugs if DLL changes in KB5065789/KB5066835 are root cause

## Key Decisions
| Decision | Rationale |
|----------|-----------|
| Use Shell.Application COM instead of explorer.exe GUID | Documented Microsoft API, more PowerShell-idiomatic |
| Only enable for win_11_2009, not win_10_2009 | User requested Windows 11 only |

## Blockers / Gotchas
- Try push still has 18 failures even with MinimizeAll potentially enabled
- Failures span multiple categories (not just focus): storage, network, graphics
- Windows KB5065789 and KB5066835 update core UI DLLs which may affect test behavior
- xpcshell tests failing (test_http2_with_http3_proxy.js) - these don't need UI focus, suggesting deeper system issues

## Test Failure Analysis

**Timeouts (potential focus issues):**
- browser_popup_keyNav.js (keyboard navigation)
- browser_fullscreen_newwindow.js (fullscreen)
- browser_bug481560.js (tab close shortcut)
- test_non_8bit_video.html (media)

**Non-timeout failures (system issues):**
- test_temporaryStorageEviction.js - Storage quota: 1024 == 0
- browser_test_clipboardcache.js - vsync not disabled
- browser_UrlbarInput_searchTerms.js - Off-by-one ordering
- test_http2_with_http3_proxy.js - Network assertion

## Relevant Links
- Treeherder: https://treeherder.mozilla.org/jobs?repo=try&revision=2444e20d52efee64c6ce58c09352b0fea0afa73e
- KB5065789 (Sept 29): https://support.microsoft.com/en-us/topic/september-29-2025-kb5065789-os-build-26100-6725-preview-fa03ce47-cec5-4d1c-87d0-cac4195b4b4e
- KB5066835 (Oct 14): https://support.microsoft.com/en-us/topic/october-14-2025-kb5066835-os-builds-26200-6899-and-26100-6899-1db237d8-9f3b-4218-9515-3e0a32729685
- Worker Image SBOMs: https://github.com/mozilla-platform-ops/worker-images/blob/main/sboms/

## Resume Prompt
Read HANDOFF.md and continue investigating RELOPS-2138. The MinimizeAll fix is in PR #1028 but try push still shows failures. Need to determine if root cause is the ronin_puppet change or Windows KB updates (KB5065789/KB5066835) that updated user32.dll, shell32.dll, and other UI DLLs.
