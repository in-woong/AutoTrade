import schedule
import time
from user_manager import UserManager
from data_collector import DataCollector
from trade_executor import TradeExecutor
from ai_decision_maker import AIDecisionMaker

class Scheduler:
    def __init__(self, user_manager: UserManager, data_collector: DataCollector, trade_executor: TradeExecutor, ai_decision_maker: AIDecisionMaker):
        self.user_manager = user_manager
        self.data_collector = data_collector
        self.trade_executor = trade_executor
        self.ai_decision_maker = ai_decision_maker

    def run_trading_cycle(self, user_id: str):
        user = self.user_manager.get_user(user_id)
        if not user:
            return

        market_data = self.data_collector.collect_market_data("KRW-BTC")
        fgi = self.data_collector.collect_fear_greed_index()
        news = self.data_collector.collect_news()
        chart_path = self.data_collector.capture_chart()

        # Reflection 데이터 (예시)
        reflection = {"past_trades": "Example reflection data"}

        decision = self.ai_decision_maker.get_decision(user.gpt_preferences, market_data, reflection)

        if decision.get("decision") in ["buy", "sell"]:
            self.trade_executor.execute_trade(decision)

    def schedule_trading(self):
        for user_id, user in self.user_manager.users.items():
            schedule.every(user.trading_interval).hours.do(self.run_trading_cycle, user_id)

    def start(self):
        while True:
            schedule.run_pending()
            time.sleep(1)
