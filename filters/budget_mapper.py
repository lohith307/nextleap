"""BudgetMapper maps budget tiers (low, medium, high) into numeric cost ranges."""
from typing import Tuple
from domain.models import BudgetBand


class BudgetMapper:
    def __init__(self, p33: float = 400.0, p66: float = 800.0):
        self.p33 = p33
        self.p66 = p66

    def update_percentiles(self, p33: float, p66: float):
        self.p33 = p33
        self.p66 = p66

    def get_cost_range(self, budget: BudgetBand) -> Tuple[float, float]:
        """
        Map BudgetBand to (min_cost, max_cost).
        - low: <= P33 (e.g. ₹0 - ₹400)
        - medium: P33 to P66 (e.g. ₹350 - ₹900 with generous overlap)
        - high: >= P66 (e.g. ₹750 - ₹100,000)
        """
        if budget == BudgetBand.LOW:
            return 0.0, self.p33 * 1.15
        elif budget == BudgetBand.MEDIUM:
            return self.p33 * 0.85, self.p66 * 1.2
        elif budget == BudgetBand.HIGH:
            return self.p66 * 0.9, 100000.0
        return 0.0, 100000.0
