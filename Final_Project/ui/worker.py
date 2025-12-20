import time
import copy
import traceback
from PyQt6.QtCore import QThread, pyqtSignal

# Import từ core package
from core.scheduler import Scheduler
from core.gwo import GWOScheduler

class GWOThread(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int, int, float)
    error = pyqtSignal(str)
    thread_done = pyqtSignal() 

    def __init__(self, scheduler: Scheduler, pop_size: int, max_iter: int):
        super().__init__()
        self.scheduler = scheduler
        self.pop_size = pop_size
        self.max_iter = max_iter

    def run(self):
        try:
            start_time = time.time()  # <--- BẮT ĐẦU ĐO THỜI GIAN
            
            scheduler_copy = copy.deepcopy(self.scheduler)
            gwo = GWOScheduler(scheduler_copy, pop_size=self.pop_size, max_iter=self.max_iter)
            
            def update_progress(t, max_t, fitness):
                self.progress.emit(t, max_t, fitness)

            best_priority_vector, best_fitness = gwo.solve(progress_callback=update_progress)

            sch_final = copy.deepcopy(self.scheduler)
            sch_final.greedy_schedule(priority_vector=best_priority_vector)
            metrics_gwo = sch_final.compute_metrics()
            
            end_time = time.time()  # <--- KẾT THÚC ĐO THỜI GIAN
            metrics_gwo['executionTime'] = end_time - start_time # Lưu thời gian chạy

            self.finished.emit({
                "vector": best_priority_vector,
                "metrics": metrics_gwo,
                "schedule": sch_final.schedule, 
                "fitness_history": getattr(gwo, 'best_fitness_history', [])
            })
        except Exception as e:
            error_message = f"Lỗi GWO (Runtime): {type(e).__name__}: {e}"
            self.error.emit(error_message)
            print(f"TRACEBACK GWO:\n{traceback.format_exc()}")
        finally:
            self.thread_done.emit()