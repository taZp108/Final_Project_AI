import random
import math
from typing import Dict, List, Any
from PyQt6.QtWidgets import (
    QWidget, QLabel, QGridLayout, QScrollArea, QVBoxLayout
)
from PyQt6.QtCore import Qt, QCoreApplication, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush

class GanttChartWidget(QWidget):
    """Widget tùy chỉnh để vẽ biểu đồ Gantt."""
    def __init__(self):
        super().__init__()
        self.schedule_data: Dict[str, List[Dict[str, Any]]] = {}
        self.max_time = 0
        self.job_colors: Dict[int, QColor] = {}
        self.setMinimumHeight(150)

    def _get_job_color(self, job_id: int):
        if job_id not in self.job_colors:
            random.seed(job_id * 12345) 
            # Dùng màu sắc rực rỡ hơn cho theme "lộng lẫy"
            r = random.randint(150, 255) 
            g = random.randint(100, 200)
            b = random.randint(150, 255)
            self.job_colors[job_id] = QColor(r, g, b)
        return self.job_colors[job_id]

    def set_schedule_data(self, schedule_dict: Dict[str, List[Dict[str, Any]]]):
        self.schedule_data = schedule_dict
        self.max_time = 0
        
        for tasks in schedule_dict.values():
            for task in tasks:
                self.max_time = max(self.max_time, task.get("end", 0.0))

        num_machines = len(schedule_dict)
        if num_machines > 0:
            self.setMinimumHeight(max(150, num_machines * 30 + 30)) 
        else:
            self.setMinimumHeight(150)

        self.update()
        

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Nền tối
        painter.setBrush(QBrush(QColor("#0d1117"))) # Nền siêu tối
        painter.drawRect(self.rect()) 

        if not self.schedule_data or self.max_time == 0:
            painter.setPen(QPen(QColor("#9cdafa")))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "✨ Chưa có lịch trình để vẽ Biểu đồ Gantt. ✨")
            return

        padding_y = 20
        padding_x_left = 80 
        padding_x_right = 20
        chart_width = self.width() - padding_x_left - padding_x_right
        
        machines = sorted(self.schedule_data.keys(), key=lambda m: int(m.replace('M', '') if m.startswith('M') and m[1:].isdigit() else 9999))
        num_machines = len(machines)
             
        machine_height = (self.height() - 2 * padding_y) / num_machines
        bar_height = machine_height * 0.6 
        
        # 1. Vẽ trục thời gian (Time Axis)
        painter.setPen(QPen(QColor("#007bff"), 2)) # Xanh Neon
        time_axis_y = self.height() - padding_y 
        painter.drawLine(padding_x_left, time_axis_y, self.width() - padding_x_right, time_axis_y)
        
        num_ticks = 5 if self.max_time > 10 else int(math.ceil(self.max_time)) 
        time_step = self.max_time / num_ticks if self.max_time else 1 
        
        for i in range(num_ticks + 1):
            time_value = i * time_step
            if time_value > self.max_time + 1e-6 and i < num_ticks: continue 
            
            x_pos = padding_x_left + (time_value / self.max_time) * chart_width if self.max_time else padding_x_left
            
            painter.drawLine(x_pos, time_axis_y, x_pos, time_axis_y + 5)
            
            painter.setPen(QPen(QColor("#00bcd4"))) # Màu cyan sáng
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(x_pos - 20, time_axis_y + 5, 40, 20), 
                             Qt.AlignmentFlag.AlignHCenter, 
                             f"{time_value:.1f}")

        # 2. Vẽ các thanh công việc (Job Bars)
        for i, machine_name in enumerate(machines):
            y_start = padding_y + i * machine_height
            
            # Vẽ nhãn máy
            painter.setPen(QPen(QColor("#ffc107"))) # Màu vàng nổi bật
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.drawText(QRectF(0, y_start, padding_x_left - 5, machine_height), 
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 
                             machine_name)
            
            # Vẽ đường phân cách máy
            painter.setPen(QPen(QColor("#495057"), 1, Qt.PenStyle.DotLine))
            if i > 0:
                painter.drawLine(padding_x_left, y_start, self.width() - padding_x_right, y_start)

            # Vẽ các Job
            tasks = self.schedule_data.get(machine_name, [])
            for task in tasks:
                job_id = task.get("job", 0)
                start = task.get("start", 0.0)
                end = task.get("end", 0.0) 
                duration = end - start
                
                if self.max_time == 0 or duration <= 0:
                    continue

                x1 = padding_x_left + (start / self.max_time) * chart_width
                x2 = padding_x_left + (end / self.max_time) * chart_width
                width = x2 - x1
                
                y_bar = y_start + (machine_height - bar_height) / 2
                
                color = self._get_job_color(job_id)
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(QColor(0, 0, 0), 0.5))
                painter.drawRect(QRectF(x1, y_bar, width, bar_height))
                
                if width > 10: 
                    painter.setPen(QPen(QColor("#000000"))) 
                    font_size = 8 if width > 20 else 7 
                    painter.setFont(QFont("Arial", font_size, QFont.Weight.Bold)) 
                    painter.drawText(QRectF(x1, y_bar, width, bar_height), 
                                     Qt.AlignmentFlag.AlignCenter, 
                                     f"J{job_id}")


class MetricsDisplayWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(1) 
        self.labels: Dict[str, QLabel] = {}
        self._setup_grid()
        self.clear_metrics()

    def _create_cell(self, text, is_header=False, alignment=Qt.AlignmentFlag.AlignCenter):
        label = QLabel(text)
        label.setAlignment(alignment)
        return label

    def _setup_grid(self):
        # THÊM CỘT Execution Time
        HEADERS = ["👑", "Makespan (Thời gian Hoàn tất)", "Total Penalty (Tổng Tiền phạt)", "Objective Value (Mục tiêu)", "Max Lateness (Trễ tối đa)", "Execution Time (Thời gian chạy)"]
        
        ROW_NAMES_DISPLAY = ["Baseline", "GWO 🐺"]
        ROW_NAMES_KEYS = ["baseline", "gwo"] 
        
        # THÊM KEY executionTime
        METRICS_KEYS = ["makespan", "totalPenalty", "objectiveValue", "maxLateness", "executionTime"]
        
        # Tăng cường màu mè cho header
        header_style = "background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8e24aa, stop:1 #ff00ff); color: white; padding: 10px; font-weight: bold; border: 1px solid #ff00ff;"
        
        for col, header in enumerate(HEADERS):
            label = self._create_cell(header, is_header=True)
            label.setStyleSheet(header_style)
            self.layout.addWidget(label, 0, col)
        
        # Tăng cường màu mè cho row header
        row_header_style = "background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1de9b6, stop:1 #00bcd4); color: #1f2733; padding: 10px; font-weight: bold; border: 1px solid #00bcd4;"
        data_style_base = "color: #9cdafa; padding: 10px; border: 1px solid #1f2733; background-color: #1f2733;" 
            
        for row_idx, row_name_display in enumerate(ROW_NAMES_DISPLAY):
            row_prefix_key = ROW_NAMES_KEYS[row_idx] 

            row_header = self._create_cell(row_name_display, is_header=True) 
            row_header.setStyleSheet(row_header_style)
            self.layout.addWidget(row_header, row_idx + 1, 0)
            
            for col_idx, key in enumerate(METRICS_KEYS):
                label_name = f"{row_prefix_key}_{key}" 
                data_label = self._create_cell("")
                data_label.setStyleSheet(data_style_base)
                self.labels[label_name] = data_label
                self.layout.addWidget(data_label, row_idx + 1, col_idx + 1)
                

    def clear_metrics(self):
        for label in self.labels.values():
            label.setText("...")
            label.setStyleSheet("background-color: #1f2733; color: #6c757d; padding: 10px; border: 1px solid #1f2733;") 

    def update_metrics(self, row: int, metrics: Dict[str, Any]):
        ROW_NAME = "gwo" if row == 1 else "baseline"
        METRICS_KEYS = ["makespan", "totalPenalty", "objectiveValue", "maxLateness", "executionTime"]
        data_style_base = "color: #9cdafa; padding: 10px; border: 1px solid #1f2733; background-color: #1f2733;" 

        for key in METRICS_KEYS:
            label_name = f"{ROW_NAME}_{key}"
            value = metrics.get(key, None)
            
            if value is not None:
                if key in ["makespan", "maxLateness"]:
                    self.labels[label_name].setText(f"🌟 {int(value)}")
                elif key == "executionTime":
                    # HIỂN THỊ THỜI GIAN
                    self.labels[label_name].setText(f"⏱️ {value:.4f}s")
                else:
                    self.labels[label_name].setText(f"💰 {value:.2f}")
            else:
                 self.labels[label_name].setText("...")
            
            self.labels[label_name].setStyleSheet(data_style_base)

        # Highlight Objective Value
        if "objectiveValue" in metrics:
            try:
                baseline_obj_label = self.labels["baseline_objectiveValue"]
                gwo_obj_label = self.labels["gwo_objectiveValue"]
                
                baseline_obj_str = baseline_obj_label.text().replace('💰 ', '').replace('...', '').strip()
                
                if row == 1 and baseline_obj_str:
                    baseline_obj_value = float(baseline_obj_str)
                    gwo_obj = metrics['objectiveValue']
                    
                    if gwo_obj < baseline_obj_value:
                        # Tốt hơn (Xanh Neon Rực rỡ)
                        color_style = "background-color: #004d40; color: #4CAF50; padding: 10px; border: 3px solid #64ffda; font-weight: extra bold; font-size: 11pt;" 
                    elif gwo_obj > baseline_obj_value:
                        # Kém hơn (Đỏ Cảnh báo)
                        color_style = "background-color: #4e0000; color: #ff5252; padding: 10px; border: 3px solid #ff1744; font-weight: extra bold; font-size: 11pt;"
                    else:
                        # Bằng nhau (Tím Lấp lánh)
                        color_style = "background-color: #260026; color: #ff80ff; padding: 10px; border: 3px solid #ea80fc; font-weight: extra bold; font-size: 11pt;"
                    
                    gwo_obj_label.setStyleSheet(color_style)
                    
            except Exception:
                pass


class ScheduleGridDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #495057; background-color: #0d1117; }")

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #0d1117;")
        
        self.inner_layout = QVBoxLayout(self.content_widget) 
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(1) 
        
        self.inner_layout.addWidget(self.grid_container)
        self.inner_layout.addStretch(1) 

        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)
        
        self._setup_headers()

    def _clear_grid_layout(self):
        while self.grid_layout.count() > 4: 
            item = self.grid_layout.takeAt(4)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                del item

    def _create_cell(self, text, style_base, alignment=Qt.AlignmentFlag.AlignCenter):
        label = QLabel(text)
        label.setAlignment(alignment)
        label.setStyleSheet(style_base)
        label.setMinimumHeight(30)
        return label

    def _setup_headers(self):
        HEADERS = ["Máy ⚙️", "Job ID", "Bắt đầu", "Kết thúc"]
        # Tăng cường header
        header_style = "background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffea00, stop:1 #ff9800); color: #1f2733; padding: 8px; font-weight: bold; border: 1px solid #ffea00;"
        
        for col, header in enumerate(HEADERS):
            label = self._create_cell(header, header_style)
            self.grid_layout.addWidget(label, 0, col)
            self.grid_layout.setColumnStretch(col, 1) 

    def display_schedule(self, schedule_dict: Dict[str, List[Dict[str, Any]]]):
        
        self._clear_grid_layout()

        if not isinstance(schedule_dict, dict) or not any(schedule_dict.values()):
            no_data_label = self._create_cell("✨ Không có dữ liệu lịch trình nào được tạo. Chạy Baseline hoặc GWO. ✨", 
                                              "background-color: #1f2733; color: #ffc107; padding: 20px; font-weight: bold; border: 2px solid #ffeb3b;", 
                                              Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(no_data_label, 1, 0, 1, 4) 
            QCoreApplication.processEvents()
            return

        row_idx = 1
        
        def machine_sort_key(machine_name):
            try:
                if machine_name.startswith('M') and machine_name[1:].isdigit():
                    return int(machine_name[1:])
                return machine_name 
            except ValueError:
                return machine_name 

        all_tasks = []
        for machine_name, tasks in schedule_dict.items():
            if isinstance(tasks, list):
                 for task in tasks:
                    all_tasks.append({
                        "machine": machine_name,
                        "job": task.get("job", "N/A"),
                        "start": task.get("start", 0.0),
                        "end": task.get("end", 0.0)
                    })
        
        all_tasks.sort(key=lambda x: (machine_sort_key(x['machine']), x['start']))
        
        current_machine_name = None
        
        for task in all_tasks:
            machine_name = task['machine']
            job_id = str(task['job'])
            start_time = f"⏱️ {task['start']:.2f}"
            end_time = f"🏁 {task['end']:.2f}"
            
            if machine_name != current_machine_name:
                try:
                    machine_id = machine_sort_key(machine_name)
                    # Sắc sỡ hơn: Xen kẽ xanh neon và tím
                    row_color_1 = "#1f2733" # Nền tối
                    row_color_2 = "#121a24" # Nền tối hơn
                    row_color = row_color_1 if machine_id % 2 == 1 else row_color_2
                except:
                    row_color = "#1f2733" 
                current_machine_name = machine_name
            
            # Highlight chi tiết từng task bằng màu cyan sáng
            style_base = f"background-color: {row_color}; color: #4fffe8; padding: 6px; border: 1px solid #121a24;"
            
            machine_cell = self._create_cell(machine_name, style_base)
            job_cell = self._create_cell(f"J-{job_id}", style_base)
            start_cell = self._create_cell(start_time, style_base)
            end_cell = self._create_cell(end_time, style_base)
            
            self.grid_layout.addWidget(machine_cell, row_idx, 0)
            self.grid_layout.addWidget(job_cell, row_idx, 1)
            self.grid_layout.addWidget(start_cell, row_idx, 2)
            self.grid_layout.addWidget(end_cell, row_idx, 3)
            
            row_idx += 1
            
        QCoreApplication.processEvents()