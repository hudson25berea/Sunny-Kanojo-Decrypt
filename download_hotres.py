import os
import requests
import concurrent.futures
from tqdm import tqdm

# ================= 默认配置 =================
DEFAULT_MANIFESTS = [
    r"D:\Download\tmp\jp.sunny.kanojo\files\hotRes\hot_file_list.dat",
    r"D:\Download\tmp\jp.sunny.kanojo\files\bundleRes\decrypted_bundle_file_list.dat.txt"
]
DEFAULT_SAVE_ROOT = r"D:\Download\tmp\jp.sunny.kanojo\files"
DEFAULT_BASE_URL = "http://kanojo-jp-cdncf.y2sgames.com/kanojo-jp/1.0.1578/"    # 游戏更新后需要更新这个URL
# ===========================================

def get_user_config():
    print("=== 资源下载配置 (直接回车使用默认值) ===")
    
    # 1. 清单文件
    print("\n[1] 请输入下载清单路径 (多个用逗号分隔):")
    def_manifest_str = ",".join(DEFAULT_MANIFESTS)
    print(f"默认: {def_manifest_str}")
    user_manifests = input("> ").strip()
    
    manifest_files = []
    if not user_manifests:
        manifest_files = DEFAULT_MANIFESTS
    else:
        manifest_files = [f.strip().strip('"').strip("'") for f in user_manifests.split(',')]

    # 2. 保存目录
    print(f"\n[2] 请输入保存根目录:\n默认: {DEFAULT_SAVE_ROOT}")
    user_save = input("> ").strip().strip('"').strip("'")
    save_root = user_save if user_save else DEFAULT_SAVE_ROOT

    return manifest_files, save_root, DEFAULT_BASE_URL

def parse_manifest(manifest_path, save_root_base):
    tasks = []
    if not os.path.exists(manifest_path):
        print(f"[跳过] 找不到清单: {manifest_path}")
        return []

    # 自动判断子目录
    filename = os.path.basename(manifest_path).lower()
    sub_folder = "hotRes" if "hot" in filename else "bundleRes"

    print(f"读取清单: {filename} -> 目标: {sub_folder}")
    
    with open(manifest_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 6:
                file_hash = parts[0]
                try: file_size = int(parts[1])
                except: file_size = 0
                
                raw_path_str = parts[5]
                target_rel_path = raw_path_str.split(',')[0]
                full_rel_path = os.path.join(sub_folder, target_rel_path)
                
                tasks.append({
                    'hash': file_hash,
                    'size': file_size,
                    'rel_path': full_rel_path,
                    'save_root': save_root_base
                })
    return tasks

def download_file(task, base_url):
    url = base_url + task['hash']
    save_path = os.path.join(task['save_root'], task['rel_path'])
    
    if os.path.exists(save_path):
        local_size = os.path.getsize(save_path)
        if task['size'] > 0 and local_size == task['size']:
            return "skipped"
        elif task['size'] <= 0 and local_size > 0:
             return "skipped"

    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        resp = requests.get(url, stream=True, timeout=20)
        if resp.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return "success"
        elif resp.status_code == 404:
            return "404"
        return "error"
    except:
        return "error"

def main():
    manifests, save_root, base_url = get_user_config()
    
    all_tasks = []
    for m in manifests:
        all_tasks.extend(parse_manifest(m, save_root))

    total = len(all_tasks)
    print(f"\n共 {total} 个文件待处理。")
    if total == 0: return

    print("开始下载...")
    # 这里使用偏函数或者lambda传递 base_url
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as executor:
        futures = [executor.submit(download_file, task, base_url) for task in all_tasks]
        results = [f.result() for f in tqdm(concurrent.futures.as_completed(futures), total=total, unit="file", ncols=80)]

    print(f"\n下载完成！保存位置: {save_root}")
    input("按回车键退出...")

if __name__ == "__main__":
    main()