// Draws a RoHub TikTok video (1080x1920) from a timeline made by make_audio.py and adds its soundtrack.
//
//   swiftc -O render.swift -o build/render
//   build/render build/<name>.json                       writes the finished .mp4
//   build/render build/<name>.json --frames 1.0,6.5      writes preview PNGs instead
import AppKit
import AVFoundation
import Foundation

struct Screen: Decodable { let image: String; let from: Double; let zoom: [Double]; let focus: [Double] }
struct Item: Decodable {
    let kind: String
    let start: Double
    let end: Double
    let text: String?
    let accent: String?
    let size: Double?
    let y: Double?
    let image: String?
    let height: Double?
    let screens: [Screen]?
}
struct Spec: Decodable {
    let width: Int
    let height: Int
    let fps: Int
    let duration: Double
    let items: [Item]
    let video: String
    let audio: String
    let out: String
}

let args = CommandLine.arguments
let spec = try! JSONDecoder().decode(Spec.self, from: Data(contentsOf: URL(fileURLWithPath: args[1])))
let W = CGFloat(spec.width), H = CGFloat(spec.height)
let sRGB = CGColorSpace(name: CGColorSpace.sRGB)!
let accentColor = NSColor(srgbRed: 0.62, green: 0.68, blue: 1.0, alpha: 1)

// ---------- helpers ----------
func color(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: a)
}
func clamp(_ x: Double) -> Double { max(0, min(1, x)) }
func easeOut(_ x: Double) -> Double { 1 - pow(1 - clamp(x), 3) }
func easeIn(_ x: Double) -> Double { pow(clamp(x), 3) }
func easeInOut(_ x: Double) -> Double { let t = clamp(x); return t < 0.5 ? 4 * t * t * t : 1 - pow(-2 * t + 2, 3) / 2 }
func easeOutBack(_ x: Double) -> Double { let c1 = 1.70158, c3 = c1 + 1, t = clamp(x) - 1; return 1 + c3 * t * t * t + c1 * t * t }

var imageCache: [String: CGImage] = [:]
func image(_ path: String) -> CGImage? {
    if let cached = imageCache[path] { return cached }
    guard let ns = NSImage(contentsOfFile: path), let cg = ns.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return nil }
    imageCache[path] = cg
    return cg
}

func roundedFont(_ size: CGFloat, _ weight: NSFont.Weight = .heavy) -> NSFont {
    let base = NSFont.systemFont(ofSize: size, weight: weight)
    if let d = base.fontDescriptor.withDesign(.rounded), let f = NSFont(descriptor: d, size: size) { return f }
    return base
}
func styled(_ text: String, accent: String?, size: CGFloat, color: NSColor = .white, weight: NSFont.Weight = .heavy) -> NSAttributedString {
    let p = NSMutableParagraphStyle()
    p.alignment = .center
    p.lineHeightMultiple = 0.95
    let s = NSMutableAttributedString(string: text, attributes: [.font: roundedFont(size, weight), .foregroundColor: color, .paragraphStyle: p, .kern: -size * 0.01])
    if let a = accent, let r = text.range(of: a) { s.addAttribute(.foregroundColor, value: accentColor, range: NSRange(r, in: text)) }
    return s
}
func drawText(_ ctx: CGContext, _ s: NSAttributedString, centerY: CGFloat, scale: CGFloat = 1, alpha: CGFloat = 1, glow: Bool = true) {
    let maxW = W - 120
    let box = s.boundingRect(with: NSSize(width: maxW, height: 3000), options: [.usesLineFragmentOrigin, .usesFontLeading])
    let rect = NSRect(x: (W - maxW) / 2, y: H - centerY - box.height / 2, width: maxW, height: ceil(box.height) + 6)
    ctx.saveGState()
    ctx.setAlpha(alpha)
    ctx.translateBy(x: W / 2, y: H - centerY)
    ctx.scaleBy(x: scale, y: scale)
    ctx.translateBy(x: -W / 2, y: -(H - centerY))
    if glow { ctx.setShadow(offset: .zero, blur: 30, color: color(0x4263eb, 0.65)) }
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
    s.draw(with: rect, options: [.usesLineFragmentOrigin, .usesFontLeading])
    NSGraphicsContext.restoreGraphicsState()
    ctx.restoreGState()
}
func glow(_ ctx: CGContext, _ x: CGFloat, _ y: CGFloat, _ r: CGFloat, _ hex: UInt32, _ a: CGFloat) {
    let g = CGGradient(colorsSpace: sRGB, colors: [color(hex, a), color(hex, 0)] as CFArray, locations: [0, 1])!
    ctx.drawRadialGradient(g, startCenter: CGPoint(x: x, y: H - y), startRadius: 0, endCenter: CGPoint(x: x, y: H - y), endRadius: r, options: [])
}

// ---------- background: drifting glow and slowly rising stars ----------
var seed: UInt64 = 42
func rnd() -> CGFloat { seed = seed &* 6364136223846793005 &+ 1442695040888963407; return CGFloat(seed >> 33) / CGFloat(1 << 31) }
let stars = (0..<48).map { _ in (x: rnd() * W, y: rnd() * H, r: 1.5 + rnd() * 3, speed: 1 + rnd() * 2.5, phase: rnd() * 6.3) }
func background(_ ctx: CGContext, _ t: Double) {
    ctx.setFillColor(color(0x000000))
    ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
    let b = CGFloat(sin(t * 0.8)), c = CGFloat(cos(t * 0.6))
    glow(ctx, W * 0.4 + b * 50, H * 0.42 + c * 60, 1000 + b * 70, 0x4263eb, 0.42)
    glow(ctx, W * 0.66 - b * 60, H * 0.64 + c * 40, 820, 0x9c36b5, 0.28)
    glow(ctx, W * 0.3 + c * 40, H * 0.86, 620, 0x0ca678, 0.14)
    for s in stars {
        let a = 0.5 + 0.5 * sin(CGFloat(t) * s.speed + s.phase)
        var y = (s.y - CGFloat(t) * 16).truncatingRemainder(dividingBy: H)
        if y < 0 { y += H }
        ctx.setFillColor(color(0xffffff, 0.5 * a))
        ctx.fillEllipse(in: CGRect(x: s.x - s.r, y: H - y - s.r, width: s.r * 2, height: s.r * 2))
    }
}

// ---------- elements ----------
func popScale(_ t: Double, _ start: Double, from: Double = 0.45) -> CGFloat {
    CGFloat(from + (1 - from) * easeOutBack((t - start) / 0.42))
}
func fadeAlpha(_ t: Double, _ it: Item) -> CGFloat {
    CGFloat(min(clamp((t - it.start) / 0.12), clamp((it.end - t) / 0.14)))
}

var textCache: [String: NSAttributedString] = [:]
func cachedText(_ key: String, _ make: () -> NSAttributedString) -> NSAttributedString {
    if let s = textCache[key] { return s }
    let s = make()
    textCache[key] = s
    return s
}

func drawShot(_ ctx: CGContext, _ img: CGImage, _ area: CGRect, zoom: CGFloat, fx: CGFloat, fy: CGFloat, alpha: CGFloat) {
    let w = area.width * zoom, h = area.height * zoom
    let x = area.minX + area.width * fx - w * fx
    let top = area.maxY - area.height * fy + h * fy
    ctx.saveGState()
    ctx.clip(to: area)
    ctx.setAlpha(alpha)
    ctx.interpolationQuality = .high
    ctx.draw(img, in: CGRect(x: x, y: top - h, width: w, height: h))
    ctx.restoreGState()
}

func drawPhone(_ ctx: CGContext, _ it: Item, _ t: Double) {
    guard let screens = it.screens, !screens.isEmpty else { return }
    let shotH = CGFloat(it.height ?? 1214), shotW = shotH * 786 / 1704
    let statusH = shotW * 59 / 393, screenH = shotH + statusH, bezel: CGFloat = 18
    let enter = easeOutBack((t - it.start) / 0.6), leave = easeIn((t - (it.end - 0.3)) / 0.3)
    let cy = CGFloat(it.y ?? 0.6) * H + CGFloat(1 - enter) * H * 0.75 + CGFloat(sin(t * 1.7)) * 7 + CGFloat(leave) * H * 0.9
    let screen = CGRect(x: W / 2 - shotW / 2, y: H - cy - screenH / 2, width: shotW, height: screenH)
    let outer = screen.insetBy(dx: -bezel, dy: -bezel)

    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -24), blur: 70, color: color(0x000000, 0.85))
    ctx.addPath(CGPath(roundedRect: outer, cornerWidth: 92, cornerHeight: 92, transform: nil))
    ctx.setFillColor(color(0x0d0d0f))
    ctx.fillPath()
    ctx.restoreGState()
    ctx.addPath(CGPath(roundedRect: outer.insetBy(dx: 2, dy: 2), cornerWidth: 90, cornerHeight: 90, transform: nil))
    ctx.setStrokeColor(color(0x4a4a52))
    ctx.setLineWidth(4)
    ctx.strokePath()

    ctx.saveGState()
    ctx.addPath(CGPath(roundedRect: screen, cornerWidth: 74, cornerHeight: 74, transform: nil))
    ctx.clip()
    ctx.setFillColor(color(0x000000))
    ctx.fill(screen)
    let area = CGRect(x: screen.minX, y: screen.minY, width: shotW, height: shotH)
    var idx = 0
    for (k, s) in screens.enumerated() where t >= s.from { idx = k }
    func draw(_ k: Int, _ alpha: CGFloat, _ extra: CGFloat) {
        let s = screens[k]
        let until = k + 1 < screens.count ? screens[k + 1].from : it.end
        let p = easeInOut((t - s.from) / max(0.01, until - s.from))
        let zoom = CGFloat(s.zoom[0] + (s.zoom[1] - s.zoom[0]) * p) * extra
        let fx = CGFloat(s.focus[0] + (s.focus[2] - s.focus[0]) * p), fy = CGFloat(s.focus[1] + (s.focus[3] - s.focus[1]) * p)
        if let img = image(s.image) { drawShot(ctx, img, area, zoom: zoom, fx: fx, fy: fy, alpha: alpha) }
    }
    let since = t - screens[idx].from
    if idx > 0 && since < 0.25 {
        draw(idx - 1, 1, 1)
        draw(idx, CGFloat(easeOut(since / 0.25)), 1 + 0.05 * CGFloat(1 - easeOut(since / 0.25)))
    } else {
        draw(idx, 1, 1)
    }
    // status bar: time, signal and battery
    let bar = CGRect(x: screen.minX, y: screen.maxY - statusH, width: shotW, height: statusH)
    ctx.setFillColor(color(0x000000))
    ctx.fill(bar)
    let time = cachedText("time", { styled("9:41", accent: nil, size: statusH * 0.36, weight: .semibold) })
    let tb = time.size()
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
    time.draw(at: NSPoint(x: bar.minX + shotW * 0.17 - tb.width / 2, y: bar.midY - tb.height / 2))
    NSGraphicsContext.restoreGraphicsState()
    ctx.setFillColor(color(0xffffff))
    let rightX = bar.maxX - shotW * 0.2
    for k in 0..<4 {
        let h = statusH * (0.12 + 0.06 * CGFloat(k))
        ctx.fill(CGRect(x: rightX - 40 + CGFloat(k) * 9, y: bar.midY - statusH * 0.15, width: 6, height: h))
    }
    let batt = CGRect(x: rightX + 6, y: bar.midY - statusH * 0.12, width: statusH * 0.5, height: statusH * 0.24)
    ctx.addPath(CGPath(roundedRect: batt, cornerWidth: 5, cornerHeight: 5, transform: nil))
    ctx.setStrokeColor(color(0xffffff, 0.45))
    ctx.setLineWidth(2)
    ctx.strokePath()
    ctx.fill(batt.insetBy(dx: 3.5, dy: 3.5))
    ctx.restoreGState()
}

func drawLogo(_ ctx: CGContext, _ it: Item, _ t: Double) {
    guard let path = it.image, let img = image(path) else { return }
    let size = CGFloat(it.size ?? 360) * popScale(t, it.start, from: 0.3)
    let cy = CGFloat(it.y ?? 0.4) * H + CGFloat(sin(t * 2.2)) * 10
    glow(ctx, W / 2, cy, size * 1.25, 0x4263eb, 0.75 * fadeAlpha(t, it))
    ctx.saveGState()
    ctx.setAlpha(fadeAlpha(t, it))
    ctx.translateBy(x: W / 2, y: H - cy)
    ctx.rotate(by: CGFloat(sin(t * 1.6)) * 0.05)
    let r = CGRect(x: -size / 2, y: -size / 2, width: size, height: size)
    ctx.addPath(CGPath(roundedRect: r, cornerWidth: size * 0.23, cornerHeight: size * 0.23, transform: nil))
    ctx.clip()
    ctx.interpolationQuality = .high
    ctx.draw(img, in: r)
    ctx.restoreGState()
}

func drawPill(_ ctx: CGContext, _ it: Item, _ t: Double) {
    let size = CGFloat(it.size ?? 52)
    let s = cachedText("pill" + (it.text ?? ""), { styled(it.text ?? "", accent: nil, size: size, weight: .bold) })
    let ts = s.size(), scale = popScale(t, it.start, from: 0.6), alpha = fadeAlpha(t, it)
    let cy = CGFloat(it.y ?? 0.58) * H
    let rect = CGRect(x: W / 2 - ts.width / 2 - 44, y: H - cy - ts.height / 2 - 24, width: ts.width + 88, height: ts.height + 48)
    ctx.saveGState()
    ctx.setAlpha(alpha)
    ctx.translateBy(x: W / 2, y: H - cy)
    ctx.scaleBy(x: scale, y: scale)
    ctx.translateBy(x: -W / 2, y: -(H - cy))
    let path = CGPath(roundedRect: rect, cornerWidth: rect.height / 2, cornerHeight: rect.height / 2, transform: nil)
    ctx.addPath(path)
    ctx.setFillColor(color(0xffffff, 0.12))
    ctx.fillPath()
    ctx.addPath(path)
    ctx.setStrokeColor(color(0xb4c0ff, 0.7))
    ctx.setLineWidth(3)
    ctx.strokePath()
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
    s.draw(at: NSPoint(x: W / 2 - ts.width / 2, y: H - cy - ts.height / 2))
    NSGraphicsContext.restoreGraphicsState()
    ctx.restoreGState()
}

func drawFrame(_ ctx: CGContext, _ t: Double) {
    background(ctx, t)
    for it in spec.items where t >= it.start && t < it.end {
        let size = CGFloat(it.size ?? 80), y = CGFloat(it.y ?? 0.5) * H
        switch it.kind {
        case "phone": drawPhone(ctx, it, t)
        case "logo": drawLogo(ctx, it, t)
        case "pill": drawPill(ctx, it, t)
        case "big":
            let s = cachedText("big" + (it.text ?? "") + "\(size)", { styled(it.text ?? "", accent: it.accent, size: size) })
            drawText(ctx, s, centerY: y, scale: popScale(t, it.start), alpha: fadeAlpha(t, it))
        case "head":
            let s = cachedText("head" + (it.text ?? ""), { styled(it.text ?? "", accent: it.accent, size: size) })
            let slide = CGFloat(1 - easeOut((t - it.start) / 0.35)) * -40
            drawText(ctx, s, centerY: y + slide, scale: popScale(t, it.start, from: 0.75), alpha: fadeAlpha(t, it))
        case "sub":
            let s = cachedText("sub" + (it.text ?? ""), { styled(it.text ?? "", accent: it.accent, size: size, color: NSColor(srgbRed: 0.8, green: 0.81, blue: 0.87, alpha: 1), weight: .bold) })
            drawText(ctx, s, centerY: y, scale: popScale(t, it.start, from: 0.8), alpha: fadeAlpha(t, it), glow: false)
        case "flash":
            ctx.setFillColor(color(0xffffff, 0.45 * CGFloat(1 - clamp((t - it.start) / (it.end - it.start)))))
            ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
        default: break
        }
    }
}

func makeContext(_ data: UnsafeMutableRawPointer?, _ bytesPerRow: Int) -> CGContext {
    CGContext(data: data, width: spec.width, height: spec.height, bitsPerComponent: 8, bytesPerRow: bytesPerRow, space: sRGB,
              bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)!
}

// ---------- preview frames ----------
if args.count > 3 && args[2] == "--frames" {
    for t in args[3].split(separator: ",").compactMap({ Double($0) }) {
        let ctx = makeContext(nil, 0)
        drawFrame(ctx, t)
        let rep = NSBitmapImageRep(cgImage: ctx.makeImage()!)
        let url = URL(fileURLWithPath: spec.video.replacingOccurrences(of: "-silent.mp4", with: String(format: "-frame-%05.2f.png", t)))
        try! rep.representation(using: .png, properties: [:])!.write(to: url)
        print(url.path)
    }
    exit(0)
}

// ---------- video ----------
let videoURL = URL(fileURLWithPath: spec.video)
try? FileManager.default.removeItem(at: videoURL)
let writer = try! AVAssetWriter(outputURL: videoURL, fileType: .mp4)
let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: spec.width, AVVideoHeightKey: spec.height,
    AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 10_000_000, AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel, AVVideoMaxKeyFrameIntervalKey: 30],
])
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA, kCVPixelBufferWidthKey as String: spec.width,
    kCVPixelBufferHeightKey as String: spec.height, kCVPixelBufferCGBitmapContextCompatibilityKey as String: true,
])
writer.add(input)
writer.startWriting()
writer.startSession(atSourceTime: .zero)
let frames = Int((spec.duration * Double(spec.fps)).rounded(.up))
for f in 0..<frames {
    while !input.isReadyForMoreMediaData { usleep(2000) }
    var buffer: CVPixelBuffer?
    CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &buffer)
    guard let pb = buffer else { fatalError("no pixel buffer") }
    CVPixelBufferLockBaseAddress(pb, [])
    drawFrame(makeContext(CVPixelBufferGetBaseAddress(pb), CVPixelBufferGetBytesPerRow(pb)), Double(f) / Double(spec.fps))
    CVPixelBufferUnlockBaseAddress(pb, [])
    adaptor.append(pb, withPresentationTime: CMTime(value: Int64(f), timescale: Int32(spec.fps)))
}
input.markAsFinished()
let done = DispatchSemaphore(value: 0)
writer.finishWriting { done.signal() }
done.wait()

// ---------- add the soundtrack ----------
let comp = AVMutableComposition()
let vAsset = AVURLAsset(url: videoURL), aAsset = AVURLAsset(url: URL(fileURLWithPath: spec.audio))
let range = CMTimeRange(start: .zero, duration: vAsset.duration)
try! comp.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)!
    .insertTimeRange(range, of: vAsset.tracks(withMediaType: .video)[0], at: .zero)
if let a = aAsset.tracks(withMediaType: .audio).first {
    try! comp.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)!
        .insertTimeRange(CMTimeRange(start: .zero, duration: min(aAsset.duration, vAsset.duration)), of: a, at: .zero)
}
let outURL = URL(fileURLWithPath: spec.out)
try? FileManager.default.removeItem(at: outURL)
let export = AVAssetExportSession(asset: comp, presetName: AVAssetExportPresetHighestQuality)!
export.outputURL = outURL
export.outputFileType = .mp4
export.exportAsynchronously { done.signal() }
done.wait()
print(export.status == .completed ? "wrote \(outURL.path)" : "export failed: \(String(describing: export.error))")
