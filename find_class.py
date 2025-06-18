#!/usr/bin/env python3
import argparse
import sys
import re
import time
import concurrent.futures
import logging
import zipfile
import io
import traceback

# 尝试兼容不同版本的 Androguard
try:
    from androguard.misc import AnalyzeAPK
    from androguard.core.bytecodes.apk import APK
    from androguard.core.bytecodes.dvm import DalvikVMFormat
except ImportError:
    try:
        # 一些新版本可能没有 core.bytecodes
        from androguard.core.apk import APK
        from androguard.core.dex import DEX
    except ImportError:
        print("无法导入必要的 Androguard 模块")
        sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def get_dex_files(apk_path):
    """从APK中提取DEX文件而不使用Androguard的高级功能"""
    dex_files = {}
    try:
        with zipfile.ZipFile(apk_path, 'r') as z:
            for file_info in z.infolist():
                if file_info.filename.startswith('classes') and file_info.filename.endswith('.dex'):
                    logger.info(f"提取DEX文件: {file_info.filename}")
                    with z.open(file_info.filename) as dex_file:
                        dex_bytes = dex_file.read()
                    dex_files[file_info.filename] = dex_bytes
    except Exception as e:
        logger.error(f"提取DEX文件出错: {str(e)}")
    return dex_files

def process_dex_file(dex_bytes, class_pattern, dex_name):
    """处理单个DEX字节数据，查找匹配的类"""
    results = []
    try:
        # 首先尝试使用Androguard处理DEX
        try:
            from androguard.core.bytecodes.dvm import DalvikVMFormat
            dex = DalvikVMFormat(dex_bytes, using_api=27)
        except ImportError:
            logger.warning("无法导入 DalvikVMFormat, 尝试使用备选方法")
            from androguard.core.dex import DEX
            dex = DEX(dex_bytes)

        # 准备正则表达式模式
        escaped_pattern = re.escape(class_pattern)
        pattern = re.compile(escaped_pattern, re.IGNORECASE)

        # 遍历DEX中的所有类
        for cls in dex.get_classes():
            try:
                # 获取原始和点分格式的类名
                if hasattr(cls, 'get_name'):
                    raw_name = cls.get_name()  # Lcom/example/Class;
                elif hasattr(cls, 'name'):
                    raw_name = cls.name
                else:
                    continue

                dot_name = raw_name[1:-1].replace('/', '.')  # com.example.Class

                # 检查是否匹配模式
                if pattern.search(raw_name) or pattern.search(dot_name):
                    # 获取类的基本信息
                    class_info = {
                        'raw_name': raw_name,
                        'dot_name': dot_name,
                        'dex_name': dex_name,
                    }

                    # 添加访问权限
                    if hasattr(cls, 'get_access_flags'):
                        class_info['access_flags'] = cls.get_access_flags()
                    elif hasattr(cls, 'access_flags'):
                        class_info['access_flags'] = cls.access_flags
                    else:
                        class_info['access_flags'] = 0

                    # 添加方法数量
                    if hasattr(cls, 'get_methods'):
                        methods = cls.get_methods()
                        class_info['method_count'] = len(methods)
                    elif hasattr(cls, 'methods'):
                        class_info['method_count'] = len(cls.methods)
                    else:
                        class_info['method_count'] = 0

                    # 添加字段数量
                    if hasattr(cls, 'get_fields'):
                        class_info['field_count'] = len(cls.get_fields())
                    elif hasattr(cls, 'fields'):
                        class_info['field_count'] = len(cls.fields)
                    else:
                        class_info['field_count'] = 0

                    results.append(class_info)
            except Exception as e:
                logger.warning(f"处理类时出错: {str(e)}")
                continue

        return results
    except Exception as e:
        error_msg = f"处理 {dex_name} 时出错: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return []

def access_flags_to_string(access_flags):
    """将访问标志转换为可读字符串"""
    if isinstance(access_flags, str):
        return access_flags

    flags = []
    if access_flags & 0x1:
        flags.append("public")
    if access_flags & 0x2:
        flags.append("private")
    if access_flags & 0x4:
        flags.append("protected")
    if access_flags & 0x8:
        flags.append("static")
    if access_flags & 0x10:
        flags.append("final")
    if access_flags & 0x400:
        flags.append("abstract")
    if access_flags & 0x1000:
        flags.append("synthetic")
    if access_flags & 0x20000:
        flags.append("interface")

    return " ".join(flags) if flags else "unknown"

def find_specific_class(apk_path, class_pattern):
    """在APK中查找特定类 - 最大兼容版本"""
    logger.info(f"正在分析 APK: {apk_path}")
    logger.info(f"查找类模式: {class_pattern}")
    start_time = time.time()

    try:
        # 获取所有DEX文件
        dex_files = get_dex_files(apk_path)
        if not dex_files:
            logger.error("APK中没有找到DEX文件")
            return []

        logger.info(f"开始并行分析 {len(dex_files)} 个DEX文件...")
        total_found = 0

        # 多线程处理DEX文件
        all_results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 提交所有任务
            futures = []
            for dex_name, dex_bytes in dex_files.items():
                future = executor.submit(process_dex_file, dex_bytes, class_pattern, dex_name)
                futures.append((future, dex_name))

            # 等待任务完成并收集结果
            for future, dex_name in futures:
                try:
                    results = future.result()
                    if results:
                        all_results.extend(results)
                        found_count = len(results)
                        total_found += found_count
                        logger.info(f"在 {dex_name} 中找到 {found_count} 个匹配类")
                except Exception as e:
                    logger.error(f"处理 {dex_name} 的结果时出错: {str(e)}")

        elapsed = time.time() - start_time
        logger.info(f"分析完成，耗时 {elapsed:.2f} 秒")
        logger.info(f"总共找到 {total_found} 个匹配类")
        return all_results

    except Exception as e:
        logger.error(f"分析APK出错: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='APK特定类查找工具')
    parser.add_argument('apk', help='APK文件路径')
    parser.add_argument('-c', '--class', dest='class_name', required=True,
                        help='要查找的类名（支持部分匹配）')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细类信息')
    args = parser.parse_args()

    # 处理类名输入
    class_pattern = args.class_name
    # 处理特殊字符
    class_pattern = class_pattern.replace('$', r'\$')
    # 确保点号作为分隔符处理
    class_pattern = class_pattern.replace('.', r'\.')

    results = find_specific_class(args.apk, class_pattern)

    if not results:
        print(f"\n在 {args.apk} 中未找到匹配类: {args.class_name}")
        sys.exit(0)

    print(f"\n在 {args.apk} 中找到 {len(results)} 个匹配类:")
    print("=" * 90)

    for i, cls in enumerate(results, 1):
        access_str = access_flags_to_string(cls.get('access_flags', 0))

        print(f"匹配类 #{i}:")
        print(f"  Smali格式: {cls['raw_name']}")
        print(f"  Java格式: {cls['dot_name']}")
        print(f"  访问权限: {access_str}")
        print(f"  方法数量: {cls['method_count']}")
        print(f"  字段数量: {cls['field_count']}")
        print(f"  DEX文件: {cls['dex_name']}")
        print("-" * 90)

    # 如果启用详细模式，显示所有匹配类的列表
    if args.verbose:
        print("\n详细匹配类列表:")
        for cls in results:
            print(f"- {cls['dot_name']} (在 {cls['dex_name']})")

if __name__ == "__main__":
    print("APK类搜索工具 - 兼容版本 v1.1")
    main()