import os
cfg_dir = '/extp6/workspace/tmp/ai_ta/hw8/configs/hw2.yaml'
# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上一级目录
parent_dir = os.path.dirname(current_dir)
# 构建src目录路径
src_dir = os.path.join(parent_dir, 'src')

os.system(f'python3 {src_dir}/gui.py --config {cfg_dir}')