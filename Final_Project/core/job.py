from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Job:
    id: int
    p: int
    d: int
    w: float
    r: int = 0
    preds: List[int] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Job':
        return Job(
            id=int(d['id']),
            p=int(d.get('p', d.get('processing_time', 0))),
            d=int(d.get('d', d.get('deadline', 0))),
            w=float(d.get('w', d.get('weight', 1.0))),
            r=int(d.get('r', d.get('release', 0))),
            preds=[int(x) for x in d.get('preds', [])]
        )