import json

def get_spine_animations(file_path):
    try:
        # 打开文件，注意指定 utf-8 编码以防中文路径或乱码
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 1. 检查是否存在 animations 字段
        if "animations" not in data:
            print("❌ 该文件中没有找到 'animations' 字段。")
            return []

        # 2. 获取 animations 字典下的所有 Key (即动作名称)
        # Spine 的结构是: "animations": { "动作名1": {...}, "动作名2": {...} }
        action_names = list(data["animations"].keys())
        
        return action_names

    except FileNotFoundError:
        print(f"❌ 找不到文件: {file_path}")
    except json.JSONDecodeError:
        print("❌ 文件格式错误：这似乎不是一个有效的 JSON 文件 (可能是二进制的 .skel？)")
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
    return []

# --- 使用方法 ---

# 文件路径
my_file_path = input("json文件：")

actions = get_spine_animations(my_file_path)

if actions:
    print(f"✅ 成功找到 {len(actions)} 个动作:")
    print("-" * 20)
    for action in actions:
        print(f" • {action}")