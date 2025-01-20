import os
import threading
import glob
import openai
from dotenv import load_dotenv
import schedule
import time
import requests
from datetime import datetime
import logging
from typing import Dict, List, Optional, Any
import pyupbit
from openai import OpenAI
import json
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import base64
import sqlite3
import pandas as pd
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 로깅 설정
file_handler = RotatingFileHandler(
    "trading_bot.log", maxBytes=5 * 1024 * 1024, backupCount=5
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


def encode_image(image_path: str) -> str:
    """이미지 파일을 Base64로 인코딩"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

@dataclass
class TradingConfig:
    MINIMUM_ORDER_AMOUNT: float = 5000.0
    TRANSACTION_FEE: float = 0.0005
    TRADING_INTERVAL: int = 1  # 4시간에서 1시간으로 변경
    SCHEDULE_CHECK_INTERVAL: int = 60  # 5분마다 체크
    CHART_LOAD_WAIT: int = 3  # 차트 로딩 대기 시간
    CHART_WIDTH: int = 800  # 차트 캡처 너비
    CHART_HEIGHT: int = 600  # 차트 캡처 높이
    DB_PATH: str = "trading_data.db"
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'local')
    SIMULATION_MODE: bool = os.getenv('ENVIRONMENT', 'local').lower() != 'ec2'
    UPBIT_ACCESS_KEY: str = os.getenv('UPBIT_ACCESS_KEY', '')
    UPBIT_SECRET_KEY: str = os.getenv('UPBIT_SECRET_KEY', '')
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    SERPAPI_API_KEY: str = os.getenv('SERPAPI_API_KEY', '')

    # 디버깅 파일 관리 설정
    DEBUG_FILE_RETENTION_DAYS: int = 7  # 디버깅 파일 보관 기간
    DEBUG_FILE_MAX_COUNT: int = 100  # 디버깅 파일 최대 개수

def cleanup_old_files(directory: str, file_extension: str = "*.png", days: int = 7):
    now = time.time()
    cutoff = now - (days * 86400)
    for file_path in glob.glob(os.path.join(directory, file_extension)):
        if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff:
            try:
                os.remove(file_path)
                logger.info(f"Deleted old file: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")

def limit_files_in_directory(directory: str, file_extension: str = "*.png", max_files: int = 100):
    files = sorted(glob.glob(os.path.join(directory, file_extension)), key=os.path.getmtime)
    if len(files) > max_files:
        for file_path in files[:-max_files]:
            try:
                os.remove(file_path)
                logger.info(f"Deleted excess file: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")

def maintain_debug_directory(directory: str, config: TradingConfig):
    """
    디버깅 디렉토리의 파일을 정리하는 함수 (오래된 파일 삭제 + 파일 개수 제한).
    """
    cleanup_old_files(directory, "*.png", days=config.DEBUG_FILE_RETENTION_DAYS)
    limit_files_in_directory(directory, "*.png", max_files=config.DEBUG_FILE_MAX_COUNT)

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- 기본 정보
                    decision TEXT,
                    percentage REAL,
                    reason TEXT,
                    -- 잔고 정보
                    btc_balance REAL,
                    krw_balance REAL,
                    btc_avg_buy_price REAL,
                    btc_krw_price REAL,
                    -- 분석 정보
                    reflection TEXT,
                    strategy_analysis TEXT,
                    key_patterns TEXT,
                    improvement_suggestions TEXT,
                    -- 트리거 정보
                    trigger_type TEXT,
                    price_change_percent REAL,
                    chart_path TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and return a database connection"""
        sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
        sqlite3.register_converter("timestamp", lambda val: datetime.fromisoformat(val.decode()))
        return sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

    def get_latest_reflection(self) -> Dict[str, Any]:
        """최근 거래에 대한 회고 데이터 가져오기"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    strategy_analysis, 
                    key_patterns, 
                    improvement_suggestions
                FROM trades
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return {
                    "strategy_analysis": row[0],
                    "key_patterns": row[1],
                    "improvement_suggestions": row[2]
                }
            return {}
        except Exception as e:
            logger.error(f"Error fetching latest reflection: {e}")
            return {}
        finally:
            conn.close()

    def log_trade(self, trade_data: Dict[str, Any]):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    timestamp, decision, percentage, reason,
                    btc_balance, krw_balance, btc_avg_buy_price,
                    btc_krw_price, reflection, 
                    strategy_analysis, key_patterns, improvement_suggestions,
                    trigger_type, price_change_percent,
                    technical_indicators, market_conditions, trading_volume,
                    fear_greed_data, news_sentiment, confidence_score, risk_assessment, chart_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(),
                trade_data['decision'],
                trade_data['percentage'],
                trade_data['reason'],
                trade_data['btc_balance'],
                trade_data['krw_balance'],
                trade_data['avg_buy_price'],
                trade_data['current_price'],
                trade_data['reflection'],
                trade_data.get('strategy_analysis', ''),
                trade_data.get('key_patterns', ''),
                trade_data.get('improvement_suggestions', ''),
                trade_data.get('trigger_type', 'schedule'),
                trade_data.get('price_change_percent', 0.0),
                json.dumps(trade_data.get('technical_indicators', {})),
                json.dumps(trade_data.get('market_conditions', {})),
                json.dumps(trade_data.get('trading_volume', {})),
                json.dumps(trade_data.get('fear_greed_data', {})),
                json.dumps(trade_data.get('news_sentiment', {})),
                trade_data.get('confidence', 0),
                trade_data.get('risk_level', ''),
                trade_data.get('chart_path', '')
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
            conn.rollback()
        finally:
            conn.close()


    def get_recent_trades(self, limit: int = 5) -> List[tuple]:
        """Get recent trades from database"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    timestamp, 
                    decision, 
                    percentage, 
                    btc_krw_price
                FROM trades 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()
        finally:
            conn.close()


class TradingBot:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.db_manager = DatabaseManager(config.DB_PATH)
        self.upbit = pyupbit.Upbit(config.UPBIT_ACCESS_KEY, config.UPBIT_SECRET_KEY)
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

        self.price_monitor_thread = None
        self.stop_monitoring = False

        # Define debug directory
        if self.config.ENVIRONMENT == 'EC2':
            self.debug_dir = "/home/ubuntu/bitcoin_chart_debug"
        else:
            self.debug_dir = os.path.join(os.path.expanduser("~"), "bitcoin_chart_debug")
        os.makedirs(self.debug_dir, exist_ok=True)

    def start_price_monitoring(self):
        def monitor_price():
            try:
                # 초기 가격 설정
                last_price = pyupbit.get_current_price("KRW-BTC")
                if last_price is None:
                    logger.error("Failed to get initial price")
                    return

                logger.info(f"Price monitoring started. Initial price: {last_price}")

                while not self.stop_monitoring:
                    try:
                        time.sleep(60)  # 1분 대기 후 가격 체크

                        current_price = pyupbit.get_current_price("KRW-BTC")
                        if current_price is None:
                            logger.error("Failed to get current price")
                            continue

                        change_percent = abs((current_price - last_price) / last_price * 100)

                        if change_percent > 1.0:  # 3% 이상 변동
                            logger.info(f"Significant price change detected: {change_percent}%")
                            self.trading_cycle(
                                trigger="price_change",
                                additional_data={
                                    "price_change_percent": change_percent,
                                    "previous_price": last_price,
                                    "current_price": current_price
                                }
                            )

                        last_price = current_price

                    except Exception as e:
                        logger.error(f"Price monitoring error: {e}")
                        time.sleep(60)  # 에러 발생 시 1분 대기

            except Exception as e:
                logger.error(f"Initial price fetch error: {e}")
                return

            self.price_monitor_thread = threading.Thread(target=monitor_price)
            self.price_monitor_thread.daemon = True
            self.price_monitor_thread.start()

    def calculate_trade_result(self, trade: tuple, current_status: Dict[str, Any]) -> str:
        """거래 결과 계산
        Args:
            trade: (timestamp, decision, percentage, reflection) 튜플
            current_status: 현재 상태 정보를 담은 딕셔너리
        """
        try:
            timestamp, decision, percentage, _ = trade
            current_price = current_status['current_price']
            avg_buy_price = current_status['avg_buy_price']

            if decision == 'buy':
                # 매수의 경우 현재가와 평균 매수가 비교
                if avg_buy_price > 0:
                    profit_percent = ((current_price - avg_buy_price) / avg_buy_price) * 100
                    return f"수익률: {profit_percent:.2f}%"
                return "평균매수가 정보 없음"

            elif decision == 'sell':
                return f"매도 완료 ({percentage}%)"

            else:  # hold
                return "홀딩"

        except Exception as e:
            logger.error(f"Error calculating trade result: {e}")
            return "계산 실패"

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to dataframe"""
        # 기본 지표들
        bb = BollingerBands(close=df['close'])
        macd = MACD(close=df['close'])
        rsi = RSIIndicator(close=df['close'])
        stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'])
        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'])
        obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume'])
        vwap = VolumeWeightedAveragePrice(high=df['high'], low=df['low'], close=df['close'],
                                          volume=df['volume'])

        # 이동평균선
        df['ma5'] = SMAIndicator(close=df['close'], window=5).sma_indicator()
        df['ma20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
        df['ma60'] = SMAIndicator(close=df['close'], window=60).sma_indicator()
        df['ma120'] = SMAIndicator(close=df['close'], window=120).sma_indicator()

        # 볼린저 밴드
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_width'] = bb.bollinger_wband()

        # MACD
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()

        # RSI
        df['rsi'] = rsi.rsi()

        # Stochastic
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()

        # ATR
        df['atr'] = atr.average_true_range()

        # OBV
        df['obv'] = obv.on_balance_volume()

        # VWAP
        df['vwap'] = vwap.volume_weighted_average_price()

        return df

    def click_option_with_scroll(self, driver, menu_xpath: str, option_xpath: str, wait_time: int = 10):
        """
        Selenium WebDriver를 사용하여 특정 옵션을 클릭하며, 화면에 표시되지 않은 경우 스크롤로 접근.

        Args:
            driver: Selenium WebDriver 객체.
            menu_xpath: 메뉴 버튼의 XPath.
            option_xpath: 선택할 옵션의 XPath.
            wait_time: 대기 시간 (초 단위, 기본값: 10).

        Returns:
            성공 여부 (True/False).
        """
        try:
            # 메뉴 버튼 클릭
            menu_button = WebDriverWait(driver, wait_time).until(
                EC.element_to_be_clickable((By.XPATH, menu_xpath))
            )
            menu_button.click()
            time.sleep(0.5)  # 메뉴 로딩 대기

            # 옵션 버튼 찾기
            option_button = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, option_xpath))
            )

            # 강제 스크롤로 옵션 버튼 노출
            driver.execute_script("arguments[0].scrollIntoView(true);", option_button)
            time.sleep(0.5)  # 스크롤 후 대기

            # 옵션 버튼 클릭
            WebDriverWait(driver, wait_time).until(
                EC.element_to_be_clickable((By.XPATH, option_xpath))
            ).click()
            logger.info(f"Successfully clicked option: {option_xpath}")
            return True

        except Exception as e:
            logger.error(f"Error in click_option_with_scroll: {e}")
            return False

    def select_bollinger_band(self, driver):
        """
        볼린저 밴드 설정을 위한 함수.
        """
        menu_xpath = "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[3]"
        option_xpath = '//*[@id="fullChartiq"]/div/div/div[1]/div/div/cq-menu[3]/cq-menu-dropdown/cq-scroll/cq-studies/cq-studies-content/cq-item[15]'
        return self.click_option_with_scroll(driver, menu_xpath, option_xpath)

    def select_3min_interval(self, driver):
        """
        3분 간격 설정을 위한 함수.
        """
        menu_xpath = "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[1]/span/cq-clickable"
        option_xpath = "/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[1]/cq-menu-dropdown/cq-item[3]"
        return self.click_option_with_scroll(driver, menu_xpath, option_xpath)

    def capture_chart(self) -> Optional[str]:
        """Capture and encode chart image based on environment"""
        if self.config.ENVIRONMENT == 'EC2':
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--remote-debugging-port=9222')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument(f"--window-size={self.config.CHART_WIDTH},{self.config.CHART_HEIGHT}")

            chromedriver_path = "/home/ubuntu/.wdm/drivers/chromedriver/linux64/128.0.6613.137/chromedriver-linux64/chromedriver"
            service = Service(executable_path=chromedriver_path)
        else:
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument(f"--window-size={self.config.CHART_WIDTH},{self.config.CHART_HEIGHT}")
            service = Service(ChromeDriverManager().install())

        try:
            # Chrome 버전에 맞는 WebDriver 설정
            driver = webdriver.Chrome(service=service, options=chrome_options)

            # 웹 페이지 로드 타임아웃 설정
            driver.set_page_load_timeout(10)  # 30초 타임아웃
            driver.get("https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC")

            # 명시적 대기 사용
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            time.sleep(self.config.CHART_LOAD_WAIT)

            # 3분 간격 설정
            if not self.select_3min_interval(driver):
                logger.error("Failed to select 3-minute interval.")

            # 볼린저 밴드 설정
            if not self.select_bollinger_band(driver):
                logger.error("Failed to select Bollinger Band.")

            # 스크린샷 저장 (디버깅 목적)
            if self.config.ENVIRONMENT == 'EC2':
                debug_dir = "/home/ubuntu/bitcoin_chart_debug"
            else:
                debug_dir = os.path.join(os.path.expanduser("~"), "bitcoin_chart_debug")

            os.makedirs(debug_dir, exist_ok=True)

            # 디버깅 디렉토리 정리
            maintain_debug_directory(self.debug_dir, self.config)

            # 타임스탬프 포함 파일명
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(debug_dir, f"chart_screenshot_{timestamp}.png")

            # 스크린샷 저장
            driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")

            # Base64로 인코딩
            encoded_image = encode_image(screenshot_path)

            # 디버깅 로그 추가
            logger.info(f"Screenshot saved to {screenshot_path}")
            return encoded_image
        except Exception as e:
            logger.error(f"Error capturing chart: {e}")
            return None
        finally:
            driver.quit()

    def fetch_fear_greed_index(self) -> Optional[Dict[str, Any]]:
        """Fetch Fear and Greed Index data"""
        url = "https://api.alternative.me/fng/"
        params = {
            "limit": 1,
            "format": "json"
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                return {
                    "value": int(data["data"][0]["value"]),
                    "classification": data["data"][0]["value_classification"]
                }
        except Exception as e:
            logger.error(f"Error fetching Fear and Greed Index: {e}")
            return None

    def fetch_google_news(self) -> List[Dict[str, str]]:
        """Fetch the latest BTC news headlines from Google News RSS"""
        rss_url = "https://news.google.com/rss/search?q=btc+when:1d&hl=en-US&gl=US&ceid=US:en"

        try:
            import feedparser
            feed = feedparser.parse(rss_url)

            # 최신 뉴스 5개만 추출
            news_results = []
            for entry in feed.entries[:5]:
                news_results.append({
                    "title": entry.title,
                    "date": entry.published
                })

            return news_results
        except Exception as e:
            logger.error(f"Error fetching Google News: {e}")
            return []

    def get_trading_data(self) -> Dict[str, Any]:
        """Collect all trading-related data"""
        try:
            # 현재 상태 조회
            krw_balance = self.upbit.get_balance("KRW")
            btc_balance = self.upbit.get_balance("KRW-BTC")
            avg_buy_price = self.upbit.get_avg_buy_price("KRW-BTC")
            current_price = pyupbit.get_current_price("KRW-BTC")

            # 총 자산 계산
            total_assets = krw_balance + (btc_balance * current_price)
            btc_ratio = (btc_balance * current_price) / total_assets if total_assets > 0 else 0

            # 수익률 계산
            profit_loss = ((current_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0

            # Get basic trading data
            investment_status = {
                "krw_balance": krw_balance,
                "btc_balance": btc_balance,
                "avg_buy_price": avg_buy_price,
                "current_price": current_price,
                "total_assets": total_assets,
                "btc_ratio": btc_ratio,
                "profit_loss": profit_loss
            }

            # Get orderbook data
            orderbook = pyupbit.get_orderbook("KRW-BTC")

            # Get and process chart data
            daily_data = pyupbit.get_ohlcv("KRW-BTC", count=200, interval="day")
            hourly_data = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=200)

            if daily_data is not None and hourly_data is not None:
                # Convert column names to lowercase
                daily_data.columns = [col.lower() for col in daily_data.columns]
                hourly_data.columns = [col.lower() for col in hourly_data.columns]

                # Add technical indicators
                daily_data = self.add_technical_indicators(daily_data)
                hourly_data = self.add_technical_indicators(hourly_data)

                return {
                    "investment_status": investment_status,
                    "orderbook": orderbook,
                    "daily_data": daily_data.tail(30).to_dict('records'),
                    "hourly_data": hourly_data.tail(24).to_dict('records'),
                    "technical_summary": {
                        "daily": {
                            "rsi": daily_data['rsi'].iloc[-1],
                            "macd": daily_data['macd'].iloc[-1],
                            "macd_signal": daily_data['macd_signal'].iloc[-1],
                            "bb_width": daily_data['bb_width'].iloc[-1],
                            "stoch_k": daily_data['stoch_k'].iloc[-1],
                            "stoch_d": daily_data['stoch_d'].iloc[-1],
                        },
                        "hourly": {
                            "rsi": hourly_data['rsi'].iloc[-1],
                            "macd": hourly_data['macd'].iloc[-1],
                            "macd_signal": hourly_data['macd_signal'].iloc[-1],
                            "bb_width": hourly_data['bb_width'].iloc[-1],
                            "stoch_k": hourly_data['stoch_k'].iloc[-1],
                            "stoch_d": hourly_data['stoch_d'].iloc[-1],
                        }
                    }
                }
            return {
                "investment_status": investment_status,
                "orderbook": orderbook,
                "daily_data": [],
                "hourly_data": []
            }
        except Exception as e:
            logger.error(f"Error getting trading data: {e}")
            return {}

    def execute_trade(self, decision: Dict[str, Any]) -> bool:
        """Execute trade based on AI decision"""
        try:
            if self.config.SIMULATION_MODE:
                logger.info(f"[Simulation Mode] {decision['decision']} trade would be executed: {decision['percentage']}%")
                return True  # 시뮬레이션 모드에서는 항상 성공으로 처리

            if decision["decision"] == "buy":
                return self._execute_buy(decision["percentage"])
            elif decision["decision"] == "sell":
                return self._execute_sell(decision["percentage"])
            return True  # Hold position
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
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

    def prepare_trading_summary(self, trading_data: Dict[str, Any]) -> Dict[str, str]:
        """Prepare concise trading summary for AI"""
        try:
            orderbook = trading_data.get('orderbook', {}).get('orderbook_units', [])
            market_depth = {
                'bid_total': sum(item['bid_size'] for item in orderbook[:5]) if orderbook else 0,
                'ask_total': sum(item['ask_size'] for item in orderbook[:5]) if orderbook else 0
            }

            return {
                "market_status": (
                    f"Current BTC Price: {trading_data['investment_status']['current_price']:,.0f} KRW\n"
                    f"Position: {trading_data['investment_status']['btc_balance']:.8f} BTC\n"
                    f"Average Buy Price: {trading_data['investment_status']['avg_buy_price']:,.0f} KRW\n"
                ),
                "technical_analysis": (
                    f"Daily RSI: {trading_data['technical_summary']['daily']['rsi']:.2f}\n"
                    f"Daily MACD: {trading_data['technical_summary']['daily']['macd']:.2f}\n"
                    f"Hourly RSI: {trading_data['technical_summary']['hourly']['rsi']:.2f}\n"
                    f"Hourly MACD: {trading_data['technical_summary']['hourly']['macd']:.2f}\n"
                ),
                "market_depth": (
                    f"Buy Pressure: {market_depth['bid_total']:.2f} BTC\n"
                    f"Sell Pressure: {market_depth['ask_total']:.2f} BTC\n"
                )
            }
        except KeyError as e:
            logger.error(f"Error preparing trading summary: {e}")
            return {}

    def get_trading_reflection(self) -> Dict[str, Any]:
        """Get AI analysis of past trading performance and patterns"""
        try:
            # 거래 직후 최신 데이터 가져오기
            current_status = self.get_trading_data()["investment_status"]
            recent_trades = self.db_manager.get_recent_trades(6)  # 최근 6개 거래만 분석



            # 트레이드가 없는 경우 처리
            if not recent_trades:
                return {
                    "strategy_analysis": "No recent trades available",
                    "key_patterns": "Cannot identify patterns",
                    "improvement_suggestions": "Insufficient trading history"
                }

            # Summarize trade history
            trades_summary = "\n".join([
                f"Time: {trade[0]}, Action: {trade[1]}, Result: {self.calculate_trade_result(trade, current_status)}"
                for trade in recent_trades
            ])

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-2024-08-06",
                messages=[
                    {
                        "role": "system",
                        "content": """As a trading analyst, review the Bitcoin trading history and analyze:
                           1. Characteristics of profitable trades
                           2. Patterns in trades that resulted in losses
                           3. Effectiveness of technical indicator usage
                           4. Trading strategies that need improvement
                           5. Key points to consider for future trades"""
                    },
                    {
                        "role": "user",
                        "content": f"""Recent Trading History:
                           {trades_summary}
                           
                           Please analyze these trades and provide insights for future trading decisions."""
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "trading_reflection",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "strategy_analysis": {"type": "string"},
                                "key_patterns": {"type": "string"},
                                "improvement_suggestions": {"type": "string"}
                            },
                            "required": ["strategy_analysis", "key_patterns", "improvement_suggestions"],
                            "additionalProperties": False
                        }
                    }
                },
                max_tokens=500
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error getting trading reflection: {e}")
            import traceback
            traceback.print_exc()  # 전체 스택 트레이스 출력
            return {
                "strategy_analysis": "Error occurred during analysis",
                "key_patterns": "Unable to identify patterns",
                "improvement_suggestions": f"Analysis failed: {str(e)}"
            }

    def get_ai_decision(self, trading_data: Dict[str, Any], chart_image_base64: str) -> Dict[str, Any]:
        """Get trading decision from AI with comprehensive analysis"""
        try:
            # 데이터 요약 준비
            trading_summary = self.prepare_trading_summary(trading_data)

            # 트리거 정보 준비
            current_time = datetime.now()
            current_price = float(pyupbit.get_current_price("KRW-BTC"))

            last_trade = self.db_manager.get_recent_trades(1)
            last_trade_price = None
            if last_trade and last_trade[0][3] is not None:
                try:
                    last_trade_price = float(last_trade[0][3]) if last_trade and last_trade[0][3] is not None else None
                except ValueError:
                    logger.error(f"Invalid last_trade_price value: {last_trade[0][3]}")
                    last_trade_price = None

            # 변동성 계산
            try:
                if last_trade_price is not None:
                    price_change_percent = abs((current_price - last_trade_price) / last_trade_price * 100)
                else:
                    price_change_percent = 0  # 기본값
            except Exception as e:
                logging.error(f"Error calculating price change: {e}")
                price_change_percent = 0

            logging.error(f"Price chage percent : {price_change_percent} {last_trade_price} {current_price}")

            time_since_last_trade = None
            if last_trade:
                last_trade_time = last_trade[0][0]  # timestamp는 첫 번째 요소
                if isinstance(last_trade_time, str):
                    last_trade_time = datetime.fromisoformat(last_trade_time)
                time_since_last_trade = (current_time - last_trade_time).total_seconds() / 3600

            # 거래 트리거 컨텍스트 준비
            trading_context = {
                "regular_interval": True if time_since_last_trade and time_since_last_trade >= 2 else False,
                "price_volatility": price_change_percent,
                "hours_since_last_trade": time_since_last_trade
            }

            #최근 회고 데이터 가져오기
            latest_reflection = self.db_manager.get_latest_reflection()
            if not latest_reflection:
                latest_reflection = {
                    "strategy_analysis": "No past reflections available.",
                    "key_patterns": "No patterns identified.",
                    "improvement_suggestions": "No suggestions available."
                }

            try:
                #GPT에게 전달
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a Bitcoin trading expert. You analyze the data provided to you and make decisions that will maximize your profitability.:
                                        - Recent price trends and volume
                                        - Technical indicators (RSI, MACD, BB)
                                        - Order book depth
                                        - Fear and Greed Index (not much important)
                                        - Use the provided chart image for reference
                                        - Past trade reflections
                                        - recent news headlines about btc
                                        
                                        Consider these important contextual factors:
                                        - Regular trading checks occur every 1 hours
                                        - Consider both the technical indicators and the timing of trades                                    
                        """
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"""Current Market Analysis:
                                            {trading_summary['market_status']}
                                            
                                            Technical Analysis:
                                            {trading_summary['technical_analysis']}
                                            
                                            Market Depth Analysis:
                                            {trading_summary['market_depth']}
                                            
                                             Trading Context:
                                            - Regular 2-hour interval check: {'Yes' if trading_context['regular_interval'] else 'No'}
                                            - Hours since last trade: {trading_context['hours_since_last_trade']} hours
                                            - Recent price volatility: {trading_context['price_volatility']}%
                                            
                                            Fear & Greed Index:
                                            {trading_data.get('fear_greed_index', 'Not available')}
                                            
                                            Recent News Headlines:
                                            {chr(10).join([f"- [{news['date']}] {news['title']}" for news in trading_data.get('news_headlines', [])])}
                                            
                                            Reflection on Previous Trades:
                                            - Strategy Analysis: {latest_reflection.get('strategy_analysis', 'No data available')}
                                            - Key Patterns: {latest_reflection.get('key_patterns', 'No data available')}
                                            - Improvement Suggestions: {latest_reflection.get('improvement_suggestions', 'No data available')}
                                        """
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{chart_image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "trading_decision",
                            "strict": True,
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "decision": {"type": "string", "enum": ["buy", "sell", "hold"]},
                                    "percentage": {"type": "number"},
                                    "reason": {"type": "string"},
                                    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                                    "confidence": {"type": "integer"}
                                },
                                "required": ["decision", "percentage", "reason", "risk_level", "confidence"],
                                "additionalProperties": False
                            }
                        }
                    },
                    max_tokens=500
                )

                # 응답 내용 로그 추가
                logger.info(f"GPT Response: {response.choices[0].message.content}")

            except openai.error.InvalidRequestError as e:
                logger.error(f"Error in GPT request: {e}")
                return {
                    "decision": "hold",
                    "percentage": 0,
                    "reason": f"Error occurred: {str(e)}",
                    "risk_level": "high",
                    "confidence": 0
                }

            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error getting AI decision: {e}")
            return {
                "decision": "hold",
                "percentage": 0,
                "reason": f"Error: {str(e)}",
                "risk_level": "high",
                "confidence": 0
            }

    def trading_cycle(self, trigger: str = "schedule", additional_data: Dict = None):
        """
        거래 사이클 실행
        Args:
            trigger: 트리거 타입 (schedule/price_change/initial)
            additional_data: 추가 데이터 (가격 변동 등)
        """
        logger.info(f"Starting trading cycle. Trigger: {trigger}")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if self.config.ENVIRONMENT == 'EC2':
                debug_dir = "/home/ubuntu/bitcoin_chart_debug"
            else:
                debug_dir = os.path.join(os.path.expanduser("~"), "bitcoin_chart_debug")

            os.makedirs(debug_dir, exist_ok=True)
            screenshot_path = os.path.join(debug_dir, f"chart_screenshot_{timestamp}.png")

            # 1. Collect data
            trading_data = self.get_trading_data()
            chart_image_base64 = self.capture_chart()
            fgi_data = self.fetch_fear_greed_index()
            news_data = self.fetch_google_news()

            if not chart_image_base64:
                logger.error("Failed to capture chart image.")
                return

            # GPT 판단에 사용될 데이터 준비
            technical_data = {
                "daily": trading_data['technical_summary']['daily'],
                "hourly": trading_data['technical_summary']['hourly']
            }

            market_conditions = {
                "current_price": trading_data['investment_status']['current_price'],
                "orderbook": trading_data.get('orderbook', {}),
                "price_change": additional_data.get('price_change_percent', 0.0) if additional_data else 0.0
            }

            trading_volume = {
                "orderbook_units": trading_data.get('orderbook', {}).get('orderbook_units', [])
            }

            # Add additional market data
            trading_data['fear_greed_index'] = fgi_data
            trading_data['news_headlines'] = news_data

            # 2. Get AI decision
            decision = self.get_ai_decision(trading_data, chart_image_base64)

            # 3. Execute trade
            trade_executed = self.execute_trade(decision)

            # 4. Log results
            if trade_executed:
                # 거래 후 최신 상태 수집
                current_status = self.get_trading_data()["investment_status"]

                # 최신 상태로 거래 회고 분석
                reflection = self.get_trading_reflection()

                trade_data = {
                    **decision,
                    **current_status,
                    **reflection,
                    "trigger_type": trigger,
                    "chart_path": screenshot_path,
                    "price_change_percent": additional_data.get('price_change_percent', 0.0) if additional_data else 0.0,
                    "reflection": f"Trade executed successfully: {decision['reason']}",
                    # GPT 판단 데이터 추가
                    "technical_indicators": technical_data,
                    "market_conditions": market_conditions,
                    "trading_volume": trading_volume,
                    "fear_greed_data": fgi_data,
                    "news_sentiment": news_data
                }

                self.db_manager.log_trade(trade_data)
                logger.info(f"Trade executed and logged. Trigger: {trigger}")
                logger.info(f"Trading Reflection: {reflection}")

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")


def main():
    """Main function to initialize and run the trading bot"""
    config = TradingConfig()
    bot = TradingBot(config)

    print(f"ENVIRONMENT={os.getenv('ENVIRONMENT')}")
    print(f"Simulation Mode: {os.getenv('ENVIRONMENT', 'local').lower() != 'ec2'}")

    # 가격 모니터링 시작
    bot.start_price_monitoring()

    # Schedule trading cycles
    schedule.every(config.TRADING_INTERVAL).hours.do(bot.trading_cycle, trigger="schedule")

    # # 첫 거래 분석 실행
    bot.trading_cycle(trigger="initial")

    logger.info(f"Trading bot started. Running every {config.TRADING_INTERVAL} hours")

    # 매일 정리 스케줄
    schedule.every().day.at("00:00").do(lambda: maintain_debug_directory(bot.debug_dir, config))

    # Keep the script running
    while True:
        try:
            schedule.run_pending()
            time.sleep(config.SCHEDULE_CHECK_INTERVAL)  # 1분마다 체크
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(300)  # 에러 발생 시 5분 대기


if __name__ == "__main__":
    main()