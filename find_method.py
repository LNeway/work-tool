import sys
import concurrent.futures
from queue import Queue
from androguard.misc import AnalyzeAPK

def process_dex(dex, dex_name, result_queue):
    """ 带DEX名称的多线程处理方法 """
    try:
        for cls in dex.get_classes():
            for method in cls.get_methods():
                if method.name == "onReceivedSslError":
                    result_queue.put( (cls.name, method, dex_name) )
    except Exception as e:
        print(f"DEX处理异常 [{dex_name}]: {str(e)}")

def find_ssl_error_handler(apk_path, max_workers=4):
    try:
        apk, dexes, analysis = AnalyzeAPK(apk_path)
        dex_names = apk.get_dex_names()  # 获取所有DEX文件名
        
        result_queue = Queue()
        found = False

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 为每个DEX提交处理任务，并携带DEX名称
            futures = []
            for dex, name in zip(dexes, dex_names):
                futures.append(
                    executor.submit(process_dex, dex, name, result_queue)
                )
            
            # 实时结果处理
            while not all(f.done() for f in futures):
                while not result_queue.empty():
                    cls_name, method, dex_file = result_queue.get()
                    print(f"Found in DEX: {dex_file}")
                    print(f"Class: {cls_name}")
                    print(f"Method: {method}")
                    print("=" * 50)
                    found = True

            concurrent.futures.wait(futures)

        if not found:
            print("No onReceivedSslError found in any DEX")

    except Exception as e:
        print(f"APK分析失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) not in [2,3]:
        print("Usage: python3 find_ssl_dex.py <APK_PATH> [THREADS]")
        sys.exit(1)
    
    apk_path = sys.argv[1]
    threads = int(sys.argv[2]) if len(sys.argv)>=3 else 4
    find_ssl_error_handler(apk_path, threads)
