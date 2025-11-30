import os
import sys
import zlib
import xxtea
from tqdm import tqdm  # 必须先 pip install tqdm

# ================= 配置区域 =================

# 1. 游戏原始资源目录 (包含 hotRes 和 bundleRes 的那个 files 目录)
SOURCE_ROOT = r"D:\Download\tmp\jp.sunny.kanojo\files"

# 2. 输出目录
OUTPUT_ROOT = r"D:\Download\tmp\jp.sunny.kanojo\files\Restored_Assets"

# 3. 刚才解密出来的映射文件路径
PATH_BUNDLE_LIST_TXT = r"D:\Download\tmp\jp.sunny.kanojo\files\bundleRes\decrypted_bundle_file_list.dat.txt"
PATH_PROTECTOR_TXT = r"D:\Download\tmp\jp.sunny.kanojo\files\hotRes\decrypted_protector.dat.txt"

# ===========================================

KEY = b"\x24\xfa\x49\x9b\x10\x8d\x62\x59\x29\x26\x81\x67\x4b\xf7\x91\xeb"
HEADER_BYTES = b"\x0c\x07\x08\x0d\x0b\x09"

def load_mappings():
    """读取两个txt文件，构建文件名映射表"""
    mapping = {} 
    
    print("正在加载文件名映射表...")

    # 1. 解析 protector.dat
    if os.path.exists(PATH_PROTECTOR_TXT):
        try:
            with open(PATH_PROTECTOR_TXT, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        real_name = parts[0]
                        rel_path = parts[1]
                        key = f"hotRes/{rel_path}".replace("\\", "/")
                        mapping[key] = {
                            'type': 'protector',
                            'real_name': real_name,
                            'orig_path': rel_path
                        }
            print(f"-> 已加载 protector 映射: {len(mapping)} 条")
        except Exception as e:
            print(f"[Error] 加载 protector 失败: {e}")

    # 2. 解析 bundle_file_list.dat
    if os.path.exists(PATH_BUNDLE_LIST_TXT):
        count = 0
        try:
            with open(PATH_BUNDLE_LIST_TXT, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        hash_name = parts[0]
                        target_name = parts[-1]
                        key = f"bundleRes/{hash_name}".replace("\\", "/")
                        mapping[key] = {
                            'type': 'bundle',
                            'real_name': target_name
                        }
                        count += 1
            print(f"-> 已加载 bundle list 映射: {count} 条")
        except Exception as e:
            print(f"[Error] 加载 bundle list 失败: {e}")
            
    return mapping

def guess_extension(data):
    if data.startswith(b'UnityFS'): return '.unity3d'
    if data.startswith(b'\x89PNG'): return '.png'
    if data.startswith(b'FFD8FF'): return '.jpg'
    if data.startswith(b'OggS'): return '.ogg'
    if data.startswith(b'ID3') or data.startswith(b'\xff\xfb'): return '.mp3'
    if data.startswith(b'\x1bLua'): return '.luac'
    return '.dat'

def decrypt_and_save(file_path, mapping):
    try:
        # 排除非资源文件
        if file_path.endswith(".txt") or file_path.endswith(".py") or file_path.endswith(".bat"):
            return

        # 读取文件
        with open(file_path, "rb") as f:
            enc = f.read()

        header_len = len(HEADER_BYTES)
        
        # [修改] 关键逻辑变更：判断是否加密
        is_encrypted = False
        if len(enc) > header_len and enc[:header_len] == HEADER_BYTES:
            is_encrypted = True

        final_data = None

        if is_encrypted:
            # --- 分支 A: 加密文件 (执行解密 + 解压) ---
            ed = enc[header_len:]
            pad_len = (4 - (len(ed) % 4)) % 4
            decrypted_raw = xxtea.decrypt(ed + b"\x00" * pad_len, KEY, padding=False)
            
            if not decrypted_raw:
                tqdm.write(f"[Fail] XXTEA解密失败: {os.path.basename(file_path)}")
                return

            try:
                # Zlib 解压 (去掉第1个混淆字节)
                final_data = zlib.decompress(decrypted_raw[1:])
            except:
                # 极少数情况解压失败，但可能解密是对的？暂且跳过或保留
                tqdm.write(f"[Fail] Zlib解压失败: {os.path.basename(file_path)}")
                return
        else:
            # --- 分支 B: 未加密文件 (直接保留原数据) ---
            # [修改] 这就是找回那 2GB 数据的关键！
            final_data = enc

        if not final_data:
            return

        # ================== 路径处理 (逻辑不变) ==================
        rel_path = os.path.relpath(file_path, SOURCE_ROOT).replace("\\", "/")
        output_rel_path = ""
        
        # 1. 尝试从映射表还原名字
        if rel_path in mapping:
            info = mapping[rel_path]
            if info['type'] == 'bundle':
                real_name = info['real_name']
                if "." not in real_name:
                    real_name += guess_extension(final_data) # 使用解密后的数据猜后缀
                output_rel_path = os.path.join("bundleRes", real_name)
                
            elif info['type'] == 'protector':
                real_name = info['real_name']
                orig_path_dir = os.path.dirname(info['orig_path'])
                output_rel_path = os.path.join("hotRes", orig_path_dir, real_name)
        
        # 2. 不在映射表中，或者映射表也没覆盖到的文件
        else:
            # 使用 guess_extension 自动识别它是 mp3, png 还是 unity3d
            ext = guess_extension(final_data)
            output_rel_path = rel_path + ext

        # 写入文件
        final_out_path = os.path.join(OUTPUT_ROOT, output_rel_path)
        os.makedirs(os.path.dirname(final_out_path), exist_ok=True)
        
        with open(final_out_path, "wb") as f_out:
            f_out.write(final_data)

    except Exception as e:
        tqdm.write(f"[Error] 处理文件出错 {os.path.basename(file_path)}: {e}")

def main():
    if not os.path.exists(SOURCE_ROOT):
        print(f"源目录不存在: {SOURCE_ROOT}")
        return

    # 1. 加载映射表
    full_mapping = load_mappings()
    
    # 2. 收集所有待处理文件
    print("正在扫描文件列表...")
    target_files = []
    scan_dirs = ["bundleRes", "hotRes"]
    
    for d in scan_dirs:
        work_dir = os.path.join(SOURCE_ROOT, d)
        if not os.path.exists(work_dir):
            continue
        
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                target_files.append(os.path.join(root, file))
                
    total_files = len(target_files)
    print(f"共发现 {total_files} 个文件，开始解密还原...")
    
    # 3. 使用 tqdm 显示进度条进行处理
    # unit="file" 显示单位
    # ncols=100 固定宽度防止换行混乱
    for file_path in tqdm(target_files, total=total_files, unit="file", ncols=100):
        decrypt_and_save(file_path, full_mapping)

    print(f"\n全部完成！文件已保存至: {OUTPUT_ROOT}")

if __name__ == "__main__":
    main()