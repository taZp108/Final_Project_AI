import heapq
import math
from typing import List, Dict, Any
from .job import Job  # Kết nối với file job.py

class Scheduler:
    def __init__(self, machines:int=1, alpha:float=1.0, beta:float=1.0):
        self.machines = machines
        self.alpha = alpha
        self.beta = beta
        self.jobs: Dict[int, Job] = {}
        # Đảm bảo schedule luôn là một DICTIONARY RỖNG để tránh lỗi key
        self.schedule: Dict[str, List[Dict[str, Any]]] = {} 

    @staticmethod
    def from_dict(input_data: Dict[str, Any]) -> 'Scheduler':
        sch = Scheduler(machines=int(input_data.get('machines',1)),
                        alpha=float(input_data.get('alpha',1.0)),
                        beta=float(input_data.get('beta',1.0)))
        for j in input_data.get('jobs', []):
            job = Job.from_dict(j)
            sch.jobs[job.id] = job
        return sch

    def greedy_schedule(self, priority_vector: Dict[int, float] = None):
        # --- build graph (indeg, succ) ---
        indeg = {jid: 0 for jid in self.jobs}
        succ = {jid: [] for jid in self.jobs}
        for jid, job in self.jobs.items():
            for p in job.preds:
                if p not in self.jobs:
                    # Lỗi chu trình hoặc dữ liệu không hợp lệ
                    raise ValueError(f"Predecessor {p} of job {jid} not found") 
                indeg[jid] += 1
                succ[p].append(jid)
        
        # Cycle check (simplified from original for brevity, assume check is valid)
        tmp_q = [jid for jid, deg in indeg.items() if deg == 0]
        visited = 0
        tmp_indeg = indeg.copy()
        while tmp_q:
            x = tmp_q.pop()
            visited += 1
            for nb in succ.get(x, []):
                tmp_indeg[nb] -= 1
                if tmp_indeg[nb] == 0:
                    tmp_q.append(nb)
        if visited != len(self.jobs):
            # Nếu có chu trình, trả về lịch trình rỗng an toàn
            self.schedule = {f"M{m}": [] for m in range(1, self.machines + 1)}
            raise ValueError("Cycle detected in precedence constraints")

        # --- machine heap: (time_free, machine_id) ---
        machine_heap = [(0, m) for m in range(1, self.machines + 1)]
        heapq.heapify(machine_heap)

        # --- priority key cho ready heap ---
        def ready_key(jid, now):
            job = self.jobs[jid]
            
            if priority_vector is not None:
                # GWO priority: ưu tiên giá trị nhỏ nhất
                return (
                    priority_vector.get(jid, 0), 
                    job.d,                        
                    jid
                )
            else:
                # Baseline heuristic (Sử dụng LIFO/Critical path)
                alpha_h = 10
                beta_h = 1.0
                system_pressure = job.d + job.p
                job_risk = job.w * (max(0, job.p + max(now, preds_completed_at[jid]) - job.d))                
                core_score = alpha_h * system_pressure - beta_h * job_risk
                return (core_score, job.d, job.p, -job.w, jid)
                

        ready_heap = []      
        in_ready = set()     

        # --- release state tracking ---
        release_heap = []
        sched_indeg = indeg.copy()
        remaining = set(self.jobs.keys())
        preds_completed_at = {jid: 0 for jid in self.jobs}
        
        # Schedule lưu trữ kết quả theo format GUI
        schedule_dict = {f"M{m}": [] for m in range(1, self.machines + 1)}

        # khởi tạo release_heap
        for jid, job in self.jobs.items():
            if sched_indeg[jid] == 0:
                heapq.heappush(release_heap, (job.r, jid))

        current_time = 0.0 # Sử dụng float cho thời gian

       # helper: chuyển tất cả job có r <= now từ release_heap -> ready_heap (batch)
        def pop_releases_up_to(now):
            # Sử dụng nonlocal để tác động lên biến ở scope cha
            nonlocal ready_heap
            
            # 1. Chuyển job từ release_heap sang in_ready
            while release_heap and release_heap[0][0] <= now:
                _, jid = heapq.heappop(release_heap)
                in_ready.add(jid)
            
            # Cập nhật lại toàn bộ ready_heap bằng cách gọi ready_key
            new_heap = []
            for jid in list(in_ready):
                if jid in remaining:
                    score = ready_key(jid, now)  # <--- Dùng hàm ở đây cho gọn
                    heapq.heappush(new_heap, (score, jid))
            ready_heap = new_heap

        # ban đầu add tất cả job r <= 0
        pop_releases_up_to(0)
        
        # --- main loop ---
        while remaining:
            
            # 1. Xử lý trường hợp ready_heap trống (chưa có job nào sẵn sàng)
            if not ready_heap:
                if not release_heap:
                    break 

                # Chuyển thời gian đến sự kiện release sớm nhất
                next_r, _ = release_heap[0]
                current_time = max(current_time, next_r)
                pop_releases_up_to(current_time)
                # Tiếp tục vòng lặp để lấy máy rảnh ở thời điểm mới

            # 2. Xử lý máy rảnh
            # Lấy máy rảnh sớm nhất
            t_free, mid = machine_heap[0]
            
            # Nếu máy rảnh muộn hơn thời điểm hiện tại và có job sẵn sàng, 
            # cần chuyển thời gian đến thời điểm máy rảnh.
            if t_free > current_time + 1e-6 and ready_heap:
                current_time = t_free
                pop_releases_up_to(current_time) # Cần kiểm tra lại release
                
            free_machines = []
            # Lấy tất cả máy rảnh tại thời điểm current_time
            while machine_heap and machine_heap[0][0] <= current_time + 1e-6:
                free_machines.append(heapq.heappop(machine_heap))

            # 3. Phân công (Assignments)
            assignments = []
            for _ in range(len(free_machines)):
                # Dọn dẹp ready_heap khỏi các job đã bị xếp lịch trong các luồng khác (nếu có)
                while ready_heap and ready_heap[0][1] not in remaining:
                    _, stale_jid = heapq.heappop(ready_heap)
                    in_ready.discard(stale_jid)
                
                if not ready_heap:
                    break
                    
                _, jid = heapq.heappop(ready_heap)
                in_ready.discard(jid)
                assignments.append(jid)

            # Schedule
            used_free = free_machines[:len(assignments)]
            unused_free = free_machines[len(assignments):]
            
            for (t_free, mid), jid in zip(used_free, assignments):
                job = self.jobs[jid]
                
                # Thời gian bắt đầu: max(Máy rảnh, Job release, Tiền nhiệm hoàn thành)
                start_time = max(t_free, job.r, preds_completed_at[jid]) 
                completion_time = start_time + job.p
                
                machine_name = f"M{mid}"
                schedule_dict[machine_name].append({
                    "job": jid,
                    "machine": machine_name,
                    "start": float(start_time),
                    "end": float(completion_time) # Sử dụng key "end"
                })
                
                heapq.heappush(machine_heap, (completion_time, mid))
                remaining.discard(jid)
                
                # Xử lý các job tiếp theo (successors)
                for s in succ.get(jid, []):
                    preds_completed_at[s] = max(preds_completed_at[s], completion_time)
                    sched_indeg[s] -= 1
                    if sched_indeg[s] == 0:
                        # Job tiếp theo đã sẵn sàng, thêm vào release_heap để chờ r.
                        heapq.heappush(release_heap, (self.jobs[s].r, s))
                
                # Cập nhật ready_heap với các job mới được release/đã hoàn thành tiền nhiệm
                pop_releases_up_to(completion_time) 

            # Trả lại các máy rảnh không được dùng
            for item in unused_free:
                heapq.heappush(machine_heap, item)
            
            # Cập nhật current_time cho vòng lặp tiếp theo
            if assignments:
                # Nếu có công việc được xếp, current_time có thể là thời gian hoàn thành sớm nhất
                earliest_completion = min([item[0] for item in used_free]) + job.p
                current_time = max(current_time, earliest_completion)
            else:
                 # Nếu không có assignment nào, current_time phải được cập nhật qua logic time jump ở đầu loop
                 pass

        self.schedule = schedule_dict
        return schedule_dict

    # Đã sửa: Tính metrics an toàn hơn từ cấu trúc Dict[str, List]
    def compute_metrics(self):
        # Kiểm tra an toàn: Lịch trình phải là dict và phải chứa dữ liệu
        if not isinstance(self.schedule, dict) or not any(self.schedule.values()):
            return {"makespan": 0, "totalPenalty": 0.0, "maxLateness": 0, "objectiveValue": 0.0}
        
        completion = {}
        makespan = 0
        
        # Duyệt qua từng máy và từng tác vụ
        for machine_tasks in self.schedule.values():
            for task in machine_tasks:
                jid = task.get('job')
                C = task.get('end', 0.0) # Sử dụng get('end') - key mới
                
                if jid is not None and jid in self.jobs:
                    completion[jid] = C
                    makespan = max(makespan, C)

        if not completion:
            return {"makespan": 0, "totalPenalty": 0.0, "maxLateness": 0, "objectiveValue": 0.0}
            
        total_penalty = 0.0
        max_lateness = 0
        
        # Tính toán Penalty
        for jid, job in self.jobs.items():
            C = completion.get(jid, makespan) # Nếu job bị thiếu, giả định hoàn thành ở Makespan
                
            tard = max(0, C - job.d)
            total_penalty += job.w * tard
            max_lateness = max(max_lateness, int(math.ceil(tard)))
            
        objective_value = self.alpha * makespan + self.beta * total_penalty
        return {
            "makespan": int(math.ceil(makespan)),
            "totalPenalty": float(total_penalty),
            "maxLateness": int(max_lateness),
            "objectiveValue": float(objective_value)
        }