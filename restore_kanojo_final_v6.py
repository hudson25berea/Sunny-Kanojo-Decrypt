import os
import zlib
import xxtea
import zipfile
import io
from tqdm import tqdm

# ================= 默认配置 =================
DEFAULT_SOURCE = r"D:\Download\tmp\jp.sunny.kanojo\files"
DEFAULT_OUTPUT = r"D:\Download\tmp\jp.sunny.kanojo\files\Restored_Assets"

# 这里预设了常用的映射表路径，根据实际情况修改
# 多个protector，把它们的路径都写在这里，或者在终端输入
DEFAULT_PROTECTORS = [
    r"D:\Download\tmp\jp.sunny.kanojo\files\hotRes\decrypted_protector.dat.txt",
    r"D:\Download\tmp\jp.sunny.kanojo\files\hotRes\decrypted_login_protector.dat.txt"
    # 如果有其他的 protector，继续往下列加
]
DEFAULT_BUNDLE_LIST = r"D:\Download\tmp\jp.sunny.kanojo\files\bundleRes\decrypted_bundle_file_list.dat.txt"

# 密钥配置
KEY = b"\x24\xfa\x49\x9b\x10\x8d\x62\x59\x29\x26\x81\x67\x4b\xf7\x91\xeb"
HEADER_BYTES = b"\x0c\x07\x08\x0d\x0b\x09"
# ===========================================

def get_user_config():
    print("=== 全量智能还原配置 V6 (通用扫描版) ===")
    print(f"\n[1] 原始资源目录 (Source) - 请指向从手机复制出来的 files 目录:")
    print(f"默认: {DEFAULT_SOURCE}")
    src = input("> ").strip().strip('"').strip("'") or DEFAULT_SOURCE

    print(f"\n[2] 还原输出目录 (Output):")
    print(f"默认: {DEFAULT_OUTPUT}")
    out = input("> ").strip().strip('"').strip("'") or DEFAULT_OUTPUT

    print(f"\n[3] Protector 列表 (如果有多个，请用英文逗号分隔):")
    print(f"默认: {','.join(DEFAULT_PROTECTORS)}")
    prot_in = input("> ").strip()
    prot_list = [p.strip().strip('"').strip("'") for p in prot_in.split(',')] if prot_in else DEFAULT_PROTECTORS

    print(f"\n[4] Bundle List:\n默认: {DEFAULT_BUNDLE_LIST}")
    bun_list = input("> ").strip().strip('"').strip("'") or DEFAULT_BUNDLE_LIST

    return src, out, prot_list, bun_list

def load_mappings(prot_list, bundle_list):
    mapping = {}
    print("\n正在加载映射表 (自动合并多个 Protector)...")

    # 1. Bundle List (基础层)
    if os.path.exists(bundle_list):
        try:
            with open(bundle_list, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        target_path = parts[-1].split(',')[0]
                        # Key = 纯 UUID 路径 (小写)
                        key = target_path.replace("\\", "/").lower()
                        mapping[key] = {
                            'type': 'bundle',
                            'real_name': target_path 
                        }
        except: pass

    # 2. Protector Lists (覆盖层)
    # 循环读取用户提供的每一个 protector 文件
    for path in prot_list:
        if os.path.exists(path):
            print(f"-> 读取: {os.path.basename(path)}")
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            # Key = 纯 UUID 路径 (小写)
                            key = parts[1].replace("\\", "/").lower()
                            mapping[key] = {
                                'type': 'protector',
                                'real_name': parts[0],
                                'orig_path': parts[1]
                            }
            except: pass
        else:
            print(f"-> [警告] 文件不存在: {path}")

    print(f"映射表加载完成，共合并 {len(mapping)} 条记录")
    return mapping

def guess_extension(data):
    if len(data) < 4: return '.dat'
    if data.startswith(b'UnityFS'): return '.unity3d'
    if data.startswith(b'\x89PNG'): return '.png'
    if data.startswith(b'FFD8FF'): return '.jpg'
    if data.startswith(b'OggS'): return '.ogg'
    if data.startswith(b'ID3') or data.startswith(b'\xff\xfb'): return '.mp3'
    if data.startswith(b'\x1bLua'): return '.luac'
    try:
        if b"size:" in data[:100] and b".png" in data[:100]: return ".atlas"
    except: pass
    return '.dat'

def smart_decrypt(data):
    if not data: return None
    # 1. XXTEA
    if len(data) > len(HEADER_BYTES) and data[:len(HEADER_BYTES)] == HEADER_BYTES:
        try:
            ed = data[len(HEADER_BYTES):]
            pad = (4 - (len(ed) % 4)) % 4
            dec = xxtea.decrypt(ed + b"\x00" * pad, KEY, padding=False)
            if dec: return zlib.decompress(dec[1:])
        except: pass
    # 2. ZIP (Nested)
    if data.startswith(b'PK\x03\x04'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                return smart_decrypt(z.read(z.namelist()[0]))
        except: pass
    # 3. Raw
    return data

def get_unique_output_path(base_dir, filename):
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while True:
        full_path = os.path.join(base_dir, new_filename)
        if not os.path.exists(full_path):
            return full_path
        counter += 1
        new_filename = f"{name}_{counter}{ext}"

def decrypt_and_save(file_path, mapping, source_root, output_root):
    try:
        if file_path.endswith(".txt") or file_path.endswith(".py"): return

        with open(file_path, "rb") as f:
            raw_data = f.read()

        final_data = smart_decrypt(raw_data)
        if not final_data: return

        # === 查找映射 ===
        rel_path = os.path.relpath(file_path, source_root).replace("\\", "/")
        
        # 尝试提取 Key (去除第一层目录前缀)
        parts = rel_path.split("/", 1)
        lookup_key = parts[1].lower() if len(parts) > 1 else rel_path.lower()
        
        info = mapping.get(lookup_key)
        # 再次尝试：直接用完整相对路径查（防止新文件夹结构不同）
        if not info:
             info = mapping.get(rel_path.lower())
        # 再次尝试：去掉后缀查
        if not info:
            base, _ = os.path.splitext(lookup_key)
            info = mapping.get(base)

        output_rel_path = ""

        if info:
            # === [命中] 已知文件 (还原名字) ===
            if info['type'] == 'protector':
                rname = info['real_name']
                # 放入 hotRes，并扁平化 (直接放 hotRes 根目录)
                output_rel_path = os.path.join("hotRes", rname)
            else:
                rname = info['real_name']
                if "." not in rname: rname += guess_extension(final_data)
                output_rel_path = os.path.join("bundleRes", rname)
        else:
            # === [未命中] 未知文件 (保留原目录结构) ===
            # V6 改进：不再强行归类到 Unknown，而是保留它在 source_root 下的相对位置
            
            ext = guess_extension(final_data)
            base_name = os.path.basename(file_path)
            
            # 修正文件名后缀
            if base_name.endswith(ext):
                final_name = base_name
            else:
                final_name = base_name + ext
            
            # 构建路径： output_root + 原相对目录 + 文件名
            # 例如: source/NewFolder/123 -> output/NewFolder/123.dat
            parent_dir = os.path.dirname(rel_path)
            output_rel_path = os.path.join(parent_dir, final_name)

        # === 写入处理 ===
        final_abs_path = os.path.join(output_root, output_rel_path)
        final_dir = os.path.dirname(final_abs_path)
        
        os.makedirs(final_dir, exist_ok=True)
        
        # 如果是 hotRes (扁平化区域)，需要防止重名
        if "hotRes" in output_rel_path and info and info['type'] == 'protector':
             final_abs_path = get_unique_output_path(final_dir, os.path.basename(output_rel_path))

        with open(final_abs_path, "wb") as f:
            f.write(final_data)

    except Exception as e:
        if "Bad zip" not in str(e): tqdm.write(f"[Error] {os.path.basename(file_path)}: {e}")

def main():
    src, out, prots, bun = get_user_config()
    if not os.path.exists(src):
        print("源目录不存在！")
        return

    full_map = load_mappings(prots, bun)

    print(f"开始全量扫描: {src} ...")
    files_to_proc = []
    
    # [V6 核心改动]：不再限制目录，扫描所有子文件夹
    for root, dirs, files in os.walk(src):
        for f in files:
            # 跳过脚本本身和解密出来的txt
            if f.endswith(".py") or f.endswith(".txt"): continue
            files_to_proc.append(os.path.join(root, f))

    print(f"共发现 {len(files_to_proc)} 个文件，开始还原...")
    
    for f in tqdm(files_to_proc, unit="file", ncols=80):
        decrypt_and_save(f, full_map, src, out)

    print(f"\n全部完成！")
    print(f"资源已输出至: {out}")
    input("按回车键退出...")

if __name__ == "__main__":
    main()