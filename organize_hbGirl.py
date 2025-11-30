import os
import shutil
import json
import re

def organize_files():
    # 获取当前脚本所在的目录
    current_dir = os.getcwd()
    
    # 扫描目录下所有的文件
    files = [f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f))]
    
    # 用于存储找到的基础名称 (例如: hbGirl_1001)
    basenames = set()
    
    # 正则表达式匹配文件名 (hbGirl_数字).后缀
    pattern = re.compile(r"^(hbGirl_\d+)\.(png|atlas|json)$")
    
    # 第一步：找出所有的基础名称
    for file in files:
        match = pattern.match(file)
        if match:
            basenames.add(match.group(1))
            
    if not basenames:
        print("未在当前目录下找到符合 'hbGirl_数字' 格式的文件。")
        return

    print(f"找到 {len(basenames)} 组文件，开始处理...")

    # 第二步：处理每一组文件
    for base_name in basenames:
        target_folder = os.path.join(current_dir, base_name)
        
        # 1. 创建文件夹 (如果不存在)
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
            print(f"创建文件夹: {base_name}")
        
        # 2. 移动三个主要文件 (.png, .atlas, .json)
        extensions = ['.png', '.atlas', '.json']
        for ext in extensions:
            file_name = f"{base_name}{ext}"
            src_path = os.path.join(current_dir, file_name)
            dst_path = os.path.join(target_folder, file_name)
            
            # 只有当源文件存在时才移动
            if os.path.exists(src_path):
                # 如果目标文件夹里已经有这个文件，先覆盖或跳过，这里选择移动并覆盖
                shutil.move(src_path, dst_path)
                print(f"  - 已移动: {file_name}")
        
        # 3. 生成 config.json 文件
        config_file_name = f"{base_name}.config.json"
        config_path = os.path.join(target_folder, config_file_name)
        
        # 构建字典
        config_data = {
            "conf_ver": 1,
            "type": 9,
            "controllers": {
                "param_hit": {},
                "param_loop": {},
                "key_trigger": {},
                "eye_blink": {
                    "min_interval": 500,
                    "max_interval": 6000
                },
                "lip_sync": {
                    "gain": 5.0
                },
                "mouse_tracking": {
                    "smooth_time": 0.15
                },
                "auto_breath": {},
                "extra_motion": {},
                "accelerometer": {},
                "intimacy_system": {},
                "slot_opacity": {},
                "slot_color": {}
            },
            "motions": {
                "idle": [
                    {
                        "file": "A" 
                    }
                ],
                "tap": [
                    {
                        "file": "A1"
                    }
                ]
            },
            "options": {
                "scale_factor": 0.2,
                "tex_type": 0,
                "edge_padding": False,
                "shader_type": 1
            },
            "skeleton": f"{base_name}.json",
            "atlases": [
                {
                    "atlas": f"{base_name}.atlas",
                    "tex_names": [
                        base_name
                    ],
                    "textures": [
                        f"{base_name}.png"
                    ]
                }
            ]
        }
        
        # 写入 json 文件
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"  - 已生成配置: {config_file_name}")

    print("\n所有操作已完成！")

if __name__ == "__main__":
    organize_files()
    input("按回车键退出...")