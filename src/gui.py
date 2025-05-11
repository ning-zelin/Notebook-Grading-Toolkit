"""
Author: ning-zelin zl.ning@qq.com
Date: 2025-03-07 12:23:00
LastEditors: ning-zelin zl.ning@qq.com
LastEditTime: 2025-05-11 10:00:00
Description: CV Grading System with PyQt5 UI.

Copyright (c) 2025 by ning-zelin zl.ning@qq.com, All Rights Reserved. 
"""

import os
import sys
import pandas as pd
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, QLabel, QPushButton, QLineEdit, QFileDialog, QTextBrowser, QSizePolicy)
import nbformat
# from nbconvert import HTMLExporter # Not strictly needed for current output extraction
import base64
import yaml 
from PyQt5.QtCore import Qt, QTimer
class GradingApp(QMainWindow):
    def __init__(self, config_path=None):
        super().__init__()
        # 如果通过命令行指定了config_path，则使用它，否则使用默认路径
        self.config_file_path = config_path
        
        # 检查配置文件是否存在
        if not os.path.exists(self.config_file_path):
            print(f"错误：配置文件 {self.config_file_path} 不存在")
            sys.exit(1)
            
        # 从yaml加载配置
        try:
            self.load_hw_config()
            self.output_dir = self.config.get("outputs_path")
            self.hw_dir = self.config.get("hw_path")
            output_id = self.config.get("output_id")
            self.output_file = os.path.join(self.output_dir, f"评分结果_{str(output_id)}.xlsx")
            
            os.makedirs(self.output_dir, exist_ok=True)
            
        except Exception as e:
            print(f"加载配置文件时出错: {str(e)}")
            sys.exit(1)
            
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        self.initUI()
        self.load_existing_scores()
        
        self.current_index = 0
        self.notebook_files = self.get_notebook_files()
        
        if self.notebook_files:
            # 查找第一个未批阅的学生
            self.find_first_unreviewed_student()
            self.load_notebook_by_index(self.current_index)
            self._set_controls_enabled(True)
            self._update_navigation_buttons_state()
        else:
            self.display_no_notebooks_state()
    def find_first_unreviewed_student(self):
        """查找第一个未批阅的学生并设置current_index"""
        for i, notebook_file in enumerate(self.notebook_files):
            student_name, student_id = self._extract_student_info(notebook_file)
            if student_id not in self.scores_df["学号"].values:
                self.current_index = i
                return
        # 如果所有学生都已批阅，保持current_index为0
        self.current_index = 0
    def load_hw_config(self):
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                self.target_string = self.config.get("target")
                if not self.target_string:
                    self.statusBar().showMessage("Warning: 'target' not found in hw_config.yaml.", 5000)
                else:
                    self.statusBar().showMessage(f"Loaded target string: '{self.target_string}' from config.", 3000)
        except FileNotFoundError:
            self.statusBar().showMessage(f"Error: Configuration file '{self.config_file_path}' not found.", 5000)
            self.target_string = None
            self.config = {}
        except Exception as e:
            self.statusBar().showMessage(f"Error loading config: {e}", 5000)
            self.target_string = None
            self.config = {}
    def initUI(self):
        self.setWindowTitle("CV TA GradingSystem")
        self.setGeometry(100, 100, 1200, 800)

        central_widget_layout = QHBoxLayout() # Main horizontal layout

        # Code Display (Left)
        self.code_display = QTextEdit()
        self.code_display.setReadOnly(True)
        self.code_display.setFixedWidth(600)
        
        # No explicit size policy needed here if using stretch factor,
        # QTextEdit defaults to Expanding/Expanding.

        # Output Display (Middle)
        self.output_display = QLabel("Output will be displayed here")
        self.output_display.setAlignment(Qt.AlignCenter)
        self.output_display.setWordWrap(True)
        self.output_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred) # Good for image scaling

        # Right Panel for controls
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget) # Vertical layout for controls

        # Populate right_panel_layout:
        self.student_nav_label = QLabel("Student: N/A")
        right_panel_layout.addWidget(self.student_nav_label) # Add label at the top

        # Navigation buttons
        nav_buttons_layout = QHBoxLayout()
        self.previous_button = QPushButton("Previous (Q)")
        self.previous_button.clicked.connect(self.navigate_previous)
        nav_buttons_layout.addWidget(self.previous_button)

        self.next_button = QPushButton("Next (E)")
        self.next_button.clicked.connect(self.navigate_next)
        nav_buttons_layout.addWidget(self.next_button)
        right_panel_layout.addLayout(nav_buttons_layout)

        self.score_input = QLineEdit()
        self.score_input.setPlaceholderText("Enter score here")
        right_panel_layout.addWidget(self.score_input)

        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("Enter comments here (optional)")
        self.comment_input.setFixedHeight(300) 
        right_panel_layout.addWidget(self.comment_input)

        self.call_ai_button = QPushButton("Call AI for Suggestions")
        self.call_ai_button.clicked.connect(self.call_ai)
        right_panel_layout.addWidget(self.call_ai_button)

        
        right_panel_layout.addStretch(1) # Pushes all controls in right_panel_layout upwards

        # Set a fixed width for the right panel
        # Adjust this value as needed for your content.
        right_panel_fixed_width = 320 
        right_panel_widget.setFixedWidth(right_panel_fixed_width)
        # Optional: Reinforce that it shouldn't expand horizontally.
        # right_panel_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)


        # Add widgets to the central_widget_layout with specified stretch factors:
        # Code display: 1 part of the space remaining after fixed right panel
        # Output display: 2 parts of the space remaining (will be the "middle rest")
        # Right panel: 0 stretch factor, as its width is fixed.
        central_widget_layout.addWidget(self.code_display, 1)
        central_widget_layout.addWidget(self.output_display, 2) 
        central_widget_layout.addWidget(right_panel_widget, 0)

        # Set the central widget
        container = QWidget()
        container.setLayout(central_widget_layout)
        self.setCentralWidget(container)
        
        self.statusBar()

    def _set_controls_enabled(self, enabled):
        self.score_input.setEnabled(enabled)
        self.comment_input.setEnabled(enabled)
        self.call_ai_button.setEnabled(enabled)
    def _update_navigation_buttons_state(self):
        if not self.notebook_files:
            self.previous_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return

        self.previous_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(True)

    def display_no_notebooks_state(self):
        self.code_display.setText(f"No notebook files found in '{self.hw_dir}' folder or folder is missing.")
        self.output_display.setText("")
        self.output_display.setPixmap(QPixmap())
        self.setWindowTitle("CV Grading System - No Notebooks")
        self.student_nav_label.setText("Student: N/A")
        self.score_input.clear()
        self.comment_input.clear()
        self._set_controls_enabled(False)
        self._update_navigation_buttons_state() # Also update nav buttons
        self.statusBar().showMessage(f"No notebooks loaded. Please check the '{self.hw_dir}' folder.")


    def load_existing_scores(self):
        try:
            if os.path.exists(self.output_file):
                self.scores_df = pd.read_excel(self.output_file, dtype={"学号": str})  
                # Ensure required columns exist
                expected_cols = ["学号", "姓名", "分数", "评论"]
                for col in expected_cols:
                    if col not in self.scores_df.columns:
                        self.scores_df[col] = "" # Add missing columns as empty strings or appropriate defaults
            else:
                self.scores_df = pd.DataFrame(columns=["学号", "姓名", "分数", "评论"])
        except Exception as e:
            self.scores_df = pd.DataFrame(columns=["学号", "姓名", "分数", "评论"])
            self.statusBar().showMessage(f"Error loading scores: {e}. Starting with empty scores.", 5000)


    def _extract_student_info(self, notebook_file_path):
        notebook_basename = os.path.basename(notebook_file_path)
        name_part = notebook_basename.split(".")[0] # Remove .ipynb
        parts = name_part.split("-")
        
        student_name = "Unknown"
        student_id = f"File_{name_part}" # Default ID if parsing fails

        if len(parts) >= 2: # Expected format: Name-ID or Name-ID-MoreInfo
            student_name = parts[0]
            student_id = parts[1]
        elif len(parts) == 1 and parts[0]: # Only one part, e.g., StudentID.ipynb or Name.ipynb
            # Heuristic: if it's all digits or common ID patterns, assume ID
            if parts[0].isalnum() and not parts[0].isalpha(): # Mix of num and alpha, or all num
                 student_id = parts[0]
                 student_name = parts[0] # Or keep "Unknown"
            else: # Assume it's a name or a single-word ID
                 student_name = parts[0]
                 student_id = parts[0]
        return student_name, str(student_id)
    def save_score_and_next(self): # Renamed method
        if not self.notebook_files or self.current_index >= len(self.notebook_files):
            self.statusBar().showMessage("No student selected or no notebooks loaded.")
            return

        notebook_file = self.notebook_files[self.current_index]
        student_name, student_id = self._extract_student_info(notebook_file)
        
        score_text = self.score_input.text().strip()
        comment = self.comment_input.toPlainText().strip()

        if not score_text:
            self.statusBar().showMessage("Score cannot be empty.")
            return
        
        try:
            float(score_text) 
        except ValueError:
            self.statusBar().showMessage("Invalid score. Please enter a number.")
            return

        existing_entry_mask = self.scores_df["学号"] == student_id
        
        if existing_entry_mask.any():
            idx_to_update = self.scores_df[existing_entry_mask].index[0]
            self.scores_df.loc[idx_to_update, "姓名"] = student_name
            self.scores_df.loc[idx_to_update, "分数"] = score_text
            self.scores_df.loc[idx_to_update, "评论"] = comment
            action_message = f"Score updated for {student_name}."
        else:
            new_row = pd.DataFrame([{
                "学号": student_id, 
                "姓名": student_name, 
                "分数": score_text, 
                "评论": comment
            }])
            self.scores_df = pd.concat([self.scores_df, new_row], ignore_index=True)
            action_message = f"Score saved for {student_name}."
        
        try:
            self.scores_df.to_excel(self.output_file, index=False)
            self.statusBar().showMessage(action_message)
            # Navigate to next student
            self.navigate_next(show_message_if_last=False) # Don't show "last student" message here
        except Exception as e:
            self.statusBar().showMessage(f"Error saving scores to Excel: {e}")



    def call_ai(self):
        student_code = self.code_display.toPlainText()
        if not student_code.strip():
            self.statusBar().showMessage("No code to grade.")
            return

        try:
            import openai
            from openai import OpenAI
            
            # 读取配置文件
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                system_prompt = config.get("system_prompt", "")
                question = config.get("question", "")
            
                ai_input = config.get("ai_input", 1)  # 默认为1:仅代码

            # 根据ai_input准备输入内容
            # 准备输入内容
            if ai_input == 1:  # 仅代码
                input_content = f"{question}\n\n学生代码:\n{student_code}"
            else:
                # 获取输出文本内容
                output_text = ""
                if hasattr(self.output_display, 'text'):  # 如果是QLabel
                    output_text = self.output_display.text()
                elif isinstance(self.output_display, QWidget):  # 如果是QWidget容器
                    # 查找容器中的QLabel
                    for child in self.output_display.findChildren(QLabel):
                        output_text = child.text()
                        break
                
                if ai_input == 2:  # 仅输出文本
                    input_content = f"{question}\n\n学生输出:\n{output_text}"
                else:  # 代码和输出文本
                    input_content = f"{question}\n\n学生代码:\n{student_code}\n\n学生输出:\n{output_text}"
            
            
            # 初始化客户端
            client = OpenAI(api_key=config.get("api_key"), base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
     
            # 清空评论框并显示"正在评估..."
            self.comment_input.clear()
            self.comment_input.setPlainText("正在评估...")
            self.comment_input.repaint()  # 强制立即更新UI
            
            # 流式请求
            full_response = ""
            stream = client.chat.completions.create(
                model=config.get("model_name"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_content}
                ],
                stream=True,
            )
            
            # 处理流式响应
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    part = chunk.choices[0].delta.content
                    full_response += part
                    # 实时更新评论框
                    self.comment_input.setPlainText(full_response)
                    self.comment_input.moveCursor(self.comment_input.textCursor().End)
                    self.comment_input.repaint()
                    QApplication.processEvents()  # 处理UI事件
            
            self.statusBar().showMessage("AI评估完成", 3000)
            
        except Exception as e:
            self.comment_input.setPlainText(f"AI评估失败: {str(e)}")
            self.statusBar().showMessage(f"调用AI API出错: {str(e)}", 5000)

    def get_notebook_files(self):
        if not os.path.isdir(self.hw_dir):
            self.statusBar().showMessage(f"'{self.hw_dir}' directory not found. Please create it and add notebooks.", 5000)
            return []
        
        files = [os.path.join(self.hw_dir, f) for f in os.listdir(self.hw_dir) if f.endswith(".ipynb") and not f.startswith('.~lock.')] # Ignore lock files
        if not files:
            self.statusBar().showMessage(f"No .ipynb files found in '{self.hw_dir}'.", 3000)
        return sorted(files) # Sort for consistent order

    def load_notebook_by_index(self, index):
        if not self.notebook_files or not (0 <= index < len(self.notebook_files)):
            # This case should ideally be prevented by disabling buttons/keys
            # but as a safeguard:
            if not self.notebook_files:
                self.display_no_notebooks_state()
            else: # Invalid index but files exist (e.g. end of list)
                self.statusBar().showMessage("No more notebooks in this direction.")
            return

        self.current_index = index # Ensure current_index is updated
        notebook_path = self.notebook_files[index]
        notebook_basename = os.path.basename(notebook_path)
        
        self.setWindowTitle(f"CV Grading System - {notebook_basename}")
        student_name, student_id = self._extract_student_info(notebook_path)
        self.student_nav_label.setText(f"Student: {student_name} ({student_id}) | File {index+1}/{len(self.notebook_files)}")

        self.code_display.clear()
        if hasattr(self.output_display, 'setText'):
            self.output_display.setText("")
            self.output_display.setPixmap(QPixmap())
        else:
            # If output_display is a QWidget, find and clear its QLabel children
            for child in self.output_display.findChildren(QLabel):
                child.setText("")
                child.setPixmap(QPixmap())

        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                notebook = nbformat.read(f, as_version=4)
        except Exception as e:
            self.code_display.setText(f"Error loading notebook: {notebook_basename}\n\n{str(e)}")
            self.statusBar().showMessage(f"Error reading {notebook_basename}", 3000)
            self.score_input.clear()
            self.comment_input.clear()
            return

        target_cell_found = False
        if not self.target_string:
            self.code_display.setText("Target string not loaded from config. Displaying all code cells.")
            all_code_cells = [cell['source'] for cell in notebook.cells if cell.cell_type == 'code']
            self.code_display.setText("\n\n# -------- New Cell --------\n\n".join(all_code_cells))
            # Optionally, display all outputs or first output of notebook here
            self.output_display.setText("Target string not loaded. Outputs for specific cell cannot be isolated.")
        else:
            for cell in notebook.cells:
                if cell.cell_type == 'code' and self.target_string in cell['source']:
                    self.code_display.setText(cell['source'])
                    target_cell_found = True
                    
                    # 提取该cell的所有输出
                    found_image_data = None
                    text_outputs = []
                    if 'outputs' in cell:
                        for output in cell['outputs']:
                            if found_image_data is None and output.output_type == 'display_data' and \
                               'data' in output and 'image/png' in output.data:
                                found_image_data = output.data['image/png']
                            
                            if output.output_type in ['stream', 'execute_result']:
                                if 'text' in output:
                                    text_outputs.append("".join(output.text))
                                elif 'data' in output and 'text/plain' in output.data:
                                    text_outputs.append("".join(output.data['text/plain']))
                    
                    # 创建输出文本
                    output_text = "\n".join(text_outputs) if text_outputs else "No text output"
                    output_text_size = len(output_text)
                    if output_text_size > 500:
                        output_text = f"(truncated {output_text_size - 500} characters)...\n" + output_text[output_text_size-500: output_text_size] 
                    
                    # 创建新的widget来同时显示图片和文本
                    output_widget = QWidget()
                    output_layout = QVBoxLayout(output_widget)
                    
                    # 如果有图片，添加图片
                    if found_image_data:
                        pixmap = QPixmap()
                        pixmap.loadFromData(base64.b64decode(found_image_data))
                        if not pixmap.isNull():
                            image_label = QLabel()
                            scaled_pixmap = pixmap.scaled(
                                1000, 
                                int(1000 * pixmap.height() / pixmap.width()),
                                Qt.KeepAspectRatio, 
                                Qt.SmoothTransformation
                            )
                            image_label.setPixmap(scaled_pixmap)
                            output_layout.addWidget(image_label)
                    
                    # 添加文本输出
                    text_label = QLabel(output_text)
                    text_label.setWordWrap(True)
                    output_layout.addWidget(text_label)
                    
                    # 清空并设置新的输出widget
                    self.output_display = output_widget
                    container = self.centralWidget()
                    container.layout().replaceWidget(container.layout().itemAt(1).widget(), self.output_display)
                    
                    break # 找到第一个匹配的cell后停止
            
            if not target_cell_found:
                self.code_display.setText(f"Target string '{self.target_string}' not found in any code cell of this notebook.")
                self.output_display.setText("")
                self.output_display.setPixmap(QPixmap())


        # Pre-fill score and comment if exists
        self.score_input.clear()
        self.comment_input.clear()
        
        existing_score_entry = self.scores_df[self.scores_df["学号"] == student_id]
        if not existing_score_entry.empty:
            score_val = existing_score_entry["分数"].iloc[0]
            comment_val = existing_score_entry["评论"].iloc[0]
            self.score_input.setText(str(score_val) if pd.notna(score_val) else "")
            self.comment_input.setPlainText(str(comment_val) if pd.notna(comment_val) else "")
            self.statusBar().showMessage(f"Loaded existing score for {student_name}.", 2000)
        else:
            self.statusBar().showMessage(f"Loaded {notebook_basename}. No prior score found.", 2000)
        
        self._update_navigation_buttons_state() # Update button states after loading

    def navigate_previous(self):
        if self.current_index > 0:
            # self.current_index -= 1 # Decrement is handled by load_notebook_by_index
            self.load_notebook_by_index(self.current_index - 1)
        else:
            self.statusBar().showMessage("Already at the first student.")
            self._update_navigation_buttons_state() # Ensure buttons are correct
    def save_current_score(self):
        """保存当前评分，返回是否成功"""
        if not self.notebook_files or self.current_index >= len(self.notebook_files):
            self.statusBar().showMessage("No student selected or no notebooks loaded.")
            return False

        notebook_file = self.notebook_files[self.current_index]
        student_name, student_id = self._extract_student_info(notebook_file)
        
        score_text = self.score_input.text().strip()
        comment = self.comment_input.toPlainText().strip()

        if not score_text:
            self.statusBar().showMessage("Score cannot be empty.")
            return False
        
        try:
            float(score_text) 
        except ValueError:
            self.statusBar().showMessage("Invalid score. Please enter a number.")
            return False

        # 先删除所有该学生的记录
        self.scores_df = self.scores_df[self.scores_df["学号"] != student_id]
        
        # 添加新记录
        new_row = pd.DataFrame([{
            "学号": str(student_id), 
            "姓名": student_name, 
            "分数": score_text, 
            "评论": comment
        }])
        self.scores_df = pd.concat([self.scores_df, new_row], ignore_index=True)
        
        try:
            # 保存前再次去重（防御性编程）
            self.scores_df.drop_duplicates(subset=["学号"], keep="last", inplace=True)
            self.scores_df.to_excel(self.output_file, index=False)
            self.statusBar().showMessage(f"Score saved for {student_name}.")
            return True
        except Exception as e:
            self.statusBar().showMessage(f"Error saving scores to Excel: {e}")
            return False

    def navigate_next(self, show_message_if_last=True):
        # 先保存当前评分
        if not self.save_current_score():
            return  # 如果保存失败则不跳转
            
        # 然后执行跳转逻辑
        if self.current_index < len(self.notebook_files) - 1:
            self.load_notebook_by_index(self.current_index + 1)
        else:
            self.statusBar().showMessage("Already at the last student. Existing" ,3000)
            QTimer.singleShot(2000, QApplication.instance().quit)  # 2秒后退出程序

    def keyPressEvent(self, event):
        if not self.notebook_files:
            super().keyPressEvent(event) # Pass to parent if no files to navigate
            return

        key = event.key()
        original_index = self.current_index

        if key == Qt.Key_Q:  # Previous student
            if self.current_index > 0:
                self.current_index -= 1
                self.load_notebook_by_index(self.current_index)
            else:
                self.statusBar().showMessage("Already at the first student.")
        elif key == Qt.Key_E:  # Next student
            if self.current_index < len(self.notebook_files) - 1:
                self.current_index += 1
                self.load_notebook_by_index(self.current_index)
            else:
                self.statusBar().showMessage("Already at the last student.")
        else:
            super().keyPressEvent(event) # Important for other key events

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to config file", default=None)
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    grading_app = GradingApp(config_path=args.config)
    grading_app.show()
    sys.exit(app.exec_())