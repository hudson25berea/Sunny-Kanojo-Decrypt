import os
import zlib
import xxtea
import zipfile
import io
from tqdm import tqdm

# ================= 默认配置 =================
DEFAULT_SOURCE = r"D:\Download\tmp\jp.sunny.kanojo\files"
DEFAULT_OUTPUT = r"D:\Download\tmp\jp.sunny.kanojo\files\Restored_Assets"

# 这里默认把 login_protector 也加进去了
DEFAULT_PROTECTORS = [
    r"D:\Download\tmp\jp.sunny.kanojo\files\hotRes\decrypted_protector.dat.txt",
    r"D:\Download\tmp\jp.sunny.kanojo\files\hotRes\decrypted_login_protector.dat.txt"
]
DEFAULT_BUNDLE_LIST = r"D:\Download\tmp\jp.sunny.kanojo\files\bundleRes\decrypted_bundle_file_list.dat.txt"

KEY = b"\x24\xfa\x49\x9b\x10\x8d\x62\x59\x29\x26\x81\x67\x4b\xf7\x91\xeb"
HEADER_BYTES = b"\x0c\x07\x08\x0d\x0b\x09"
# ===========================================

def get_user_config():
    print("=== 智能还原配置 (直接回车使用默认值) ===")

    # 1. 源目录
    print(f"\n[1] 原始资源目录 (Source):\n默认: {DEFAULT_SOURCE}")
    src = input("> ").strip().strip('"').strip("'")
    src = src if src else DEFAULT_SOURCE

    # 2. 输出目录
    print(f"\n[2] 还原输出目录 (Output):\n默认: {DEFAULT_OUTPUT}")
    out = input("> ").strip().strip('"').strip("'")
    out = out if out else DEFAULT_OUTPUT

    # 3. Protector 列表
    print(f"\n[3] Protector 映射文件 (多个用逗号分隔):")
    def_prot_str = ",".join(DEFAULT_PROTECTORS)
    print(f"默认: {def_prot_str}")
    prot_in = input("> ").strip()
    if not prot_in:
        prot_list = DEFAULT_PROTECTORS
    else:
        prot_list = [p.strip().strip('"').strip("'") for p in prot_in.split(',')]

    # 4. Bundle List
    print(f"\n[4] Bundle List 映射文件:\n默认: {DEFAULT_BUNDLE_LIST}")
    bun_in = input("> ").strip().strip('"').strip("'")
    bun_list = bun_in if bun_in else DEFAULT_BUNDLE_LIST

    return src, out, prot_list, bun_list

def load_mappings(prot_list, bundle_list):
    mapping = {} 
    print("\n正在加载映射表...")

    # 加载 Protector (支持多个)
    for path in prot_list:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            # 统一格式: real_name | relative_path
                            key = f"hotRes/{parts[1]}".replace("\\", "/")
                            mapping[key] = {'type': 'protector', 'real_name': parts[0], 'orig_path': parts[1]}
            except: pass
    
    # 加载 Bundle List
    if os.path.exists(bundle_list):
        try:
            with open(bundle_list, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        key = f"bundleRes/{parts[0]}".replace("\\", "/")
                        mapping[key] = {'type': 'bundle', 'real_name': parts[-1]}
        except: pass
            
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
    # 2. ZIP
    if data.startswith(b'PK\x03\x04'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                return smart_decrypt(z.read(z.namelist()[0]))
        except: pass
    # 3. Raw
    return data

def decrypt_and_save(file_path, mapping, source_root, output_root):
    try:
        if file_path.endswith(".txt") or file_path.endswith(".py"): return
        with open(file_path, "rb") as f:
            final_data = smart_decrypt(f.read())
        
        if not final_data: return

        rel_path = os.path.relpath(file_path, source_root).replace("\\", "/")
        
        if rel_path in mapping:
            info = mapping[rel_path]
            if info['type'] == 'bundle':
                rname = info['real_name']
                if "." not in rname: rname += guess_extension(final_data)
                out_rel = os.path.join("bundleRes", rname)
            else:
                rname = info['real_name']
                out_rel = os.path.join("hotRes", os.path.dirname(info['orig_path']), rname)
        else:
            out_rel = rel_path + guess_extension(final_data)

        out_abs = os.path.join(output_root, out_rel)
        os.makedirs(os.path.dirname(out_abs), exist_ok=True)
        with open(out_abs, "wb") as f:
            f.write(final_data)
    except Exception as e:
        if "Bad zip" not in str(e): tqdm.write(f"Err: {e}")

def main():
    src, out, prots, bun = get_user_config()
    if not os.path.exists(src): return

    full_map = load_mappings(prots, bun)
    
    files_to_proc = []
    for d in ["bundleRes", "hotRes"]:
        wd = os.path.join(src, d)
        if os.path.exists(wd):
            for r, _, fs in os.walk(wd):
                for f in fs:
                    files_to_proc.append(os.path.join(r, f))
    
    print(f"开始还原 {len(files_to_proc)} 个文件...")
    for f in tqdm(files_to_proc, unit="file", ncols=80):
        decrypt_and_save(f, full_map, src, out)
    
    print(f"完成! 检查: {out}")
    input("按回车键退出...")

if __name__ == "__main__":
    main()