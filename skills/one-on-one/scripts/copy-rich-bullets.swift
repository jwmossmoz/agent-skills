#!/usr/bin/env swift
import AppKit
import Foundation

struct Payload: Decodable {
    let sections: [Section]
}

struct Section: Decodable {
    let title: String
    let bullets: [Bullet]
}

struct Segment: Decodable {
    let text: String
    let url: String?
}

enum Bullet: Decodable {
    case text(String)
    case segments([Segment])

    init(from decoder: Decoder) throws {
        if let value = try? decoder.singleValueContainer().decode(String.self) {
            self = .text(value)
            return
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        if let segments = try? container.decode([Segment].self, forKey: .segments) {
            self = .segments(segments)
            return
        }
        if let text = try? container.decode(String.self, forKey: .text) {
            let url = try? container.decode(String.self, forKey: .url)
            self = .segments([Segment(text: text, url: url)])
            return
        }

        throw DecodingError.dataCorrupted(
            DecodingError.Context(
                codingPath: decoder.codingPath,
                debugDescription: "Bullet must be a string or an object with text/segments"
            )
        )
    }

    private enum CodingKeys: String, CodingKey {
        case segments
        case text
        case url
    }
}

func usage() -> Never {
    fputs("Usage: copy-rich-bullets.swift <payload.json|->\n", stderr)
    exit(2)
}

func escapeHTML(_ value: String) -> String {
    value
        .replacingOccurrences(of: "&", with: "&amp;")
        .replacingOccurrences(of: "<", with: "&lt;")
        .replacingOccurrences(of: ">", with: "&gt;")
        .replacingOccurrences(of: "\"", with: "&quot;")
}

func html(for segments: [Segment]) -> String {
    segments.map { segment in
        let text = escapeHTML(segment.text)
        guard let url = segment.url, !url.isEmpty else {
            return text
        }
        return "<a href=\"\(escapeHTML(url))\">\(text)</a>"
    }.joined()
}

func plain(for segments: [Segment]) -> String {
    segments.map { segment in
        guard let url = segment.url, !url.isEmpty else {
            return segment.text
        }
        return "\(segment.text) (\(url))"
    }.joined()
}

func segments(for bullet: Bullet) -> [Segment] {
    switch bullet {
    case .text(let text):
        return [Segment(text: text, url: nil)]
    case .segments(let segments):
        return segments
    }
}

guard CommandLine.arguments.count == 2 else {
    usage()
}

let payloadURL = URL(fileURLWithPath: CommandLine.arguments[1])
let data: Data
if CommandLine.arguments[1] == "-" {
    data = FileHandle.standardInput.readDataToEndOfFile()
} else {
    data = try Data(contentsOf: payloadURL)
}
let payload = try JSONDecoder().decode(Payload.self, from: data)

var htmlBody = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
body { font-family: Arial, sans-serif; font-size: 11pt; }
p.topic { margin: 8px 0 2px 0; font-weight: 700; }
ul { margin-top: 0; margin-bottom: 8px; }
li { margin: 2px 0; }
</style>
</head>
<body>
"""

var plainText = ""

for section in payload.sections {
    htmlBody += "<p class=\"topic\">\(escapeHTML(section.title))</p><ul>"
    plainText += "\(section.title)\n"

    for bullet in section.bullets {
        let bulletSegments = segments(for: bullet)
        htmlBody += "<li>\(html(for: bulletSegments))</li>"
        plainText += "- \(plain(for: bulletSegments))\n"
    }

    htmlBody += "</ul>"
    plainText += "\n"
}

htmlBody += "</body></html>"
plainText = plainText.trimmingCharacters(in: .whitespacesAndNewlines)

let attributed = NSAttributedString(
    html: Data(htmlBody.utf8),
    options: [
        .documentType: NSAttributedString.DocumentType.html,
        .characterEncoding: String.Encoding.utf8.rawValue,
    ],
    documentAttributes: nil
)!

let rtf = attributed.rtf(
    from: NSRange(location: 0, length: attributed.length),
    documentAttributes: [:]
)!

let pasteboard = NSPasteboard.general
pasteboard.clearContents()
pasteboard.declareTypes([.html, .rtf, .string], owner: nil)
pasteboard.setString(htmlBody, forType: .html)
pasteboard.setData(rtf, forType: .rtf)
pasteboard.setString(plainText, forType: .string)

print("Copied \(payload.sections.count) sections to the clipboard as HTML, RTF, and plain text.")
