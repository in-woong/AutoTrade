from user_manager import UserManager
from data_collector import DataCollector
from trade_executor import TradeExecutor
from ai_decision_maker import AIDecisionMaker
from scheduler import Scheduler
from config import Config
import schedule
import time
from utils.logger import setup_logger

logger = setup_logger("Main", "application.log")

def main():
    user_manager = UserManager()
    data_collector = DataCollector()
    trade_executor = TradeExecutor(api_key=Config.UPBIT_API_KEY, secret_key=Config.UPBIT_SECRET_KEY)
    ai_decision_maker = AIDecisionMaker()

    scheduler = Scheduler(user_manager, data_collector, trade_executor, ai_decision_maker)

    # Load users from JSON file
    user_manager.load_users_from_file("users.json")

    # Schedule trading
    scheduler.schedule_trading()

    # Keep the scheduler running
    logger.info("Trading bot started. Waiting for scheduled tasks...")
    while True:
        try:
            schedule.run_pending()  # Check and execute pending tasks
            time.sleep(1)  # Sleep for 1 second to optimize CPU usage
        except Exception as e:
            logger.error(f"Unexpected error occurred in the main loop: {e}", exc_info=True)
            time.sleep(5)  # Wait before retrying to avoid rapid failure loops

if __name__ == "__main__":
    main()
