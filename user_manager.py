import json
from typing import List
from dataclasses import dataclass

@dataclass
class User:
    user_id: str
    api_key: str
    secret_key: str
    trading_interval: int
    gpt_preferences: List[str]

class UserManager:
    def __init__(self):
        self.users = {}

    def add_user(self, user: User):
        self.users[user.user_id] = user

    def load_users_from_file(self, file_path: str):
        try:
            with open(file_path, 'r') as f:
                users_data = json.load(f)
            for user_data in users_data:
                user = User(**user_data)
                self.add_user(user)
        except Exception as e:
            print(f"Error loading users from file: {e}")

    def get_user(self, user_id: str) -> User:
        return self.users.get(user_id)
