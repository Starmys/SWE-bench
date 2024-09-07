import json
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib_venn import venn2, venn3

# 假设json文件列表
json_files = ['./__mnt__teamdrive__model__DeepSeek-Coder-V2-Lite-Instruct.new_1.json', 
'./__mnt__teamdrive__model__DeepSeek-Coder-V2-Lite-Instruct.new_2.json',
'./__mnt__teamdrive__model__DeepSeek-Coder-V2-Lite-Instruct.new_3.json',
'./__mnt__teamdrive__model__DeepSeek-Coder-V2-Lite-Instruct.new_4.json',
'./__mnt__teamdrive__model__DeepSeek-Coder-V2-Lite-Instruct.new_5.json',
]  # 请替换为实际的文件名列表

# 初始化计数器
completed_counter = defaultdict(int)
resolved_counter = defaultdict(int)
error_counter = defaultdict(int)
empty_patch_counter = defaultdict(int)
incomplete_counter = defaultdict(int)

# 初始化每个json文件的resolved_ids和completed_ids集合
resolved_sets = [set() for _ in json_files]
completed_sets = [set() for _ in json_files]

# 遍历每个json文件
for i, file_name in enumerate(json_files):
    with open(file_name, 'r') as f:
        data = json.load(f)
    
    # 统计completed_ids
    for item in data.get('completed_ids', []):
        completed_counter[item] += 1
        completed_sets[i].add(item)
    
    # 统计resolved_ids
    for item in data.get('resolved_ids', []):
        resolved_counter[item] += 1
        resolved_sets[i].add(item)
    
    # 统计error_ids
    for item in data.get('error_ids', []):
        error_counter[item] += 1
    
    # 统计empty_patch_ids
    for item in data.get('empty_patch_ids', []):
        empty_patch_counter[item] += 1
    
    # 统计incomplete_ids
    for item in data.get('incomplete_ids', []):
        incomplete_counter[item] += 1

# 合并结果
all_items = set(completed_counter.keys()) | set(resolved_counter.keys()) | set(error_counter.keys()) | set(empty_patch_counter.keys()) | set(incomplete_counter.keys())
result = {}

for item in all_items:
    result[item] = {
        'completed_count': completed_counter[item],
        'resolved_count': resolved_counter[item],
        'error_count': error_counter[item],
        'empty_patch_count': empty_patch_counter[item],
        'incomplete_count': incomplete_counter[item]
    }

print("len(result):", len(result))

# 计算completed_count>=1的ids的数量和比例
completed_ids = [item for item, counts in result.items() if counts['completed_count'] >= 1]
completed_count = len(completed_ids)
completed_ratio = completed_count / len(result)
print(f"completed_count>=1的ids数量: {completed_count}")
print(f"completed_count>=1的ids比例: {completed_ratio:.2%}")

# 计算resolved_count>=1的ids的数量和比例
resolved_ids = [item for item, counts in result.items() if counts['resolved_count'] >= 1]
resolved_count = len(resolved_ids)
resolved_ratio = resolved_count / len(result)
print(f"resolved_count>=1的ids数量: {resolved_count}")
print(f"resolved_count>=1的ids比例: {resolved_ratio:.2%}")

# 绘制completed_count和resolved_count的分布图
completed_counts = [counts['completed_count'] for counts in result.values()]
resolved_counts = [counts['resolved_count'] for counts in result.values()]
plt.figure(figsize=(10, 6))

# 过滤掉数量为0的数据
completed_counts_nonzero = [count for count in completed_counts if count > 0]
resolved_counts_nonzero = [count for count in resolved_counts if count > 0]

# 绘制直方图
n_completed, bins_completed, patches_completed = plt.hist(completed_counts_nonzero, bins=20, alpha=0.5, label='Completed')
n_resolved, bins_resolved, patches_resolved = plt.hist(resolved_counts_nonzero, bins=20, alpha=0.5, label='Resolved')

# 添加数字标注
for i in range(len(n_completed)):
    if n_completed[i] > 0:
        plt.text(bins_completed[i], n_completed[i], f'{int(n_completed[i])}', ha='center', va='bottom')

for i in range(len(n_resolved)):
    if n_resolved[i] > 0:
        plt.text(bins_resolved[i], n_resolved[i], f'{int(n_resolved[i])}', ha='center', va='bottom')

plt.xlabel('计数')
plt.ylabel('频率')
plt.title('Completed和Resolved非零计数分布')
plt.legend()
plt.savefig('distribution.png')
plt.close()

print("非零计数分布图已保存为distribution.png")

# 创建resolved的重叠图（使用前三个JSON文件）
plt.figure(figsize=(10, 6))
venn3([set(resolved_sets[i]) for i in range(3)], set_labels=[f'JSON {i+1}' for i in range(3)])

plt.title('前三个JSON文件中Resolved IDs的重叠情况', fontsize=14)
plt.savefig('resolved_overlap.png', dpi=300, bbox_inches='tight')
plt.close()

print("Resolved重叠情况图已保存为resolved_overlap.png")

# 创建completed的重叠图（使用前两个JSON文件）
plt.figure(figsize=(10, 6))
venn2([set(completed_sets[i]) for i in range(2)], set_labels=[f'JSON {i+1}' for i in range(2)])

plt.title('前两个JSON文件中Completed IDs的重叠情况', fontsize=14)
plt.savefig('completed_overlap.png', dpi=300, bbox_inches='tight')
plt.close()

print("Completed重叠情况图已保存为completed_overlap.png")
