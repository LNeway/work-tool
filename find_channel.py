import os
import zipfile
import tempfile
import shutil
import re
from androguard.core.bytecodes.apk import APK
from androguard.core.bytecodes.dvm import DalvikVMFormat
from androguard.core.analysis.analysis import Analysis
from androguard.decompiler.dad import decompile

def analyze_apk_for_channel_mf(apk_path):
    """
    使用Androguard分析APK，查找读取channel.mf的类和方法
    
    Args:
        apk_path (str): APK文件路径
    """
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    print(f"使用临时目录: {temp_dir}")
    
    try:
        # 加载APK
        print("加载APK文件...")
        apk = APK(apk_path)
        
        # 获取DEX文件
        dex_files = []
        for dex_path in apk.get_dex_names():
            dex_data = apk.get_dex(dex_path)
            dex_files.append(dex_data)
        
        # 分析每个DEX文件
        results = {}
        for i, dex_data in enumerate(dex_files):
            print(f"\n分析DEX文件 #{i+1}...")
            dex_results = analyze_dex(dex_data, temp_dir)
            results.update(dex_results)
        
        # 输出结果
        print("\n=== 分析结果 ===")
        if results:
            print(f"找到 {len(results)} 个类的方法读取了 channel.mf:")
            for class_name, methods in results.items():
                print(f"\n类: {class_name}")
                print("方法:")
                for method in methods:
                    print(f"  - {method}")
        else:
            print("未找到读取 channel.mf 的类和方法")
            
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_ok=True)
        print(f"\n已清理临时目录: {temp_dir}")

def analyze_dex(dex_data, temp_dir):
    """
    分析单个DEX文件
    
    Args:
        dex_data (bytes): DEX文件数据
        temp_dir (str): 临时目录路径
        
    Returns:
        dict: 分析结果 {类名: [方法列表]}
    """
    results = {}
    
    try:
        # 创建DalvikVMFormat对象
        dvm = DalvikVMFormat(dex_data)
        
        # 创建分析对象
        dx = Analysis(dvm)
        dvm.set_vmanalysis(dx)
        dvm.set_decompiler(decompile.DvMachine())
        
        # 查找所有包含"channel.mf"字符串的引用
        channel_refs = []
        for string in dvm.get_strings():
            if "channel.mf" in string.get_unicode():
                channel_refs.append(string)
        
        if not channel_refs:
            print("未找到 channel.mf 字符串引用")
            return results
        
        print(f"找到 {len(channel_refs)} 个 channel.mf 字符串引用")
        
        # 查找引用这些字符串的方法
        for string_ref in channel_refs:
            # 获取引用该字符串的代码项
            for code_item in dvm.get_code_item():
                # 获取方法
                method = code_item.get_method()
                
                # 获取字节码
                bytecode = method.get_code().get_bc()
                
                # 检查字节码中是否引用了该字符串
                for inst in bytecode.get_instructions():
                    if inst.get_op_value() == 0x1a:  # const-string指令
                        string_id = inst.get_ref_kind()
                        if string_id == string_ref.get_idx():
                            # 找到引用该字符串的方法
                            class_name = method.get_class_name()[1:-1].replace('/', '.')
                            method_name = method.get_name()
                            
                            # 添加到结果
                            if class_name not in results:
                                results[class_name] = []
                            
                            if method_name not in results[class_name]:
                                results[class_name].append(method_name)
                            
                            # 尝试反编译方法获取更多上下文
                            try:
                                decompiled = method.get_source()
                                if decompiled:
                                    # 保存反编译代码用于分析
                                    analyze_decompiled_method(
                                        decompiled, 
                                        class_name, 
                                        method_name, 
                                        temp_dir
                                    )
                            except Exception:
                                pass
        
        return results
        
    except Exception as e:
        print(f"DEX分析错误: {e}")
        return results

def analyze_decompiled_method(decompiled_code, class_name, method_name, temp_dir):
    """
    分析反编译的方法代码，查找读取channel.mf的具体操作
    
    Args:
        decompiled_code (str): 反编译的Java代码
        class_name (str): 类名
        method_name (str): 方法名
        temp_dir (str): 临时目录路径
    """
    # 创建类目录
    class_dir = os.path.join(temp_dir, class_name.replace('.', '/'))
    os.makedirs(class_dir, exist_ok=True)
    
    # 保存反编译代码
    file_path = os.path.join(class_dir, f"{method_name}.java")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(decompiled_code)
    
    # 分析代码查找读取操作
    patterns = [
        r'new FileInputStream\("channel\.mf"\)',  # FileInputStream
        r'getResourceAsStream\("channel\.mf"\)',   # getResourceAsStream
        r'openAsset\("channel\.mf"\)',            # AssetManager
        r'openFileInput\("channel\.mf"\)',         # Context.openFileInput
        r'new File\("channel\.mf"\)',              # File对象
        r'\.load\("channel\.mf"\)'                # 各种load方法
    ]
    
    found = False
    for pattern in patterns:
        if re.search(pattern, decompiled_code):
            print(f"在 {class_name}.{method_name} 中找到可能的文件读取操作: {pattern}")
            found = True
    
    if not found:
        # 更深入的分析
        lines = decompiled_code.split('\n')
        for i, line in enumerate(lines):
            if "channel.mf" in line:
                # 提取上下文
                start = max(0, i-3)
                end = min(len(lines), i+4)
                context = '\n'.join(lines[start:end])
                
                print(f"在 {class_name}.{method_name} 中找到引用:")
                print(f"行 {i+1}: {line.strip()}")
                print("上下文:")
                print(context)
                print("-" * 50)

if __name__ == "__main__":
    apk_path = input("请输入APK文件路径: ").strip().strip('"')
    
    if not os.path.isfile(apk_path):
        print("文件不存在!")
        exit(1)
    
    # 检查androguard是否安装
    try:
        import androguard
    except ImportError:
        print("请先安装androguard: pip install androguard")
        exit(1)
    
    analyze_apk_for_channel_mf(apk_path)
