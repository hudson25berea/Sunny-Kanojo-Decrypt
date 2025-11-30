import os
import shutil
import json
import re

def get_config_content(model_id, variant_type):
    """
    根据变体类型（1 或 2）生成对应的 JSON 配置内容
    """
    base_name = f"AVG_{model_id}_{variant_type}"
    target_variant = "2" if variant_type == "1" else "1"
    target_config = f"AVG_{model_id}_{target_variant}.config.json"
    
    # 基础结构
    config = {
        "conf_ver": 1,
        "type": 9,
        "controllers": {
            "param_hit": {}, "param_loop": {}, "key_trigger": {},
            "eye_blink": { "min_interval": 500, "max_interval": 6000 },
            "lip_sync": { "gain": 5.0 },
            "mouse_tracking": { "smooth_time": 0.15 },
            "auto_breath": {}, "extra_motion": {}, "accelerometer": {},
            "intimacy_system": {}, "slot_opacity": {}, "slot_color": {}
        },
        "motions": {}, # 下面根据类型填充
        "options": {
            "scale_factor": 0.2,
            "position_y": -8.0,
            "tex_type": 0,
            "edge_padding": False,
            "shader_type": 1
        },
        "skeleton": f"{base_name}.json",
        "atlases": [
            {
                "atlas": f"{base_name}.atlas",
                "tex_names": [base_name],
                "textures": [f"{base_name}.png"]
            }
        ]
    }

    # 根据是 1 还是 2，填充 motions
    if variant_type == "1":
        # 变体 1：使用 in 音频，Tap 切换到 2
        config["motions"] = {
            "idle": [{"file": "A"}],
            "start": [
                {"name": "1", "sound": f"{model_id}_in1.mp3"},
                {"name": "2", "sound": f"{model_id}_in2.mp3"},
                {"name": "3", "sound": f"{model_id}_in3.mp3"}
            ],
            "tap": [
                {
                    "sound": f"{model_id}_in1.mp3",
                    "command": f"change_model {target_config}"
                }
            ]
        }
    else:
        # 变体 2：使用 act 音频，Tap 切换到 1
        config["motions"] = {
            "idle": [{"file": "A"}],
            "start": [
                {"name": "1", "sound": f"{model_id}_act1.mp3"},
                {"name": "2", "sound": f"{model_id}_act2.mp3"},
                {"name": "3", "sound": f"{model_id}_act3.mp3"}
            ],
            "tap": [
                {
                    # 变体2的示例中 Tap 没有 sound 字段，只有 command
                    "command": f"change_model {target_config}"
                }
            ]
        }
        
    return config

def organize_files():
    current_dir = os.getcwd()
    files = [f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f))]
    
    # 1. 扫描所有唯一的 ID (例如 8026)
    # 匹配 AVG_XXXX_Y
    model_pattern = re.compile(r"^AVG_(\d+)_(\d+)\.(atlas|json|png)$")
    unique_ids = set()
    
    for f in files:
        match = model_pattern.match(f)
        if match:
            unique_ids.add(match.group(1))
            
    if not unique_ids:
        print("未找到符合 AVG_XXXX_Y 格式的文件。")
        return

    print(f"找到 {len(unique_ids)} 个唯一ID，开始处理...")

    for model_id in unique_ids:
        # 预备目标文件夹名称，例如 AVG_8026
        target_folder_name = f"AVG_{model_id}"
        target_folder_path = os.path.join(current_dir, target_folder_name)
        
        files_to_move = []
        configs_to_generate = []
        
        # 检查变体 1 和 变体 2
        for variant in ["1", "2"]:
            base_name = f"AVG_{model_id}_{variant}"
            required_exts = [".atlas", ".json", ".png"]
            
            # 检查三件套是否齐全
            is_complete = True
            temp_files = []
            for ext in required_exts:
                fname = base_name + ext
                if os.path.exists(os.path.join(current_dir, fname)):
                    temp_files.append(fname)
                else:
                    is_complete = False
                    break
            
            if is_complete:
                # 如果三件套齐全，加入移动列表，并标记需要生成配置
                files_to_move.extend(temp_files)
                configs_to_generate.append(variant)
            else:
                # 如果不齐全，打印跳过信息（可选）
                pass

        # 如果没有任何模型文件要移动，就跳过这个ID，也不移动MP3
        if not files_to_move:
            continue

        # 查找该 ID 对应的所有 mp3 文件 (8026_*.mp3)
        mp3_prefix = f"{model_id}_"
        for f in files:
            if f.startswith(mp3_prefix) and f.lower().endswith(".mp3"):
                files_to_move.append(f)

        # --- 执行移动和生成 ---
        
        # 1. 创建文件夹
        if not os.path.exists(target_folder_path):
            os.makedirs(target_folder_path)
            print(f"处理 ID {model_id}: 创建文件夹 {target_folder_name}")
        
        # 2. 移动文件
        for fname in files_to_move:
            src = os.path.join(current_dir, fname)
            dst = os.path.join(target_folder_path, fname)
            try:
                shutil.move(src, dst)
            except Exception as e:
                print(f"  移动 {fname} 失败: {e}")

        # 3. 生成 Config 文件
        for variant in configs_to_generate:
            config_data = get_config_content(model_id, variant)
            config_filename = f"AVG_{model_id}_{variant}.config.json"
            config_path = os.path.join(target_folder_path, config_filename)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            print(f"  生成配置: {config_filename}")

    print("\n所有操作已完成！")

if __name__ == "__main__":
    organize_files()
    input("按回车键退出...")