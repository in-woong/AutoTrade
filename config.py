import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    TRADING_INTERVAL = int(os.getenv("TRADING_INTERVAL", 2))  # 기본 2시간 간격
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    UPBIT_API_KEY = os.getenv("UPBIT_API_KEY")
    UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")
    MINIMUM_ORDER_AMOUNT = float(os.getenv("MINIMUM_ORDER_AMOUNT", 5000))  # 최소 주문 금액
