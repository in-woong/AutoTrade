import pyupbit
from typing import Dict, Any
import logging

logger = logging.getLogger("TradeExecutor")


class TradeExecutor:
    def __init__(self, api_key: str, secret_key: str):
        self.upbit = pyupbit.Upbit(api_key, secret_key)

    def execute_trade(self, decision: Dict[str, Any]) -> bool:
        try:
            if decision["decision"] == "buy":
                return self._execute_buy(decision["percentage"])
            elif decision["decision"] == "sell":
                return self._execute_sell(decision["percentage"])
            return True # Hold position
        except Exception as e:
            print(f"Error executing trade: {e}")
            return False

    def _execute_buy(self, percentage: float) -> bool:
        """Execute buy order"""
        krw_balance = self.upbit.get_balance("KRW")
        amount = krw_balance * (percentage / 100) * (1 - self.config.TRANSACTION_FEE)

        if amount < self.config.MINIMUM_ORDER_AMOUNT:
            logger.warning("Insufficient funds for buy order")
            return False

        result = self.upbit.buy_market_order("KRW-BTC", amount)
        return bool(result)

    def _execute_sell(self, percentage: float) -> bool:
        """Execute sell order"""
        btc_balance = self.upbit.get_balance("KRW-BTC")
        amount = btc_balance * (percentage / 100)

        if amount * pyupbit.get_current_price("KRW-BTC") < self.config.MINIMUM_ORDER_AMOUNT:
            logger.warning("Insufficient BTC for sell order")
            return False

        result = self.upbit.sell_market_order("KRW-BTC", amount)
        return bool(result)