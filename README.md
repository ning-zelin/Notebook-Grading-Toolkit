# CV GradingSystem

## 📜 Introduction

**CV GradingSystem** 是一个自动化作业/考试批改工具，可极大减轻助教的重复性劳动。

主要功能包括：
- 自动扫描作业文件夹，批量加载学生提交的 `.ipynb` 文件
- 提取包含指定关键字的代码单元及其输出（支持图片与文本）
- GUI界面支持学生切换与导航，支持快捷键操作
- 支持DeepSeek/Qwen自动评分以及手动调整
- 评分结果自动保存，便于后续统计与归档

页面示例： 

<div align="center">
<img src="./misc/image-20250511184449360.png" alt="image-20250511184657302" style="width:90%;">
</div>

## 🛠️ Installation

1. 申请[阿里云大模型接口](https://bailian.console.aliyun.com/?tab=home#/home)(目前有免费活动)，如果使用其他平台的API则需要修改`src/gui.py`的base_url部分

   ```python
   client = OpenAI(api_key=config.get("api_key"), base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
   ```

2. 配置yaml文件，例如：

   ```yaml
   api_key: your-api-key
   model_name: deepseek-v3 # DeepSeekV3使用体验较好，Qwen响应速度慢
   hw_path: /extp6/ai_ta/hw6/sutdent_summit
   outputs_path: /extp6/ai_ta/hw6/output
   system_prompt: |-
     You are a teaching assistant for a computer vision course,
     You are grading students' homework assignments,
     I will tell you the assignment questions and students' answers,
     Please evaluate whether the answers meet the following criteria,
     You can only answer "正确" or "有误", and a brief explanation if the answer is  "有误",
     You are not receiving complete code, so just focus on whether the logic is correct - don't worry about missing package imports or unimplemented functions,
     output format: {result:{} explanation:{}}, your answer should be in Chinese, and both field keys must be included (value can be left empty with spaces if your result is "正确"),
   output_id: 1
   question: "检查compute_sift_descriptors函数，SIFT的实现逻辑正确即可。判错条件：1. 实现的并不是SIFT描述子（给出解释哪里实现的不对）2. 直接调用OpenCV的SIFT函数(Sobel等函数允许调用)，回答尽可能简洁"
   target: "Homework 1" # ipynb文件中的作业标识符
   ```

   

3. 运行代码

   ```shell
   python3 src/gui.py --config your-yaml-path
   ```

