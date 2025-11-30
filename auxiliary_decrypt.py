import os
import sys
import zlib
import xxtea

# 预设的默认路径
DEFAULT_FILES = [
    r"D:\Download\tmp\jp.sunny.kanojo\files\bundleRes\bundle_file_list.dat",
    r"D:\Download\tmp\jp.sunny.kanojo\files\hotRes\protector.dat",
    r"D:\Download\tmp\jp.sunny.kanojo\files\hotRes\login_protector.dat"
]

KEY = b"\x24\xfa\x49\x9b\x10\x8d\x62\x59\x29\x26\x81\x67\x4b\xf7\x91\xeb"
HEADER_BYTES = b"\x0c\x07\x08\x0d\x0b\x09"

def get_user_input():
    print("=== 配置解密目标 ===")
    print("请输入要解密的文件路径 (多个文件用英文逗号 ',' 分隔)")
    print("直接按回车将使用默认的 3 个文件。")
    
    default_str = ",".join(DEFAULT_FILES)
    user_input = input(f"\n请输入路径:\n默认: {default_str}\n> ").strip()
    
    if not user_input:
        return DEFAULT_FILES
    
    # 处理用户输入的列表
    files = [f.strip() for f in user_input.split(',')]
    return files

def decrypt_specific_file(file_path):
    # 去除引号 (防止用户直接复制路径带引号)
    file_path = file_path.strip('"').strip("'")
    
    if not os.path.exists(file_path):
        print(f"[跳过] 文件不存在: {file_path}")
        return

    try:
        with open(file_path, "rb") as f:
            enc = f.read()

        header_len = len(HEADER_BYTES)
        if len(enc) <= header_len or enc[:header_len] != HEADER_BYTES:
            print(f"[错误] 文件头不匹配 (可能未加密): {os.path.basename(file_path)}")
            return
        
        ed = enc[header_len:]
        pad_len = (4 - (len(ed) % 4)) % 4
        data_to_decrypt = ed + b"\x00" * pad_len
        decrypted_raw = xxtea.decrypt(data_to_decrypt, KEY, padding=False)

        if not decrypted_raw:
            print(f"[错误] 解密失败: {file_path}")
            return

        try:
            decompressed_data = zlib.decompress(decrypted_raw[1:])
        except zlib.error as e:
            print(f"[错误] 解压失败: {e}")
            return

        # 保存
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        out_name = f"decrypted_{base_name}.txt"
        out_path = os.path.join(dir_name, out_name)

        with open(out_path, "wb") as f_out:
            f_out.write(decompressed_data)

        print(f"[成功] 已保存: {out_path}")

    except Exception as e:
        print(f"[异常] {e}")

if __name__ == "__main__":
    target_files = get_user_input()
    print("-" * 30)
    for file_path in target_files:
        decrypt_specific_file(file_path)
    input("\n按回车键退出...")