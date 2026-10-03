"""Configuration dataclass and settings for Tying-The-Rope optimization model."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ModelConfig:
    """Configuration parameters for the site-product qualification optimization."""

    mode: str = "LP"  # 'LP' or 'MIP'
    margin: bool = False
    load_priority: bool = True
    th_value: float = 0.003
    alpha: float = 0.8
    obj_tol: float = 1e-5
    sl_tol: float = 1e-5
    pct_of_sl_full_target: float = 1.0
    wt_min_u_obj: float = 0.2
    big_m: float = 1000.0
    sl_target: float = 0.0
    max_round: int = 20
    num_scenario: int = 100
    ref_quarter: Optional[int] = None  # 0-indexed quarter; if None, defaults to quarter with maximum forecast demand
    keep_raw_other_quarters: bool = False
    keep_raw_ref_quarters: bool = False
    keep_raw_added_links: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "margin": self.margin,
            "load_priority": self.load_priority,
            "th_value": self.th_value,
            "alpha": self.alpha,
            "obj_tol": self.obj_tol,
            "sl_tol": self.sl_tol,
            "pct_of_sl_full_target": self.pct_of_sl_full_target,
            "wt_min_u_obj": self.wt_min_u_obj,
            "big_m": self.big_m,
            "sl_target": self.sl_target,
            "max_round": self.max_round,
            "num_scenario": self.num_scenario,
            "ref_quarter": self.ref_quarter,
        }

