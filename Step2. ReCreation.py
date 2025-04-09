import json
import requests
import sys

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
    def delete(endpoint):
        """Выполняет DELETE-запрос к API для отмены ордера."""
        try:
            print(f"[DEBUG] DELETE-запрос к {BASE_URL}{endpoint}")
            response = requests.delete(f"{BASE_URL}{endpoint}", headers=AtaixAPI.headers, timeout=20)
            if response.status_code == 200:
                print(f"[DEBUG] Успешное удаление ордера: {response.json()}")
                return response.json()
            else:
                print(f"[ERROR] Ошибка удаления ордера: {response.status_code}, {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ошибка запроса на удаление: {e}")
            return None

    @staticmethod
    def post(endpoint, data):
        """Выполняет POST-запрос для создания нового ордера."""
        try:
            print(f"[DEBUG] POST-запрос к {BASE_URL}{endpoint} с данными: {data}")
            response = requests.post(f"{BASE_URL}{endpoint}", headers=AtaixAPI.headers, json=data, timeout=20)
            if response.status_code == 200:
                print(f"[DEBUG] Успешный ответ от API: {response.json()}")
                return response.json()
            else:
                print(f"[ERROR] Ошибка API: {response.status_code}, {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ошибка запроса на создание ордера: {e}")
            return None


# Функция для обновления статуса ордера в файле
def update_order_status(order_id, status):
    """Обновляет статус ордера в файле orders_data.json"""
    try:
        with open(ORDERS_FILE, "r") as file:
            orders = json.load(file)

        for order in orders:
            if order["orderID"] == order_id:
                order["status"] = status
                print(f"[DEBUG] Обновлен статус ордера {order_id} на {status}")
                break

        with open(ORDERS_FILE, "w") as file:
            json.dump(orders, file, indent=4)
        print(f"[DEBUG] Статус ордера {order_id} успешно обновлен в файле.")
    except Exception as e:
        print(f"[ERROR] Ошибка при обновлении статуса ордера: {e}")

# Функция для создания нового ордера с 1% выше цены
def create_orders(pair, price):
    """Создает ордер на покупку по заданной цене."""
    print(f"DEBUG: Создание ордера -> пара: {pair}/USDT, цена: {price} USDT, кол-во: 1")

    symbol = f"{pair}"
    
    order_data = {
        "symbol": symbol,
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


# Функция для сканирования ордеров
def scan_orders():
    """Сканирует ордера, проверяет их статус и обновляет статус в файле, если ордер выполнен."""
    try:
        with open(ORDERS_FILE, "r") as file:
            orders = json.load(file)

        for order in orders:
            order_id = order["orderID"]
            print(f"[INFO] Проверяем ордер с ID: {order_id}")

            order_status_response = AtaixAPI.get(f"/api/orders/{order_id}")
            if order_status_response:
                status_from_api = order_status_response.get("result", {}).get("status")
                if status_from_api:
                    # Если ордер выполнен, обновляем статус в файле
                    if status_from_api == "filled":
                        print(f"[INFO] Ордер {order_id} выполнен (filled). Обновляем статус.")
                        update_order_status(order_id, "filled")
                    elif status_from_api == "new":
                        print(f"[INFO] Ордер {order_id} не выполнен (статус: {status_from_api}). Отменяем ордер и создаем новый с ценой на 1% выше.")
                        
                        # Отменяем ордер
                        delete_response = AtaixAPI.delete(f"/api/orders/{order_id}")
                        if delete_response:
                            # Обновляем статус ордера в файле на "cancelled"
                            update_order_status(order_id, "cancelled")
                            
                            # Создаем новый ордер с ценой на 1% выше
                            price = float(order["price"])
                            new_price = round(price * 1.01, 4)
                            new_order = create_orders(order["symbol"], new_price)
                            
                            if new_order:
                                # Сохранение нового ордера в файл
                                with open(ORDERS_FILE, "r") as file:
                                    orders = json.load(file)
                                orders.append(new_order)

                                with open(ORDERS_FILE, "w") as file:
                                    json.dump(orders, file, indent=4)

                                print(f"[INFO] Новый ордер с ID {new_order['orderID']} успешно добавлен в файл.")
                    else:
                        print(f"[INFO] Ордер {order_id} не выполнен (статус: {status_from_api}). Статус остаётся без изменений.")
                else:
                    print(f"[ERROR] Ошибка получения статуса ордера {order_id}. Ответ API: {order_status_response}")
            else:
                print(f"[ERROR] Не удалось получить статус ордера {order_id}. Ответ API: {order_status_response}")
                
    except Exception as e:
        print(f"[ERROR] Ошибка при сканировании ордеров: {e}")

# Запуск сканирования ордеров
if __name__ == "__main__":
    scan_orders()
