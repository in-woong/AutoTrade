from typing import Dict, List
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
        self.users: Dict[str, User] = {}

    def add_user(self, user: User):
        self.users[user.user_id] = user

    def get_user(self, user_id: str) -> User:
        return self.users.get(user_id)
