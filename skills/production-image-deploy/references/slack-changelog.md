# Slack changelog

Send the same changelog to both channels unless the user changes the
destinations:

- [#relops](https://mozilla.enterprise.slack.com/archives/CNN462N2F) (`CNN462N2F`)
- [#firefox-ci-proj](https://mozilla.enterprise.slack.com/archives/C030SPMMYQN) (`C030SPMMYQN`)

Do not ask the user to supply these known destinations. For clipboard
delivery, state that the message is ready to paste into both channels.

Use this September 2026 post as the format example:
https://mozilla.slack.com/archives/CNN462N2F/p1789394207903229

It replaces the older June example. The required layout has a short opening,
change bullets, `Deployment`, and `Release notes`. Use named links, not a
list of bare URLs. Keep the section labels as plain text. Bold the version
change within its bullet.

Prepare the message after the fxci-config PR merges. Check the apply job
before saying the images are deployed. If it is still running, state that
deployment is in progress. Verify every release-note URL separately; merge
status does not prove that the SBOM upload succeeded.

## Required layout

This example uses Markdown for a connector that accepts Markdown. It is not
a code block to paste into Slack. For clipboard delivery, use HTML lists,
anchors, and bold text as shown below.

```markdown
We've updated the Firefox CI Windows cloud images

- Updated generic-worker, livelog, start-worker, and taskcluster-proxy from **<OLD> to <NEW>**
- <Other Windows change from the ronin_puppet range>

Deployment

- [fxci-config PR #<PR_NUMBER>](https://github.com/mozilla-releng/fxci-config/pull/<PR_NUMBER>)

Release notes

- [Windows 10 x64 22H2](https://github.com/mozilla-platform-ops/worker-images/blob/main/sboms/win10-64-2009-<VERSION>.md)
- [Windows 11 x64 25H2](https://github.com/mozilla-platform-ops/worker-images/blob/main/sboms/win11-64-25h2-<VERSION>.md)
```

- Replace all placeholders with verified rollout values.
- Include each Windows change from the ronin_puppet range. Use concrete
  package or configuration changes; omit filler such as "Latest updates".
- For a partial rollout, name the OS, architecture, or pool family in the
  opening. Include only release notes for images that changed.
- Use one bullet per release-note link. The visible text is the friendly
  image name. Do not put a raw URL after the name.
- If an SBOM is missing, recover its upload or state that its release notes
  are pending. Do not include a broken link.
- Preserve any session instruction about sending or clipboard delivery.
  Report the actual result: sent, draft saved, or copied to clipboard.

## Windows friendly names

Use the published version for each config; families can have different
versions. Retired configs are not part of the default list.

| Link label | worker-images config |
|---|---|
| Windows 10 x64 22H2 | `win10-64-2009` |
| Windows 11 x64 25H2 | `win11-64-25h2` |
| Windows 11 ARM64 25H2 tester | `win11-a64-25h2-tester` |
| Windows 11 ARM64 25H2 L1 builder | `win11-a64-25h2-builder` |
| Windows 11 ARM64 25H2 L3 builder | `trusted-win11-a64-25h2-builder` |
| Windows Server 2022 x64 L1 builder | `win2022-64-2009` |
| Windows Server 2022 x64 L3 builder | `trusted-win2022-64-2009` |
| Windows Server 2025 x64 L1 builder | `win2025-64-24h2` |
| Windows Server 2025 x64 L3 builder | `trusted-win2025-64-24h2` |

## Rich-text clipboard

Plain-text drafts can lose list formatting or expose raw URLs. For clipboard
delivery, put both HTML and plain text on the macOS clipboard. HTML contains
real lists, named links, and bold text; plain text is the fallback.

Fill the variables below from the verified rollout, save as `slack-clip.py`,
and run `uv run --script slack-clip.py`. Include every rebuilt config in
`links`. Do not replace this with a plain-text Slack draft. If a connector
cannot edit an existing draft, copy the corrected rich text for replacement
and say that the existing draft remains unchanged.

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyobjc-framework-Cocoa"]
# ///
from html import escape
from AppKit import NSPasteboard, NSPasteboardTypeHTML, NSPasteboardTypeString

header = "We've updated the Firefox CI Windows cloud images"
old_version, new_version = "<OLD>", "<NEW>"
pr_number = "<PR_NUMBER>"
other_changes = ["<Other verified Windows change>"]
links = [
    ("Windows 10 x64 22H2", "win10-64-2009-<VERSION>"),
    ("Windows 11 x64 25H2", "win11-64-25h2-<VERSION>"),
]
base = "https://github.com/mozilla-platform-ops/worker-images/blob/main/sboms"
pr = f"https://github.com/mozilla-releng/fxci-config/pull/{pr_number}"
prefix = "Updated generic-worker, livelog, start-worker, and taskcluster-proxy from "
versions = f"{old_version} to {new_version}"

html = f"<p>{escape(header)}</p><ul><li>{escape(prefix)}<strong>{escape(versions)}</strong></li>"
html += "".join(f"<li>{escape(change)}</li>" for change in other_changes)
html += f'</ul><p>Deployment</p><ul><li><a href="{escape(pr, quote=True)}">fxci-config PR #{escape(pr_number)}</a></li></ul>'
html += "<p>Release notes</p><ul>"
html += "".join(
    f'<li><a href="{escape(base + "/" + filename + ".md", quote=True)}">{escape(label)}</a></li>'
    for label, filename in links
)
html += "</ul>"
plain = header + "\n\n" + "\n".join(
    f"• {change}" for change in [prefix + versions, *other_changes]
)
plain += f"\n\nDeployment\n• fxci-config PR #{pr_number}: {pr}\n\nRelease notes\n"
plain += "\n".join(f"• {label}: {base}/{filename}.md" for label, filename in links)

pb = NSPasteboard.generalPasteboard()
pb.clearContents()
pb.setString_forType_(html, NSPasteboardTypeHTML)
pb.setString_forType_(plain, NSPasteboardTypeString)
assert pb.stringForType_(NSPasteboardTypeHTML) == html
print("Copied changelog to clipboard (HTML + plain text)")
```

## Linux

Use the same layout, with an opening that names the Ubuntu images or pool
families that changed. Replace the Windows package bullet with the verified
Linux changes. Include the worker-images build link under `Deployment` and
one named SBOM link per rebuilt config under `Release notes`. For a full
Ubuntu 24.04 rollout, include the Wayland AMD64 SBOM. The clipboard recipe
uses the same lists and named links; replace its Windows-specific text.

## Phase 4 — Announce in Slack

After the fxci-config PR **merges**, prepare the same changelog for both
`#relops` (`CNN462N2F`) and `#firefox-ci-proj` (`C030SPMMYQN`). Use the September 2026 post as the format example:
https://mozilla.slack.com/archives/CNN462N2F/p1789394207903229

Use a short opening, change bullets, a `Deployment` section with a named PR
link, and a `Release notes` section with one named link per rebuilt image.
Bold the old-to-new package version in its bullet. Match the opening to the
actual rollout scope. Verify each SBOM link before use.

Read `references/slack-changelog.md` before preparing the message. It contains
the exact layout and the HTML + plain-text clipboard recipe. Use rich text
for clipboard delivery so Slack retains lists, bold text, and named links.
Do not substitute a draft with bare URLs. If a connector cannot preserve or
edit that format, copy the correctly formatted message to the clipboard and
state that it is ready to paste. Use both channels unless the user changes the destinations. Do not ask
for these known channel names. Report whether the message
was sent, saved as a draft, or copied to the clipboard.
