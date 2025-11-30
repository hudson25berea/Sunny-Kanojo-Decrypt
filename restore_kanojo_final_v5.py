import os
import zlib
import xxtea
import zipfile
import io
from tqdm import tqdm

# ================= 默认配置 =================
DEFAULT_SOURCE = r"D:\Download\tmp\jp.sunny.kanojo\files"
DEFAULT_OUTPUT = r"D:\Download\tmp\jp.sunny.kanojo\files\decrypted"
DEFAULT_PROTECTORS = [
    r"D:\Download\tmp\jp.sunny.kanojo\files\hotRes\decrypted_protector.dat.txt",
    r"D:\Download\tmp\jp.sunny.kanojo\files\hotRes\decrypted_login_protector.dat.txt"
]
DEFAULT_BUNDLE_LIST = r"D:\Download\tmp\jp.sunny.kanojo\files\bundleRes\decrypted_bundle_file_list.dat.txt"

# 密钥配置
KEY = b"\x24\xfa\x49\x9b\x10\x8d\x62\x59\x29\x26\x81\x67\x4b\xf7\x91\xeb"
HEADER_BYTES = b"\x0c\x07\x08\x0d\x0b\x09"
# ===========================================

def get_user_config():
    print("=== 智能还原配置 V5 (扁平化修复版) ===")
    print(f"\n[1] 原始资源目录 (Source):\n默认: {DEFAULT_SOURCE}")
    src = input("> ").strip().strip('"').strip("'") or DEFAULT_SOURCE

    print(f"\n[2] 还原输出目录 (Output):\n默认: {DEFAULT_OUTPUT}")
    out = input("> ").strip().strip('"').strip("'") or DEFAULT_OUTPUT

    print(f"\n[3] Protector 列表 (逗号分隔):")
    print(f"默认: {','.join(DEFAULT_PROTECTORS)}")
    prot_in = input("> ").strip()
    prot_list = [p.strip().strip('"').strip("'") for p in prot_in.split(',')] if prot_in else DEFAULT_PROTECTORS

    print(f"\n[4] Bundle List:\n默认: {DEFAULT_BUNDLE_LIST}")
    bun_list = input("> ").strip().strip('"').strip("'") or DEFAULT_BUNDLE_LIST

    return src, out, prot_list, bun_list

def load_mappings(prot_list, bundle_list):
    mapping = {}
    print("\n正在加载映射表 (忽略大小写)...")

    # 1. Bundle List (基础层)
    if os.path.exists(bundle_list):
        try:
            with open(bundle_list, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        # parts[-1] 是路径列表，取第一个
                        target_path = parts[-1].split(',')[0]
                        # Key = 纯 UUID 路径 (小写)
                        key = target_path.replace("\\", "/").lower()
                        mapping[key] = {
                            'type': 'bundle',
                            'real_name': target_path # BundleRes通常保留原有目录结构
                        }
        except: pass

    # 2. Protector List (覆盖层 - 拥有更好的文件名)
    for path in prot_list:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            # Key = 纯 UUID 路径 (小写)
                            key = parts[1].replace("\\", "/").lower()
                            mapping[key] = {
                                'type': 'protector',
                                'real_name': parts[0], # 这是短文件名，如 1.atlas
                                'orig_path': parts[1]
                            }
            except: pass

    print(f"映射表加载完成，共 {len(mapping)} 条记录")
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
    """
    生成不冲突的文件路径：
    如果有 1.png，则生成 1_2.png, 1_3.png
    彻底解决 UUID 目录过深的问题
    """
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    
    while True:
        full_path = os.path.join(base_dir, new_filename)
        # 如果文件不存在，或者文件大小一致(可能是同一个文件被多次映射)，则直接使用
        if not os.path.exists(full_path):
            return full_path
        
        # 文件存在，生成新名字
        counter += 1
        new_filename = f"{name}_{counter}{ext}"

def decrypt_and_save(file_path, mapping, source_root, output_root):
    try:
        if file_path.endswith(".txt") or file_path.endswith(".py"): return
        
        # 读取
        with open(file_path, "rb") as f:
            raw_data = f.read()
        
        # 解密
        final_data = smart_decrypt(raw_data)
        if not final_data: return

        # === 查找映射 ===
        rel_path = os.path.relpath(file_path, source_root).replace("\\", "/")
        
        # 提取 Key (去除 hotRes/ 前缀，转小写)
        parts = rel_path.split("/", 1)
        lookup_key = parts[1].lower() if len(parts) > 1 else rel_path.lower()

        # 查表
        info = mapping.get(lookup_key)
        # 如果查不到，尝试去掉后缀查
        if not info:
            base, _ = os.path.splitext(lookup_key)
            info = mapping.get(base)

        sub_folder = ""
        filename = ""

        if info:
            # === 已知文件 ===
            if info['type'] == 'protector':
                sub_folder = "hotRes"
                filename = info['real_name'] # 使用短名字 (AVG_8001_2.atlas)
            else:
                sub_folder = "bundleRes"
                filename = info['real_name'] # bundle通常包含部分路径
                if "." not in filename:
                    filename += guess_extension(final_data)
        else:
            # === 未知文件 ===
            sub_folder = "Unknown"
            ext = guess_extension(final_data)
            # 这里的 filename 依然可能是 UUID，但我们只取最后一段
            base_name = os.path.basename(rel_path)
            if base_name.endswith(ext):
                filename = base_name
            else:
                filename = base_name + ext

        # === 关键：扁平化处理 ===
        # 不再拼接 orig_path (UUID目录)，而是直接存到 sub_folder 下
        # bundleRes 有时自带多级目录，保留它的一级目录结构可能更好，
        # 但为了安全起见，这里对 hotRes 进行完全扁平化。
        
        final_dir = os.path.join(output_root, sub_folder)
        
        # 针对 bundleRes，如果 filename 包含斜杠，说明它本身就是路径，我们保留
        if "/" in filename:
            # 修正 Windows 路径
            filename = filename.replace("/", os.sep)
            final_path = os.path.join(final_dir, filename)
            # 确保目录存在
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
        else:
            # 针对 hotRes (Protector)，通常 filename 只是文件名
            # 使用自动重命名逻辑防止冲突
            os.makedirs(final_dir, exist_ok=True)
            final_path = get_unique_output_path(final_dir, filename)

        # 写入
        with open(final_path, "wb") as f:
            f.write(final_data)

    except Exception as e:
        # 只打印严重错误
        if "Bad zip" not in str(e):
            tqdm.write(f"[Error] {os.path.basename(file_path)}: {e}")

def main():
    src, out, prots, bun = get_user_config()
    if not os.path.exists(src):
        print("源目录不存在！")
        return
        
    full_map = load_mappings(prots, bun)

    files_to_proc = []
    # 扫描 bundleRes 和 hotRes
    for d in ["bundleRes", "hotRes"]:
        wd = os.path.join(src, d)
        if os.path.exists(wd):
            for r, _, fs in os.walk(wd):
                for f in fs:
                    files_to_proc.append(os.path.join(r, f))

    print(f"开始还原 {len(files_to_proc)} 个文件 (扁平化模式)...")
    for f in tqdm(files_to_proc, unit="file", ncols=80):
        decrypt_and_save(f, full_map, src, out)

    print(f"\n全部完成！")
    print(f"hotRes 文件在: {os.path.join(out, 'hotRes')}")
    print(f"bundleRes 文件在: {os.path.join(out, 'bundleRes')}")
    input("按回车键退出...")

if __name__ == "__main__":
    main()