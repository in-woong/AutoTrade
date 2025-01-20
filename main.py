from user_manager import UserManager, User
from data_collector import DataCollector
from trade_executor import TradeExecutor
from ai_decision_maker import AIDecisionMaker
from scheduler import Scheduler
from config import Config
from utils.logger import setup_logger

logger = setup_logger("Main")

def main():
    user_manager = UserManager()
    data_collector = DataCollector()
    trade_executor = TradeExecutor(api_key=Config.UPBIT_API_KEY, secret_key=Config.UPBIT_SECRET_KEY)
    ai_decision_maker = AIDecisionMaker()

    scheduler = Scheduler(user_manager, data_collector, trade_executor, ai_decision_maker)

    # Add user
    user_manager.add_user(User(user_id="user1", api_key="key", secret_key="secret", trading_interval=2, gpt_preferences=["market_data"]))

    # Schedule trading
    scheduler.schedule_trading()
    scheduler.start()

if __name__ == "__main__":
    main()
