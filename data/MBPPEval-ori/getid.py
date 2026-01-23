import json
import re

# 把这里改成你的文件名
file_path = "mbpp-py.jsonl" 

# 1. 读取所有数据到内存
lines_to_write = []
with open(file_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        
        data = json.loads(line)
        
        # === 提取 ID 逻辑 ===
        # 从 "mbpp_762_..." 中提取 "762"
        match = re.search(r"mbpp_(\d+)", data.get("name", ""))
        if match:
            # 格式化为 EvalPlus 标准格式 "Mbpp/762"
            # 如果你只想要纯数字，就把 f"Mbpp/{...}" 改成 int(match.group(1))
            data['task_id'] = int(match.group(1))
        # ==================
        
        lines_to_write.append(json.dumps(data, ensure_ascii=False))

# 2. 直接覆盖写入原文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines_to_write) + '\n')

print("处理完成，原文件已修改。")