import schedule
import time
from user_manager import UserManager
from data_collector import DataCollector
from trade_executor import TradeExecutor
from ai_decision_maker import AIDecisionMaker
from utils.logger import setup_logger

logger = setup_logger("Scheduler", "scheduler.log")

class Scheduler:
    def __init__(self, user_manager: UserManager, data_collector: DataCollector, trade_executor: TradeExecutor, ai_decision_maker: AIDecisionMaker):
        self.user_manager = user_manager
        self.data_collector = data_collector
        self.trade_executor = trade_executor
        self.ai_decision_maker = ai_decision_maker

    def run_trading_cycle(self, user_id: str):
        user = self.user_manager.get_user(user_id)
        if not user:
            logger.error(f"User {user_id} not found.")
            return

        logger.info(f"Running trading cycle for user {user_id}.")

        try:
            # Step 1: Data Collection
            market_data = self.data_collector.get_trading_data()
            news = self.data_collector.fetch_google_news()
            fear_greed_index = self.data_collector.collect_fear_greed_index()
            chart_image = self.data_collector.capture_chart()
            technical_indicators = market_data.get("technical_summary", {})
            trading_data = {
                "daily": market_data.get("daily_data", []),
                "hourly": market_data.get("hourly_data", []),
            }

            # Step 2: AI Decision
            decision = self.ai_decision_maker.get_decision(
                user_preferences=user.gpt_preferences,
                market_data=market_data,
                additional_data={
                    "news": news,
                    "fear_greed_index": fear_greed_index,
                    "chart_image": chart_image,
                    "technical_indicators": technical_indicators,
                    "trading_data": trading_data,
                }
            )

            # Step 3: Execute Trade
            if decision["decision"] in ["buy", "sell"]:
                self.trade_executor.execute_trade(decision)
                logger.info(f"Executed trade: {decision}.")
            else:
                logger.info("No trade executed (decision: hold).")

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")

    def schedule_trading(self):
        for user_id, user in self.user_manager.users.items():
            schedule.every(user.trading_interval).hours.do(self.run_trading_cycle, user_id)

    def start(self):
        while True:
            schedule.run_pending()
            time.sleep(1)
