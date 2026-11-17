// Gera theme/revivo/screenshot.png (1200x900) a partir da identidade visual.
// Uso: swift tools/make-screenshot.swift theme/revivo/screenshot.png
import AppKit

let out = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "theme/revivo/screenshot.png"
let W: CGFloat = 1200, H: CGFloat = 900
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(W), pixelsHigh: Int(H),
                           bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                           colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)

func rgb(_ hex: UInt32, _ a: CGFloat = 1) -> NSColor {
    NSColor(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255, alpha: a)
}
func fill(_ r: NSRect, _ c: NSColor, radius: CGFloat = 0) {
    c.setFill()
    if radius > 0 { NSBezierPath(roundedRect: r, xRadius: radius, yRadius: radius).fill() } else { r.fill() }
}
func text(_ s: String, _ r: NSRect, size: CGFloat, weight: NSFont.Weight = .regular, color: NSColor, align: NSTextAlignment = .left) {
    let p = NSMutableParagraphStyle(); p.alignment = align; p.lineHeightMultiple = 1.04
    let f = NSFont.systemFont(ofSize: size, weight: weight)
    (s as NSString).draw(in: r, withAttributes: [.font: f, .foregroundColor: color, .paragraphStyle: p])
}

let cream = rgb(0xF7F6F2), ink = rgb(0x14171B), ink2 = rgb(0x1C1F23), orange = rgb(0xF2611D),
    green = rgb(0x2E7D5B), line = rgb(0xE3E4DE), mut = rgb(0x5F6670), pale = rgb(0xFDE6D8)

fill(NSRect(x: 0, y: 0, width: W, height: H), cream)

// barra superior + header
fill(NSRect(x: 0, y: H - 34, width: W, height: 34), ink)
text("Projeto académico — a Revivo é uma loja fictícia, sem vendas nem pagamentos reais.",
     NSRect(x: 40, y: H - 27, width: 1000, height: 18), size: 12, color: rgb(0xCFD2D6))
fill(NSRect(x: 0, y: H - 120, width: W, height: 86), cream)
let headerLine = NSBezierPath()
headerLine.move(to: NSPoint(x: 0, y: H - 120)); headerLine.line(to: NSPoint(x: W, y: H - 120))
line.setStroke(); headerLine.lineWidth = 1; headerLine.stroke()

// logótipo (SVG da marca)
if let logo = NSImage(contentsOfFile: "design/brand/logo-horizontal.svg") {
    let lw: CGFloat = 168, lh = lw * logo.size.height / logo.size.width
    logo.draw(in: NSRect(x: 44, y: H - 100, width: lw, height: lh))
}
for (i, item) in ["Início", "Loja", "Serviços", "Projeto", "Inovação"].enumerated() {
    text(item, NSRect(x: 700 + CGFloat(i) * 78, y: H - 92, width: 70, height: 20), size: 15, weight: .semibold, color: ink2)
}
fill(NSRect(x: 1096, y: H - 100, width: 62, height: 34), orange, radius: 9)
text("Pedir", NSRect(x: 1104, y: H - 92, width: 50, height: 18), size: 13, weight: .bold, color: .white)

// hero escuro
let hero = NSRect(x: 0, y: 300, width: W, height: H - 420)
fill(hero, ink)
for x in stride(from: CGFloat(24), to: W, by: 44) {
    fill(NSRect(x: x, y: hero.minY, width: 1, height: hero.height), rgb(0xFFFFFF, 0.045))
}
for y in stride(from: hero.minY + 20, to: hero.maxY, by: 44) {
    fill(NSRect(x: 0, y: y, width: W, height: 1), rgb(0xFFFFFF, 0.045))
}
text("IMPRESSÃO 3D · ECONOMIA CIRCULAR", NSRect(x: 44, y: 640, width: 600, height: 22),
     size: 14, weight: .medium, color: orange)
text("Reparar em vez\nde substituir.", NSRect(x: 44, y: 470, width: 700, height: 160),
     size: 66, weight: .heavy, color: .white)
text("Peças impressas em 3D para dar vida nova a objetos que ainda funcionam.\nEnvie as medidas, receba um orçamento e nós imprimimos.",
     NSRect(x: 44, y: 390, width: 620, height: 70), size: 19, color: rgb(0xB9BEC4))
fill(NSRect(x: 44, y: 330, width: 176, height: 46), orange, radius: 10)
text("Pedir uma peça", NSRect(x: 60, y: 344, width: 160, height: 20), size: 15, weight: .bold, color: .white)
fill(NSRect(x: 240, y: 330, width: 168, height: 46), .clear, radius: 10)
let outline = NSBezierPath(roundedRect: NSRect(x: 240, y: 330, width: 168, height: 46), xRadius: 10, yRadius: 10)
rgb(0xFFFFFF, 0.35).setStroke(); outline.lineWidth = 2; outline.stroke()
text("Ver a loja", NSRect(x: 272, y: 344, width: 130, height: 20), size: 15, weight: .bold, color: .white)

// cartão de destaque no hero
fill(NSRect(x: 790, y: 360, width: 350, height: 270), rgb(0xFFFFFF, 0.04), radius: 22)
let circle = NSBezierPath(ovalIn: NSRect(x: 862, y: 430, width: 206, height: 206))
orange.setStroke(); circle.lineWidth = 26; circle.stroke()

// secção de cartões
fill(NSRect(x: 0, y: 0, width: W, height: 300), cream)
for i in 0..<3 {
    let x = 44 + CGFloat(i) * 380
    fill(NSRect(x: x, y: 96, width: 340, height: 160), .white, radius: 18)
    fill(NSRect(x: x, y: 96, width: 340, height: 160), line, radius: 18)
    fill(NSRect(x: x + 1, y: 97, width: 338, height: 158), .white, radius: 17)
    fill(NSRect(x: x + 22, y: 196, width: 46, height: 46), i == 1 ? rgb(0xDCEFE5) : pale, radius: 13)
    let dot = NSBezierPath(ovalIn: NSRect(x: x + 38, y: 212, width: 14, height: 14))
    (i == 1 ? green : orange).setFill(); dot.fill()
    text(["Envie as medidas", "Receba orçamento", "Imprimimos e enviamos"][i],
         NSRect(x: x + 22, y: 158, width: 290, height: 24), size: 19, weight: .bold, color: ink2)
    text(["Indique dimensões e material.", "Resposta em 24–48 horas.", "Entrega em Portugal."][i],
         NSRect(x: x + 22, y: 128, width: 290, height: 22), size: 14, color: mut)
}

NSGraphicsContext.restoreGraphicsState()
let png = rep.representation(using: .png, properties: [:])!
try! png.write(to: URL(fileURLWithPath: out))
print("screenshot: \(out) (\(Int(W))x\(Int(H)), \(png.count) bytes)")
