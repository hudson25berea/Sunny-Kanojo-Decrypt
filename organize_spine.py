import os
import shutil
import re
import json

def organize_spine_files():
    # 获取当前工作目录
    current_dir = os.getcwd()
    # 扫描所有文件
    all_files = [f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f))]

    # 1. 提取所有 spine ID
    spine_ids = set()
    for f in all_files:
        # 匹配 spine_XXX.json 来确定 ID
        match = re.match(r'^(spine_\d+)\.json$', f)
        if match:
            spine_ids.add(match.group(1))

    print(f"扫描到 Spine ID: {len(spine_ids)} 个")

    for spine_id in spine_ids:
        # 2. 检查核心三文件 (atlas, json, png) 是否齐全
        core_files = {
            'atlas': f"{spine_id}.atlas",
            'json': f"{spine_id}.json",
            'png': f"{spine_id}.png"
        }

        missing_core = False
        for f_name in core_files.values():
            if f_name not in all_files:
                missing_core = True
                break
        
        if missing_core:
            print(f"跳过 {spine_id}: 缺少核心文件")
            continue

        print(f"处理中: {spine_id} ...")
        
        # 创建同名文件夹
        target_folder = os.path.join(current_dir, spine_id)
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        # 3. 筛选并移动相关文件
        # 找出该 ID 的所有 MP3 (spine_XXX_1.mp3)
        related_mp3s = []
        for f in all_files:
            if f.startswith(f"{spine_id}_") and f.endswith(".mp3"):
                related_mp3s.append(f)
        
        # 按数字后缀排序 (1, 2, 3, 4...)
        related_mp3s.sort(key=lambda x: int(re.search(r'_(\d+)\.mp3', x).group(1)) if re.search(r'_(\d+)\.mp3', x) else 0)

        # 移动核心文件
        for f_name in core_files.values():
            src = os.path.join(current_dir, f_name)
            dst = os.path.join(target_folder, f_name)
            shutil.move(src, dst)

        # 移动 MP3 文件
        for mp3 in related_mp3s:
            src = os.path.join(current_dir, mp3)
            dst = os.path.join(target_folder, mp3)
            shutil.move(src, dst)

        # 4. 生成 config.json
        generate_config(target_folder, spine_id, related_mp3s)

    print("全部完成！")

def generate_config(folder_path, spine_id, mp3_list):
    # 初始化动作列表
    tap_actions = []
    start_actions = []

    for mp3 in mp3_list:
        # 提取文件名中的数字后缀，例如 spine_108_1.mp3 -> 1
        match = re.search(r'_(\d+)\.mp3$', mp3)
        if match:
            num = int(match.group(1))
            
            # === MP3 分类逻辑 ===
            # 1-3 分配给 tap (file: A1)
            # 4-6 (或更大) 分配给 start (file: in)
            if 1 <= num <= 3:
                tap_actions.append({
                    "file": "A1",
                    "sound": mp3
                })
            elif num >= 4:
                start_actions.append({
                    "file": "in",
                    "sound": mp3
                })

    # 构造完整的 JSON 数据
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
            "tap": tap_actions,
            "start": start_actions
        },
        "options": {
            "scale_factor": 0.2,
            "tex_type": 0,
            # "edge_padding": False, # 已根据你的最新JSON模板移除此项
            "shader_type": 1
        },
        "skeleton": f"{spine_id}.json",
        "atlases": [
            {
                "atlas": f"{spine_id}.atlas",
                "tex_names": [
                    spine_id
                ],
                "textures": [
                    f"{spine_id}.png"
                ]
            }
        ]
    }

    # 写入文件
    config_path = os.path.join(folder_path, "config.json")
    with open(config_path, 'w', encoding='utf-8') as json_file:
        json.dump(config_data, json_file, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    organize_spine_files()