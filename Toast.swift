#!/usr/bin/env swift

import Cocoa
import AppKit

let app = NSApplication.shared
app.setActivationPolicy(.accessory)

guard CommandLine.arguments.count == 2 else {
    print("Usage: \(CommandLine.arguments[0]) <success|failure>")
    exit(1)
}


// 快速获取可执行文件路径
func getExecutablePath(_ executableName: String) -> String? {
    // 如果已经是绝对路径
    if executableName.hasPrefix("/") {
        return executableName
    }
    
    // 如果是相对路径
    if executableName.contains("/") {
        let currentDir = FileManager.default.currentDirectoryPath
        return currentDir + "/" + executableName
    }
    
    // 使用 which 命令（最快）
    let task = Process()
    task.executableURL = URL(fileURLWithPath: "/usr/bin/which")
    task.arguments = [executableName]
    
    let pipe = Pipe()
    task.standardOutput = pipe
    
    do {
        try task.run()
        task.waitUntilExit()
        
        if task.terminationStatus == 0 {
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8) {
                return output.trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }
    } catch {
        // which 失败时的后备方案
        return nil
    }
    
    return nil
}

let executableName = CommandLine.arguments[0]
guard let executablePath = getExecutablePath(executableName) else {
    print("❌ Could not find executable path")
    exit(1)
}


let status = CommandLine.arguments[1]
let message = status == "success" ? "编译完成" : "编译失败"
let androidToastColor = NSColor(calibratedRed: 0.33, green: 0.33, blue: 0.33, alpha: 0.88)
let textColor = NSColor.white // 保持白色文字
let window = NSWindow(
    contentRect: NSRect(x: 0, y: 0, width: 640, height: 480),
    styleMask: [.borderless],
    backing: .buffered,
    defer: false
)

window.level = .floating
window.isOpaque = false
window.backgroundColor = NSColor.clear
window.center()

let container = NSView(frame: window.contentView!.bounds)
container.wantsLayer = true
container.layer?.backgroundColor = androidToastColor.cgColor
container.layer?.cornerRadius = 14
container.layer?.masksToBounds = true

// 图标
let iconName = status == "success" ? "pass.png" : "fail.png"
let executableDirectory = (executablePath as NSString).deletingLastPathComponent
let iconPath = executableDirectory + "/" + iconName
let iconImage = NSImage(contentsOfFile: iconPath)
let iconImageView = NSImageView(frame: NSRect(x: 0, y: 0, width: 32, height: 32))
iconImageView.image = iconImage
iconImageView.imageScaling = .scaleProportionallyUpOrDown

// 标签 - 关键修复点
let label = NSTextField(labelWithString: message)
label.font = NSFont.systemFont(ofSize: 32, weight: .semibold)
label.textColor = textColor
label.alignment = .center

// **关键：让标签先计算自身大小**
label.sizeToFit()

let contentView = NSView()
contentView.translatesAutoresizingMaskIntoConstraints = false

contentView.addSubview(iconImageView)
contentView.addSubview(label)

let spacing: CGFloat = 12
let iconSize: CGFloat = 32
let labelWidth = label.frame.width  // 使用实际计算后的宽度
let labelHeight = label.frame.height // 使用实际高度
let totalWidth = iconSize + spacing + labelWidth
let totalHeight = max(iconSize, labelHeight) + 16 // **增加垂直内边距**

contentView.frame = NSRect(
    x: (container.bounds.width - totalWidth) / 2,
    y: (container.bounds.height - totalHeight) / 2,
    width: totalWidth,
    height: totalHeight
)

iconImageView.frame = NSRect(x: 0, y: (totalHeight - iconSize) / 2, width: iconSize, height: iconSize)
label.frame = NSRect(x: iconSize + spacing, y: (totalHeight - labelHeight) / 2, width: labelWidth, height: labelHeight)

container.addSubview(contentView)
window.contentView?.addSubview(container)

window.makeKeyAndOrderFront(nil)

NSAnimationContext.runAnimationGroup({ context in
    context.duration = 0.2
    window.alphaValue = 1
}, completionHandler: {
    DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
        NSAnimationContext.runAnimationGroup({ context in
            context.duration = 0.2
            window.alphaValue = 0
        }, completionHandler: {
            NSApp.terminate(nil)
        })
    }
})

app.run()