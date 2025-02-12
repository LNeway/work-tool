#!/usr/bin/env swift

import Cocoa
import AppKit

// 显式创建应用实例
let app = NSApplication.shared
app.setActivationPolicy(.accessory) // 设置无 Dock 图标模式


// 参数检测
guard CommandLine.arguments.count == 2 else {
    print("Usage: \(CommandLine.arguments[0]) <success|failure>")
    exit(1)
}

let status = CommandLine.arguments[1]
let message = status == "success" ? "编译完成" : "编译失败"
let androidToastColor = NSColor(
    calibratedRed: 0.33,    // R
    green: 0.33,            // G
    blue: 0.33,             // B
    alpha: 0.9              // 90% 不透明度
)

let textColor = NSColor.white // 保持白色文字

// 创建窗口
let window = NSWindow(
    contentRect: NSRect(x: 0, y: 0, width: 480, height: 360),
    styleMask: [.borderless],
    backing: .buffered,
    defer: false
)

// 窗口配置
window.level = .floating
window.isOpaque = false
window.backgroundColor = NSColor.clear
window.center()

// 创建容器视图
let container = NSView(frame: window.contentView!.bounds)
container.wantsLayer = true
container.layer?.backgroundColor = androidToastColor.cgColor
label.textColor = textColor
container.layer?.cornerRadius = 14
container.layer?.masksToBounds = true

// 创建文字标签
let label = NSTextField(labelWithString: message)
label.font = NSFont.systemFont(ofSize: 32, weight: .semibold)
label.textColor = NSColor.white
label.alignment = .center

// 精确垂直居中设置
label.frame = CGRect(
    x: 0,
    y: (container.bounds.height - label.intrinsicContentSize.height) / 2 - 2, // 视觉补偿
    width: container.bounds.width,
    height: label.intrinsicContentSize.height
)
label.autoresizingMask = [.width, .maxYMargin, .minYMargin] // 自动居中适配


// 组合视图
container.addSubview(label)
window.contentView?.addSubview(container)

// 显示窗口
window.makeKeyAndOrderFront(nil)

// 设置动画定时器
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

// 启动应用
app.run()
