import sqlite3

class UserManager:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Initializes the user database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    api_secret TEXT NOT NULL,
                    trading_cycle INTEGER DEFAULT 60,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            conn.commit()

    def get_user_info(self, user_id):
        """Fetches user info by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return cursor.fetchone()

    def update_user_status(self, user_id, is_active):
        """Updates the trading status of a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id))
            conn.commit()

    def get_active_users(self):
        """
        Fetches all active users from the database.

        Returns:
            list: A list of dictionaries containing active user details.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, api_key, api_secret FROM users WHERE is_active = 1")
            rows = cursor.fetchall()

            # Convert the result to a list of dictionaries
            return [
                {"id": row[0], "name": row[1], "api_key": row[2], "api_secret": row[3]}
                for row in rows
            ]

