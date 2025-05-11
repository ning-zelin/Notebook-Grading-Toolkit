"""
Author: ning-zelin zl.ning@qq.com
Date: 2025-05-11
Description: 合并多个作业的评分结果并计算加权平均分数
"""

import os
import sys
import pandas as pd
import yaml
from glob import glob
import argparse

def load_configs(config_dir):
    """加载所有作业的配置文件"""
    config_files = glob(os.path.join(config_dir, "*.yaml"))
    configs = {}
    
    for config_file in config_files:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                # 使用文件名作为键（不含扩展名）
                config_name = os.path.splitext(os.path.basename(config_file))[0]
                configs[config_name] = config
        except Exception as e:
            print(f"Error loading config file {config_file}: {e}")
    
    return configs

def merge_scores(configs):
    """合并所有作业的评分结果"""
    merged_df = None
    
    for config_name, config in configs.items():
        output_dir = config.get("outputs_path", "")
        output_file = os.path.join(output_dir, f"评分结果_{config.get('output_id', '')}.xlsx")
        
        if not os.path.exists(output_file):
            print(f"Warning: Score file not found for {config_name}: {output_file}")
            continue
        
        try:
            df = pd.read_excel(output_file, dtype={"学号": str})
            df = df[["学号", "姓名", "分数", "评论"]]  # 只保留需要的列
            
            # 重命名分数和评论列，加上作业标识
            df = df.rename(columns={
                "分数": f"{config_name}_分数",
                "评论": f"{config_name}_评论"
            })
            
            # 添加权重列
            weight = config.get("weight", 1.0)
            df[f"{config_name}_权重"] = weight
            
            if merged_df is None:
                merged_df = df
            else:
                merged_df = pd.merge(merged_df, df, on=["学号", "姓名"], how="outer")
                
        except Exception as e:
            print(f"Error processing {output_file}: {e}")
    
    return merged_df

def calculate_final_scores(merged_df, configs):
    """计算加权平均分数和总评语"""
    if merged_df is None:
        return None
    
    # 获取所有分数列和权重列
    score_cols = [col for col in merged_df.columns if col.endswith("_分数")]
    weight_cols = [col for col in merged_df.columns if col.endswith("_权重")]
    comment_cols = [col for col in merged_df.columns if col.endswith("_评论")]
    
    # 计算加权平均分数
    weighted_scores = []
    for score_col, weight_col in zip(score_cols, weight_cols):
        score = merged_df[score_col].astype(float)
        weight = merged_df[weight_col]
        weighted_scores.append(score * weight)
    
    total_weight = merged_df[weight_cols].sum(axis=1)
    merged_df["分数"] = sum(weighted_scores) / total_weight
    
    # 生成结构化评语
    def generate_comment(row):
        comments = []
        for config_name in [col.replace("_评论", "") for col in comment_cols]:
            comment_col = f"{config_name}_评论"
            score_col = f"{config_name}_分数"
            weight_col = f"{config_name}_权重"
            if comment_col in merged_df.columns:
                comment = row[comment_col] if pd.notna(row[comment_col]) else ""
                score = row[score_col] if pd.notna(row[score_col]) else ""
                weight = row[weight_col] if pd.notna(row[weight_col]) else ""
                target = configs[config_name].get("target", config_name)
                comments.append(
                    f"{{target:{target}, 权重:{weight}, 分数:{score}, 评语:{comment}}}"
                )
        return ",".join(comments)
    
    merged_df["评语"] = merged_df.apply(generate_comment, axis=1)
    
    # 只保留需要的列
    final_cols = ["学号", "姓名", "分数", "评语"]
    return merged_df[final_cols]



def save_final_scores(final_df, output_dir):
    """保存最终评分结果"""
    if final_df is None:
        print("No data to save")
        return
    
    output_file = os.path.join(output_dir, "最终评分结果.xlsx")
    try:
        final_df.to_excel(output_file, index=False)
        print(f"Final scores saved to: {output_file}")
    except Exception as e:
        print(f"Error saving final scores: {e}")

def main():
    parser = argparse.ArgumentParser(description='Merge multiple homework scores')
    parser.add_argument('--config', help='Path to config directory', required=True)
    args = parser.parse_args()
    
    if not os.path.isdir(args.config):
        print(f"Error: Config directory not found: {args.config}")
        sys.exit(1)
    
    # 加载所有配置文件
    configs = load_configs(args.config)
    if not configs:
        print("No valid config files found")
        sys.exit(1)
    
    # 合并分数
    merged_df = merge_scores(configs)
    if merged_df is None:
        print("No score files found to merge")
        sys.exit(1)
    
    # 计算最终分数
    final_df = calculate_final_scores(merged_df, configs)
    
    # 保存结果到第一个作业的输出目录
    first_config = next(iter(configs.values()))
    output_dir = first_config.get("outputs_path", "")
    save_final_scores(final_df, output_dir)

if __name__ == "__main__":
    main()
