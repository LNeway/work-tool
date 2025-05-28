import argparse
from androguard.misc import AnalyzeAPK

def find_method_calls(apk_path, target_method):
    apk, dex, dx = AnalyzeAPK(apk_path)
    
    # 获取所有类和方法调用关系
    callers = []
    for cls in dx.get_classes():
        for method in cls.get_methods():
            # 检查该方法是否调用了目标方法
            for _, called_method, _ in method.get_xref_to():
                if called_method.name == target_method:
                    callers.append({
                        'class': cls.name,
                        'caller_method': method.name
                    })
                    break  # 每个方法只需记录一次
    
    return callers

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='APK方法调用分析工具')
    parser.add_argument('apk_path', help='APK文件路径')
    parser.add_argument('method', help='要查找的目标方法名（如 registerReceiver）')
    
    args = parser.parse_args()
    
    results = find_method_calls(args.apk_path, args.method)
    
    if results:
        print(f"调用 {args.method} 的类和方法：")
        for item in results:
            print(f"类：{item['class']}")
            print(f"调用方法：{item['caller_method']}\n")
    else:
        print("未找到相关调用")
