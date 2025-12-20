import random
import copy
from typing import List, Dict, Tuple
from .scheduler import Scheduler # Kết nối với file scheduler.py

class GWOScheduler:
    def __init__(self, scheduler: Scheduler,
                 pop_size=20,
                 max_iter=50,
                 lower=-1.0,
                 upper=1.0):
        self.sch = scheduler
        self.jobs = list(scheduler.jobs.keys())
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.lower = lower
        self.upper = upper

        self.population: List[Dict[int, float]] = []  # list of priority dicts
        self.fitness: List[float] = []
        self.best_fitness_history = []
        self.best_solution = None

    # ---------- initialization ----------
    def init_population(self):
        base = {}
        for jid, job in self.sch.jobs.items():
            # Sử dụng công thức heuristic
            base[jid] = job.d + job.p - job.w

        self.population = []

        # alpha wolf: heuristic
        self.population.append(base)

        # beta, delta: noisy heuristic
        for _ in range(2):
            x = {jid: base[jid] + random.uniform(-0.1, 0.1) for jid in self.jobs}
            self.population.append(x)

        # rest: random
        while len(self.population) < self.pop_size:
            x = {jid: random.uniform(self.lower, self.upper) for jid in self.jobs}
            self.population.append(x)

    # ---------- fitness ----------
    def evaluate(self, X: Dict[int, float]):
        # Tạo bản sao mới cho mỗi lần đánh giá fitness
        sch_temp = copy.deepcopy(self.sch) 
        sch_temp.greedy_schedule(priority_vector=X) 
        metrics = sch_temp.compute_metrics()
        return metrics["objectiveValue"]

    # ---------- main loop (Added progress_callback) ----------
    def solve(self, progress_callback=None) -> Tuple[Dict[int, float], float]:
        self.init_population()

        X_alpha, X_beta, X_delta = None, None, None
        
        for t in range(self.max_iter):
            self.fitness = [self.evaluate(X) for X in self.population]

            wolves = sorted(zip(self.population, self.fitness), key=lambda x: x[1])
            
            X_alpha = wolves[0][0]
            X_beta = wolves[1][0]
            X_delta = wolves[2][0]

            self.best_fitness_history.append(wolves[0][1])

            a = 2 * (1 - t / self.max_iter)

            new_population = []

            for i, X in enumerate(self.population):
                # Giữ nguyên 3 con sói đầu tiên
                if i < 3 and t == 0: 
                    new_population.append(X)
                    continue

                X_new = {}
                for jid in self.jobs:
                    r1, r2 = random.random(), random.random()
                    A1 = 2 * a * r1 - a 
                    C1 = 2 * r2         

                    D_alpha = abs(C1 * X_alpha[jid] - X[jid])
                    D_beta  = abs(C1 * X_beta[jid]  - X[jid])
                    D_delta = abs(C1 * X_delta[jid] - X[jid])

                    X1 = X_alpha[jid] - A1 * D_alpha
                    X2 = X_beta[jid]  - A1 * D_beta
                    X3 = X_delta[jid] - A1 * D_delta

                    val = (X1 + X2 + X3) / 3

                    val = max(self.lower, min(self.upper, val))
                    X_new[jid] = val

                new_population.append(X_new)

            self.population = new_population
            
            if progress_callback:
                progress_callback(t + 1, self.max_iter, self.best_fitness_history[-1]) 

        # Final evaluation
        final_fitness = [self.evaluate(X) for X in self.population]
        best_idx = final_fitness.index(min(final_fitness))
        self.best_solution = self.population[best_idx]
        
        return self.best_solution, min(final_fitness)