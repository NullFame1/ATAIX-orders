import json
import re
import requests
import sys
import os

# Константы
CONFIG_FILE = "config.json"
ORDERS_FILE = "orders_data.json"
BASE_URL = "https://api.ataix.kz"

# Загрузка API-ключа
def load_config():
    """Загружает API-ключ из config.json и выводит отладочную информацию."""
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            api_key = config.get("api_key")
            if not api_key:
                print("Ошибка: API-ключ не найден в config.json")
                sys.exit(1)
            print("[DEBUG] API-ключ успешно загружен")
            return api_key
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        sys.exit(1)

API_KEY = load_config()

# Класс для работы с API
class AtaixAPI:
    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY
    }

    @staticmethod
    def get(endpoint):
        """Выполняет GET-запрос к API и выводит отладочную информацию."""
        try:
            print(f"[DEBUG] GET-запрос к {BASE_URL}{endpoint}")
            response = requests.get(f"{BASE_URL}{endpoint}", headers=AtaixAPI.headers, timeout=20)
            if response.status_code == 200:
                print(f"[DEBUG] Успешный ответ от API: {response.json()}")
                return response.json()
            else:
                print(f"[ERROR] Ошибка API: {response.status_code}, {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ошибка запроса: {e}")
            return None

    @staticmethod
    def post(endpoint, data):
        """Выполняет POST-запрос к API и выводит отладочную информацию."""
        headers = AtaixAPI.headers.copy()
        headers["Content-Type"] = "application/json"
        try:
            print(f"[DEBUG] POST-запрос к {BASE_URL}{endpoint} с данными: {data}")
            response = requests.post(f"{BASE_URL}{endpoint}", headers=headers, json=data, timeout=20)
            if response.status_code == 200:
                print(f"[DEBUG] Успешный ответ от API: {response.json()}")
                return response.json()
            else:
                print(f"[ERROR] Ошибка API: {response.status_code}, {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ошибка при отправке запроса: {e}")
            return None

# Проверка прав доступа API
def check_api_permissions():
    """Проверяет доступные права API."""
    print("\n[INFO] Проверка прав API...")
    response = AtaixAPI.get("/api/user/info")  # Пример запроса к API для проверки
    if response and isinstance(response, dict):
        print("[INFO] API подключен. Доступные права:")
        for key, value in response.items():
            print(f"  {key}: {value}")
    else:
        print("[ERROR] Не удалось получить информацию о правах API.")

# Вызываем проверку API после загрузки
check_api_permissions()


# Функции обработки данных
def extract_values(text, key):
    """Извлекает значения по ключу из JSON-данных"""
    return re.findall(rf'"{key}":\s*"([^"]+)"', text)

def get_trading_pairs():
    """Возвращает список всех торговых пар"""
    return extract_values(json.dumps(AtaixAPI.get("/api/symbols")), "symbol")

def get_prices():
    """Возвращает список всех цен"""
    return extract_values(json.dumps(AtaixAPI.get("/api/prices")), "lastTrade")

def get_balances():
    """Получает баланс всех валют и выводит его в удобном формате"""
    print("\nДоступный баланс на бирже (только валюты с ненулевым балансом):")
    print("-" * 30)
    print(f"{'Валюта':<10} {'Баланс':>15}")
    print("-" * 30)

    symbols_data = AtaixAPI.get("/api/symbols")
    if not isinstance(symbols_data, dict):
        print("Ошибка получения списка валют.")
        return

    currencies = set(extract_values(json.dumps(symbols_data), "base"))

    for currency in currencies:
        balance_info = requests.get(
            f"{BASE_URL}/api/user/balances/{currency}",
            headers={
                "X-API-Key": API_KEY,
                "Accept": "application/json"
            },
            timeout=10
        ).json()

        # Отладочный вывод
        print(f"DEBUG: Ответ API для {currency} -> {balance_info}")

        if isinstance(balance_info, dict) and balance_info.get("status") is True and "available" in balance_info:
            try:
                available_balance = float(balance_info["available"])
                if available_balance > 0:
                    print(f"{currency:<10} {available_balance:>15.4f}")
            except ValueError:
                print(f"Ошибка: некорректный формат баланса для {currency} -> {balance_info['available']}")

    print("-" * 30)


# Получение списка пар, где цена <= 0.6 USDT
def get_low_price_pairs():
    pairs = get_trading_pairs()
    prices = get_prices()
    low_price_pairs = {pairs[i]: float(prices[i]) for i in range(len(pairs)) if "USDT" in pairs[i] and float(prices[i]) <= 0.6}

    print("\n\nТорговые пары с USDT, где цена ≤ 0.6 USDT:")
    for pair, price in low_price_pairs.items():
        print(f"{pair}\t{price}")

    return low_price_pairs

# Выбор пары
def select_pair(low_price_pairs):
    while True:
        choice = input("Выберите торговую пару --> ").upper()
        if f"{choice}/USDT" in low_price_pairs:
            return choice, low_price_pairs[f"{choice}/USDT"]
        elif choice == "EXIT":
            sys.exit()
        else:
            print("Такой торговой пары нет в списке")

# Выбор процента скидки
def select_discount():
    while True:
        discount = input("Введите процент скидки (2, 5, 8) --> ").strip()
        if discount in ["2", "5", "8"]:
            return int(discount)
        print("Ошибка! Введите 2, 5 или 8.")

# Рассчет цены для ордера
def calculate_order_price(price, discount):
    return round(price * (1 - discount / 100), 4)

# Подтверждение покупки
def confirm_purchase(pair, price):
    print(f"\nБудет создан один ордер на покупку {pair} по цене {price} USDT")
    print('Если согласны, напишите "yes"')
    while True:
        if (response := input("--> ").lower()) == "yes":
            return True
        elif response == "exit":
            sys.exit()

# Создание ордера
def create_orders(pair, price):
    """Создает ордер на покупку по заданной цене."""
    print(f"DEBUG: Создание ордера -> пара: {pair}/USDT, цена: {price} USDT, кол-во: 1")

    order_data = {
        "symbol": f"{pair}/USDT",
        "side": "buy",
        "type": "limit",
        "quantity": 1,
        "price": price
    }

    response = AtaixAPI.post("/api/orders", order_data)

    # Отладочный вывод ответа от API
    print(f"DEBUG: Ответ API -> {response}")

    if isinstance(response, dict) and "result" in response:
        return {
            "orderID": response["result"]["orderID"],
            "price": response["result"]["price"],
            "quantity": response["result"]["quantity"],
            "symbol": response["result"]["symbol"],
            "created": response["result"]["created"],
            "status": response["result"].get("status", "NEW")
        }
    else:
        print("Ошибка при создании ордера.")
        return None


# Сохранение ордера в файл
def save_order(order):
    existing_orders = []
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as file:
            try:
                existing_orders = json.load(file)
            except json.JSONDecodeError:
                pass

    with open(ORDERS_FILE, "w") as file:
        json.dump(existing_orders + [order], file, indent=4)

    print(f"[+] Ордер успешно создан и сохранён в {ORDERS_FILE}. Проверьте его на ATAIX во вкладке 'Мои ордера'.")

# Основной сценарий работы
def main():
    get_balances()
    low_price_pairs = get_low_price_pairs()

    pair, current_price = select_pair(low_price_pairs)
    discount = select_discount()
    order_price = calculate_order_price(current_price, discount)

    if confirm_purchase(pair, order_price):
        order = create_orders(pair, order_price)
        if order:
            save_order(order)
        else:
            print("Ошибка при создании ордера.")

if __name__ == "__main__":
    main()
