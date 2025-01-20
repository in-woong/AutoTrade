import time
from trading_logic import trading_logic
from utils.cleanup import CleanupManager
from data.user_manager import UserManager

if __name__ == "__main__":
    log_dir = "./logs"
    screenshot_dir = "./screenshots"
    cleanup_manager = CleanupManager()
    user_manager = UserManager()

    while True:
        try:
            # Get active users from the database
            active_users = user_manager.get_active_users()

            # Loop through active users and execute trading logic
            for user in active_users:
                user_id = user["id"]
                trading_logic(user_id)
                time.sleep(1)  # Small delay between users

            # Clean up old logs and screenshots every hour
            cleanup_manager.clean_directory(log_dir, max_age_hours=24)
            cleanup_manager.clean_directory(screenshot_dir, max_age_hours=24)

            time.sleep(60)  # Wait for 1 minute before the next iteration
        except KeyboardInterrupt:
            print("Trading bot stopped by user.")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
