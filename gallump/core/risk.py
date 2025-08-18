"""
risk.py - ONLY calculates risk
Single responsibility: Evaluate trade safety, check portfolio-level risk, expose risk parameters.
"""

from typing import Dict, Optional, List
from core.types import Trade, Portfolio, Position, RiskResult

class RiskManager:
    """Handles ALL risk calculations for trades and positions."""

    DEFAULTS = {
        'max_position_pct': 0.10,   # 10% max per position
        'max_loss_pct': 0.15,       # 15% daily loss limit
        'max_positions': 10,        # Max concurrent positions
        'option_stop_pct': 0.30,    # 30% stop for options
        'stock_stop_pct': 0.15      # 15% stop for stocks
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = dict(self.DEFAULTS)
        if config:
            self.config.update(config)

    def evaluate(self, trade: Trade, portfolio: Portfolio) -> RiskResult:
        """Evaluate if trade fits all portfolio and risk-policy limits."""
        position_value = trade.quantity * trade.price
        position_pct = position_value / float(portfolio.total_value or 1)

        warnings: List[str] = []
        approved = True

        # Check per-position size
        if position_pct > self.config['max_position_pct']:
            warnings.append(f"Position too large: {position_pct:.1%} > {self.config['max_position_pct']:.1%}")
            approved = False

        # Position count limit
        if len(portfolio.positions) >= self.config['max_positions']:
            warnings.append(f"Too many concurrent positions: {len(portfolio.positions)} (max {self.config['max_positions']})" )
            approved = False

        # Calculate stop loss
        if trade.asset_type == 'OPTION':
            stop_loss = trade.price * (1 - self.config['option_stop_pct'])
        else:
            stop_loss = trade.price * (1 - self.config['stock_stop_pct'])

        max_loss = (trade.price - stop_loss) * trade.quantity

        return RiskResult(
            approved=approved,
            position_size=trade.quantity,
            stop_loss=stop_loss,
            max_loss=max_loss,
            warnings=warnings
        )

    def check_position_limits(self, position: Position) -> bool:
        """Check risk on a single open position (e.g. for drawdown, trailing stop)."""
        # Example: flag if unrealized loss exceeds 30% of position value
        return position.unrealized_pnl > -(abs(position.market_value) * 0.30)

    def calculate_safe_size(self, trade: Trade, portfolio: Portfolio) -> float:
        """Suggests the largest safe size for a trade under risk policy."""
        max_position = portfolio.total_value * self.config['max_position_pct']
        max_shares = max_position / (trade.price or 1)
        return min(float(trade.quantity), int(max_shares))

    def get_policy_summary(self) -> Dict:
        """Returns risk-control values so API/UI can display policy."""
        return dict(self.config)
