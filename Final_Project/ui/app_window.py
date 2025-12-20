import sys
import copy
import json
import os 
import traceback 
import time  
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QTabWidget, QLabel,
    QMessageBox, QLineEdit, QSplitter,
    QFileDialog, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Import modules đã phân chia
from core.scheduler import Scheduler
from ui.worker import GWOThread
from ui.components import GanttChartWidget, MetricsDisplayWidget, ScheduleGridDisplay

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🐺 GWOScheduler App 💰 - Hệ thống Tối ưu hóa Xếp lịch")
        self.setGeometry(100, 100, 1200, 800)
        
        self.scheduler: Scheduler = None 
        self.gwo_thread: GWOThread = None
        self.last_schedule_data: Dict[str, List[Dict[str, Any]]] = {}

        self.init_ui()
        
        self.load_json_btn.clicked.connect(self.load_json_file)
        self.run_baseline_btn.clicked.connect(lambda: self.run_optimization(is_gwo=False))
        self.run_gwo_btn.clicked.connect(lambda: self.run_optimization(is_gwo=True))

    def _show_message_box(self, title, text, icon_type):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon_type)
        # Apply custom style to QMessageBox (Giữ nguyên style)
        msg.setStyleSheet("""
            QMessageBox { background-color: #1f2733; color: #9cdafa; }
            QLabel { color: #9cdafa; }
            QPushButton { 
                background-color: #3f51b5; color: white; border: none; padding: 10px; min-width: 80px; 
                border-radius: 5px; 
            }
            QPushButton:hover { background-color: #5c6bc0; }
        """)
        msg.exec()

    def load_json_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Chọn File JSON Chứa Job Data", "", "JSON Files (*.json);;All Files (*)")
        
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    data_raw = f.read()
                
                first_brace = data_raw.find('{')
                if first_brace != -1:
                    data = data_raw[first_brace:].strip() 
                else:
                    first_bracket = data_raw.find('[')
                    if first_bracket != -1:
                        data = data_raw[first_bracket:].strip()
                    else:
                        raise json.JSONDecodeError("Không tìm thấy ký tự JSON bắt đầu ({ hoặc [).", data_raw, 0)
                
                json.loads(data)
                
                self.json_input.setText(data)
                self.gwo_log.append(f"✨ Tải file: '{os.path.basename(file_name)}' thành công. ✨")
            except json.JSONDecodeError as e: 
                self._show_message_box("Lỗi File", f"File được chọn không phải là JSON hợp lệ. Chi tiết lỗi: {e}", QMessageBox.Icon.Critical)
            except UnicodeDecodeError:
                 self._show_message_box("Lỗi File", "Lỗi mã hóa: File không ở định dạng UTF-8. Vui lòng chuyển đổi file sang UTF-8 và thử lại.", QMessageBox.Icon.Critical)
            except Exception as e:
                self._show_message_box("Lỗi File", f"Không thể đọc file: {e}", QMessageBox.Icon.Critical)
    
    
    
    def load_scheduler(self):
        try:
            data_text = self.json_input.toPlainText()
            if not data_text:
                raise ValueError("JSON Job Data Input trống.")

            data = json.loads(data_text)
            
            machines = int(self.machines_input.text())
            alpha = float(self.alpha_input.text())
            beta = float(self.beta_input.text())
            
            data['machines'] = machines
            data['alpha'] = alpha
            data['beta'] = beta
            
            if 'jobs' not in data or not isinstance(data['jobs'], list):
                data['jobs'] = [] 

            self.scheduler = Scheduler.from_dict(data) 
            return True
        except Exception as e:
            print(f"TRACEBACK LOAD SCHEDULER FAILED:\n{traceback.format_exc()}")
            self._show_message_box("Lỗi Input (Load Scheduler)", f"Không thể tải dữ liệu Scheduler hoặc tham số. Lỗi: {type(e).__name__}: {e}", QMessageBox.Icon.Critical)
            return False

    def run_optimization(self, is_gwo: bool):
        if not self.load_scheduler():
            return

        if is_gwo:
             baseline_obj_label = self.metrics_display.labels.get("baseline_objectiveValue", QLabel())
             if not baseline_obj_label.text() or baseline_obj_label.text() == '...':
                 self.run_optimization(is_gwo=False)
                 if not baseline_obj_label.text() or baseline_obj_label.text() == '...':
                     self._show_message_box("Cảnh báo", "Baseline cần được chạy thành công trước khi chạy GWO. Vui lòng kiểm tra Log lỗi Baseline.", QMessageBox.Icon.Warning)
                     return

        self.gwo_log.append("\n--- 🧹 DỌN DẸP SÂN KHẤU (CLEANING RESULTS) 🧹 ---")
        
        self.metrics_display.update_metrics(1, {k: None for k in ["makespan", "totalPenalty", "objectiveValue", "maxLateness", "executionTime"]})
        if not is_gwo:
            self.metrics_display.update_metrics(0, {k: None for k in ["makespan", "totalPenalty", "objectiveValue", "maxLateness", "executionTime"]})
        
        self.schedule_grid.display_schedule({}) 
        self.gantt_chart.set_schedule_data({})

        if not is_gwo:
            try:
                self.gwo_log.append("\n🚀 Bắt đầu Baseline (Greedy) ...")
                
                start_time = time.time() # <--- BẮT ĐẦU ĐO THỜI GIAN BASELINE

                sch_baseline = copy.deepcopy(self.scheduler) 
                
                sch_baseline.greedy_schedule() 
                metrics = sch_baseline.compute_metrics()

                end_time = time.time() # <--- KẾT THÚC ĐO THỜI GIAN BASELINE
                metrics['executionTime'] = end_time - start_time
                
                self.metrics_display.update_metrics(0, metrics)
                
                self.last_schedule_data = sch_baseline.schedule
                
                self.schedule_grid.display_schedule(self.last_schedule_data) 
                self.gantt_chart.set_schedule_data(self.last_schedule_data)
                self.output_tabs.setCurrentIndex(1) 
                
                self.gwo_log.append(f"\n✅ Baseline hoàn thành. Objective Value = {metrics['objectiveValue']:.2f}. Time = {metrics['executionTime']:.4f}s")
                self._show_message_box("Thành công Tuyệt vời", f"Baseline (Greedy) đã hoàn thành xuất sắc! Objective: {metrics['objectiveValue']:.2f}", QMessageBox.Icon.Information)
            except Exception as e:
                error_msg = f"Lỗi trong quá trình xếp lịch Baseline: {type(e).__name__}: {e}"
                print(f"TRACEBACK BASELINE FAILED:\n{traceback.format_exc()}")
                self._show_message_box("Lỗi Baseline (Logic Error)", error_msg, QMessageBox.Icon.Critical)
                self.gwo_log.append(f"\n❌ Baseline FAILED: {error_msg}")
        else:
            if self.gwo_thread and self.gwo_thread.isRunning():
                self._show_message_box("Cảnh báo", "GWO đang chạy. Vui lòng chờ hoặc khởi động lại ứng dụng.", QMessageBox.Icon.Warning)
                return

            try:
                pop_size = int(self.pop_size_input.text())
                max_iter = int(self.max_iter_input.text())
            except ValueError:
                self._show_message_box("Lỗi Tham số", "Pop Size và Max Iter phải là số nguyên.", QMessageBox.Icon.Critical)
                return
            
            self.gwo_log.append(f"\n🐺 Bắt đầu GWO Optimization. Pop Size={pop_size}, Max Iter={max_iter}...")
            self.run_gwo_btn.setEnabled(False)
            self.run_baseline_btn.setEnabled(False)
            
            self.gwo_thread = GWOThread(self.scheduler, pop_size, max_iter)
            self.gwo_thread.progress.connect(self.update_gwo_progress)
            self.gwo_thread.finished.connect(self.gwo_finished)
            self.gwo_thread.error.connect(self.gwo_error)
            self.gwo_thread.thread_done.connect(self.re_enable_buttons) 
            self.gwo_thread.start()

    def re_enable_buttons(self):
        self.run_gwo_btn.setEnabled(True)
        self.run_baseline_btn.setEnabled(True)

    def apply_styles(self):
        # --- QSS Style (Cyber Glam Dark Theme) - Đã Tăng Cường ---
        style = """
            QMainWindow { 
                background-color: #0d1117; 
            }
            QLabel { 
                color: #9cdafa; 
            }
            h3 {
                color: #ffc107; 
            }
            
            /* Inputs & Text Edits (Thêm hiệu ứng focus sặc sỡ) */
            QTextEdit, QLineEdit {
                background-color: #161b22; 
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 8px; 
                padding: 5px;
            }
            
            QLineEdit:focus, QTextEdit:focus {
                border: 3px solid qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff00ff, stop:1 #00ffff); /* Neon sặc sỡ */
            }
            
            /* Log Text Edit (Màu nền sặc sỡ hơn) */
            QTextEdit#GwoLog {
                background-color: #121a24;
                border: 2px solid #5e35b1; /* Tím */
                border-radius: 10px;
                color: #ffeb3b; /* Vàng neon cho log */
                font-size: 10pt;
            }

            /* Buttons (nhất - Nút RUN) */
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5e35b1, stop:1 #3f51b5); 
                color: white;
                border: 2px solid #673ab7;
                border-radius: 12px; 
                padding: 10px 20px;
                font-size: 11pt;
                font-weight: bold;
                box-shadow: 0 4px #4527a0; 
            }
            QPushButton:hover { 
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #673ab7, stop:1 #42a5f5); 
                border: 2px solid #9c27b0;
            }
            QPushButton:pressed {
                background-color: #4527a0;
                box-shadow: none; 
                margin-top: 4px;
                margin-bottom: -4px;
            }
            
            /* NÚT TẢI FILE JSON (Sửa theo yêu cầu: Nhỏ, chữ nhỏ, sặc sỡ) */
            QPushButton#LoadJsonButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff00ff, stop:1 #00ffff); /* Pink to Cyan gradient */
                color: #1f2733; /* Dark text */
                border: 2px solid #ff00ff;
                border-radius: 8px; /* Nhỏ hơn */
                padding: 5px 10px; /* Nhỏ hơn */
                font-size: 8pt; /* Chữ nhỏ hơn */
                font-weight: bold;
                box-shadow: 0 2px #cc00cc; 
            }
            QPushButton#LoadJsonButton:hover { 
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff66ff, stop:1 #66ffff); 
                border: 2px solid #ff66ff;
            }
            QPushButton#LoadJsonButton:pressed {
                background-color: #cc00cc;
                box-shadow: none; 
                margin-top: 2px;
                margin-bottom: -2px;
            }


            /* Tabs (Tăng cường đường viền sặc sỡ) */
            QTabWidget::pane { 
                border: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffea00, stop:1 #ff00ff); 
                background-color: #161b22; 
                border-radius: 10px;
                padding: 5px;
            }
            QTabBar::tab {
                background: #1f2733; 
                color: #9cdafa; 
                padding: 10px 20px;
                border: 1px solid #30363d; 
                border-bottom: none;
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected { 
                background: #161b22; 
                color: #ffeb3b; /* Vàng neon */
                border-top: 3px solid #ffeb3b; 
                border-left: 1px solid #ffeb3b;
                border-right: 1px solid #ffeb3b;
                font-weight: bold;
            }

            /* Group Boxes (Thêm GroupBox title gradient sặc sỡ) */
            QGroupBox {
                border: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1de9b6, stop:1 #ffc107); /* Xanh lá sang vàng */
                margin-top: 25px;
                padding-top: 10px; 
                color: #ffc107; 
                font-weight: bold;
                border-radius: 10px;
                background-color: #161b22;
            }
            QGroupBox::title {
                subcontrol-origin: margin; 
                subcontrol-position: top center; 
                padding: 5px 15px; 
                color: #0d1117; /* Text đen cho nổi */
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1de9b6, stop:1 #ffc107); 
                border-radius: 5px;
                font-size: 12pt;
            }
            
            QSplitter::handle { 
                background-color: #3f51b5; 
                width: 5px;
            }
        """ 
        self.setStyleSheet(style)

    def init_ui(self):
        self.apply_styles()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # THÊM BANNER TIÊU ĐỀ (Đã tăng cường)
        title_label = QLabel("✨ CHƯƠNG TRÌNH XẾP LỊCH TỐI ƯU 36 ✨")
        title_font = QFont("Arial", 16, QFont.Weight.Black)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Sử dụng gradient rực rỡ hơn cho tiêu đề
        title_label.setStyleSheet("QLabel { background-color: #263238; color: #ffeb3b; padding: 10px; border-radius: 10px; border: 3px solid qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff9800, stop:1 #ff00ff); margin-bottom: 10px; }")
        main_layout.addWidget(title_label)

        # 1. BUTTONS
        button_group = QWidget()
        button_layout = QHBoxLayout(button_group)
        button_layout.setContentsMargins(0, 0, 0, 0)
        self.run_baseline_btn = QPushButton("👑 1. RUN BASELINE (Greedy) 🚀")
        self.run_gwo_btn = QPushButton("💰 2. RUN GWO OPTIMIZATION 🐺")
        button_layout.addWidget(self.run_baseline_btn)
        button_layout.addWidget(self.run_gwo_btn)
        main_layout.addWidget(button_group) 

        # 2. CONFIG PARAMS
        config_container = QWidget()
        config_layout_main = QHBoxLayout(config_container)
        config_layout_main.setContentsMargins(0, 0, 0, 0)
        
        # SCHEDULER PARAMS
        scheduler_group = QGroupBox("PARAMETERS ⚙️")
        scheduler_layout = QHBoxLayout(scheduler_group)
        scheduler_layout.setContentsMargins(10, 20, 10, 10)
        self._add_config_field(scheduler_layout, "Machines (m):", "machines_input", "5", 50)
        self._add_config_field(scheduler_layout, "Alpha (Makespan):", "alpha_input", "1.0", 50)
        self._add_config_field(scheduler_layout, "Beta (Penalty):", "beta_input", "3.0", 50)
        scheduler_layout.addStretch(1)

        # GWO PARAMS
        gwo_group = QGroupBox("GWO OPTIMIZATION 📈")
        gwo_layout = QHBoxLayout(gwo_group)
        gwo_layout.setContentsMargins(10, 20, 10, 10)
        self._add_config_field(gwo_layout, "Pop Size:", "pop_size_input", "10", 50)
        self._add_config_field(gwo_layout, "Max Iter:", "max_iter_input", "20", 50)
        gwo_layout.addStretch(1)
        
        config_layout_main.addWidget(scheduler_group)
        config_layout_main.addWidget(gwo_group)
        main_layout.addWidget(config_container) 
        
        # 3. SPLITTER 
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setSizes([300, 700]) 
        
        # 3.1 INPUT WIDGET (JSON)
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_header_layout = QHBoxLayout()
        
        input_header_layout.setContentsMargins(0, 0, 0, 5) 
        
        input_header_layout.addWidget(QLabel("<h3>📜 JSON Job Data Input:</h3>"))
        
        # SỬA LỖI VÀ CHỈNH SỬA NÚT FILE JSON (Nhỏ hơn và sặc sỡ hơn)
        self.load_json_btn = QPushButton("📁 Tải File JSON")
        self.load_json_btn.setObjectName("LoadJsonButton") # Dùng Object Name để style riêng
        self.load_json_btn.setFixedWidth(120) # Làm nút nhỏ lại
        
        input_header_layout.addWidget(self.load_json_btn)
        input_layout.addLayout(input_header_layout)
        
        self.json_input = QTextEdit()
        self.json_input.setText(json.dumps(self.get_sample_data(), indent=4))
        input_layout.addWidget(self.json_input)
        splitter.addWidget(input_widget)

        # 3.2 OUTPUT WIDGET (TABS)
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(QLabel("<h3>📊 BẢNG KẾT QUẢ VÀ LOGS:</h3>"))
        
        self.output_tabs = QTabWidget() 
        
        # TAB 1: METRICS AND GWO LOG
        metrics_log_widget = QWidget()
        metrics_log_layout = QVBoxLayout(metrics_log_widget)
        metrics_log_layout.setContentsMargins(5, 5, 5, 5)
        metrics_log_layout.addWidget(QLabel("So sánh Chỉ số Quan trọng:"))
        self.metrics_display = MetricsDisplayWidget()
        metrics_log_layout.addWidget(self.metrics_display)
        
        self.gwo_log = QTextEdit("✨ GWO Log: Tiến trình sẽ hiển thị tại đây... ✨\n\nKiểm tra Log (Console) nếu chương trình bị crash để xem thông báo lỗi chi tiết nhất.")
        self.gwo_log.setReadOnly(True)
        self.gwo_log.setObjectName("GwoLog") # Dùng Object Name để style riêng
        metrics_log_layout.addWidget(QLabel("Tiến trình Thuật toán:"))
        metrics_log_layout.addWidget(self.gwo_log)
        self.output_tabs.addTab(metrics_log_widget, "💰 Metrics & Log 📈")

        # TAB 2: SCHEDULE OUTPUT (GRID + GANTT)
        schedule_widget = QWidget()
        schedule_layout = QVBoxLayout(schedule_widget)
        schedule_layout.setContentsMargins(5, 5, 5, 5)

        schedule_layout.addWidget(QLabel("Lịch trình dạng Biểu đồ Gantt (Thời gian là Vàng): "))
        self.gantt_chart = GanttChartWidget()
        schedule_layout.addWidget(self.gantt_chart)
        
        schedule_layout.addWidget(QLabel("Lịch trình Chi tiết (Bảng Lưới Lấp Lánh):"))
        self.schedule_grid = ScheduleGridDisplay() 
        schedule_layout.addWidget(self.schedule_grid)
        
        self.output_tabs.addTab(schedule_widget, "⚙️ Schedule Output 📊")
        
        output_layout.addWidget(self.output_tabs) 
        splitter.addWidget(output_widget)
        
        main_layout.addWidget(splitter, 1) 
        
    def _add_config_field(self, layout, label_text, attr_name, default_value, width):
        field_container = QWidget()
        field_layout = QHBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(5)
        
        label = QLabel(label_text)
        label.setMinimumWidth(120 if "Alpha" in label_text or "Beta" in label_text else 80)
        
        line_edit = QLineEdit(default_value)
        line_edit.setFixedWidth(width)
        setattr(self, attr_name, line_edit)
        
        field_layout.addWidget(label)
        field_layout.addWidget(line_edit)
        
        layout.addWidget(field_container)

    def get_sample_data(self):
        # Dữ liệu mẫu đã được giữ nguyên
        return {
            "machines": 5,
            "alpha": 1.0,
            "beta": 3.0,
            "jobs": [
                {"id": 1, "p": 6, "d": 30, "w": 10.0, "r": 0, "preds": []},
                {"id": 2, "p": 7, "d": 36, "w": 11.0, "r": 0, "preds": [1]},
                {"id": 3, "p": 8, "d": 44, "w": 12.0, "r": 2, "preds": [2]},
                {"id": 4, "p": 5, "d": 50, "w": 13.0, "r": 4, "preds": [3]},
                {"id": 5, "p": 6, "d": 56, "w": 14.0, "r": 6, "preds": [4]},
                {"id": 6, "p": 7, "d": 64, "w": 15.0, "r": 8, "preds": [5]},
                {"id": 7, "p": 4, "d": 68, "w": 16.0, "r": 10, "preds": [6]},
                {"id": 8, "p": 5, "d": 72, "w": 17.0, "r": 12, "preds": [7]},
                {"id": 9, "p": 6, "d": 78, "w": 18.0, "r": 14, "preds": [8]},
                {"id": 10, "p": 9, "d": 88, "w": 19.0, "r": 16, "preds": [9]},

                {"id": 11, "p": 4, "d": 35, "w": 5.0, "r": 0, "preds": [1]},
                {"id": 12, "p": 5, "d": 40, "w": 5.5, "r": 0, "preds": [1]},
                {"id": 13, "p": 4, "d": 45, "w": 6.0, "r": 2, "preds": [2]},
                {"id": 14, "p": 5, "d": 50, "w": 6.5, "r": 2, "preds": [2]},
                {"id": 15, "p": 3, "d": 55, "w": 7.0, "r": 4, "preds": [3]},
                {"id": 16, "p": 4, "d": 60, "w": 7.5, "r": 4, "preds": [3]},
                {"id": 17, "p": 5, "d": 65, "w": 8.0, "r": 6, "preds": [4]},
                {"id": 18, "p": 6, "d": 70, "w": 8.5, "r": 6, "preds": [4]},
                {"id": 19, "p": 7, "d": 75, "w": 9.0, "r": 8, "preds": [5]},
                {"id": 20, "p": 8, "d": 80, "w": 9.5, "r": 8, "preds": [5]},

                {"id": 21, "p": 15, "d": 90, "w": 0.5, "r": 0, "preds": []},
                {"id": 22, "p": 18, "d": 95, "w": 0.6, "r": 0, "preds": []},
                {"id": 23, "p": 6, "d": 55, "w": 8.0, "r": 10, "preds": [11, 13, 21]},
                {"id": 24, "p": 7, "d": 60, "w": 8.5, "r": 12, "preds": [12, 14, 22]},
                {"id": 25, "p": 8, "d": 65, "w": 9.0, "r": 14, "preds": [15, 17, 23]},
                {"id": 26, "p": 9, "d": 70, "w": 9.5, "r": 16, "preds": [16, 18, 24]},
                {"id": 27, "p": 5, "d": 75, "w": 10.5, "r": 18, "preds": [19, 25]},
                {"id": 28, "p": 4, "d": 80, "w": 11.5, "r": 20, "preds": [20, 26]},
                {"id": 29, "p": 6, "d": 85, "w": 12.5, "r": 22, "preds": [27, 28]},
                {"id": 30, "p": 7, "d": 90, "w": 13.5, "r": 24, "preds": [29]},

                {"id": 31, "p": 5, "d": 95, "w": 15.0, "r": 0, "preds": [10, 23, 30]},
                {"id": 32, "p": 6, "d": 100, "w": 16.0, "r": 0, "preds": [10, 24, 30]},
                {"id": 33, "p": 7, "d": 105, "w": 17.0, "r": 0, "preds": [25, 26, 31]},
                {"id": 34, "p": 8, "d": 110, "w": 18.0, "r": 0, "preds": [27, 28, 32]},
                {"id": 35, "p": 6, "d": 115, "w": 19.0, "r": 0, "preds": [33, 34, 21, 22]},
                {"id": 36, "p": 7, "d": 120, "w": 20.0, "r": 0, "preds": [35, 17, 18, 19]},
                {"id": 37, "p": 8, "d": 125, "w": 21.0, "r": 0, "preds": [36, 10, 20, 29]},
                {"id": 38, "p": 9, "d": 130, "w": 22.0, "r": 0, "preds": [37, 1, 5, 25, 30]},
                {"id": 39, "p": 10, "d": 135, "w": 23.0, "r": 0, "preds": [38, 2, 6, 26, 31]},
                {"id": 40, "p": 12, "d": 140, "w": 25.0, "r": 0, "preds": [39, 3, 7, 27, 32]}
            ]
        }

    def update_gwo_progress(self, current, max_iter, fitness):
        self.gwo_log.append(f"✨ Iteration {current}/{max_iter}: Best Fitness = {fitness:.2f} 💖")

    def gwo_finished(self, results: dict):
        self.gwo_log.append("\n--- 🏆 TỐI ƯU HÓA HOÀN THÀNH VINH QUANG 🏆 ---")
        self.metrics_display.update_metrics(1, results['metrics'])
        
        self.last_schedule_data = results['schedule'] 
        
        self.schedule_grid.display_schedule(self.last_schedule_data)
        self.gantt_chart.set_schedule_data(self.last_schedule_data) 
        self.output_tabs.setCurrentIndex(1) 
        
        vector_str = "Best Priority Vector (Top 10 jobs - Giá trị nhỏ nhất có ưu tiên cao nhất):\n"
        
        if isinstance(results['vector'], dict):
            top_jobs = sorted(results['vector'].items(), key=lambda item: item[1])[:10]
            for jid, val in top_jobs:
                 vector_str += f"  Job {jid}: {val:.4f} ✨\n"
        else:
             vector_str += "  Error: Vector format invalid."


        self.gwo_log.append(f"\n--- GWO BEST PRIORITY VECTOR ---\n{vector_str}")
        self.gwo_log.append(f"⏱️ Tổng thời gian chạy: {results['metrics']['executionTime']:.4f}s")
        
        self._show_message_box("Thành công Tuyệt vời", f"GWO đã hoàn thành xuất sắc! Objective: {results['metrics']['objectiveValue']:.2f}. Kiểm tra tab Schedule Output.", QMessageBox.Icon.Information)

    def gwo_error(self, message: str):
        self._show_message_box("Lỗi GWO", message, QMessageBox.Icon.Critical)
        self.gwo_log.append(f"\n--- 💣 LỖI LỚN XẢY RA: {message} 💣 ---\n")