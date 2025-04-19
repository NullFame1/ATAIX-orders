import json
import requests
import sys

# Константы
CONFIG_FILE = "config.json"
ORDERS_FILE = "orders_data.json"
HISTORY_FILE = "history.txt"
BASE_URL = "https://api.ataix.kz"

# Загрузка API-ключа
def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
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

# Вспомогательные функции
def write_to_history(order, action="Перезапуск Продажи: "):
    try:
        # Используем averagePrice, если он есть, иначе обычную price
        price_str = order.get('averagePrice') or order.get('price')
        price = round(float(price_str), 4)

        commission = order.get('cumCommission', '0')
        order_id = order.get('orderID')

        with open(HISTORY_FILE, "a", encoding="utf-8") as file:
            original_id = order.get('originalID', order['orderID'])
            log_line = (f"{action} OrderID {order_id}, "
                        f"цена {price}, кол-во {order['quantity']}, символ {order['symbol']}, "
                        f"время {order['created']}, originalID {original_id}, комиссия {commission}\n")
            file.write(log_line)

        print(f"[DEBUG] Ордер {order_id} (originalID {original_id}) записан в history.txt с ценой {price}.")
    except Exception as e:
        print(f"[ERROR] Ошибка при записи в history.txt: {e}")











def update_order_status(order_id, status):
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as file:
            orders = json.load(file)

        for order in orders:
            if order["orderID"] == order_id:
                order["status"] = status
                print(f"[DEBUG] Обновлен статус ордера {order_id} на {status}")
                break

        with open(ORDERS_FILE, "w", encoding="utf-8") as file:
            json.dump(orders, file, indent=4, ensure_ascii=False)
        print(f"[DEBUG] Статус ордера {order_id} успешно обновлен в файле.")
    except Exception as e:
        print(f"[ERROR] Ошибка при обновлении статуса ордера: {e}")

def remove_order(order_id):
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as file:
            orders = json.load(file)

        orders = [order for order in orders if order["orderID"] != order_id]

        with open(ORDERS_FILE, "w", encoding="utf-8") as file:
            json.dump(orders, file, indent=4, ensure_ascii=False)

        print(f"[DEBUG] Ордер {order_id} удален из orders_data.json.")
    except Exception as e:
        print(f"[ERROR] Ошибка при удалении ордера: {e}")

def create_orders(pair, price, quantity):
    print(f"DEBUG: Создание ордера -> пара: {pair}, цена: {price} USDT, кол-во: {quantity}")

    order_data = {
        "symbol": pair,
        "side": "sell",  # Продажа
        "type": "limit",
        "quantity": quantity,  # Используем количество токенов из старого ордера
        "price": price
    }

    response = AtaixAPI.post("/api/orders", order_data)

    if isinstance(response, dict) and "result" in response:
        return {
            "orderID": response["result"]["orderID"],
            "price": response["result"]["price"],
            "quantity": response["result"]["quantity"],
            "symbol": response["result"]["symbol"],
            "created": response["result"]["created"],
            "status": response["result"].get("status", "NEW"),
            "side": "sell",
            "cumCommission": response["result"].get('cumCommission')
        }
    else:
        print("Ошибка при создании ордера.")
        return None

# Основная функция для ордеров на продажу
def scan_sell_orders():
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as file:
            orders = json.load(file)

        for order in orders:
            order_id = order["orderID"]
            side = order.get("side", "buy")
            print(f"[INFO] Проверяем ордер с ID: {order_id}, side: {side}")

            if side.lower() != "sell":
                continue  # Пропускаем ордера не на продажу

            if order.get("is_recreated", False):
                continue  # Пропускаем ордера, которые уже были пересозданы

            order_status_response = AtaixAPI.get(f"/api/orders/{order_id}")
            if order_status_response:
                status_from_api = order_status_response.get("result", {}).get("status")
                if status_from_api:
                    if status_from_api == "filled":
                        print(f"[INFO] Ордер {order_id} выполнен (filled). Обновляем статус.")
                        update_order_status(order_id, "filled")

                        order.update(order_status_response["result"])

                        write_to_history(order, action="\nПродажа: ")
                        remove_order(order_id)
                    elif status_from_api == "new":
                        print(f"[INFO] Ордер {order_id} не выполнен (new). Готовим к отмене и пересозданию.")

                        user_input = input(f"\n[ВНИМАНИЕ] Ордер с ID {order_id} (символ: {order['symbol']}, цена: {order['price']} USDT) не выполнен. Введите 'yes' для отмены и пересоздания: ").strip().lower()
                        if user_input == "yes":
                            delete_response = AtaixAPI.delete(f"/api/orders/{order_id}")
                            if delete_response:
                                # Сохраняем в history только старый ордер
                                write_to_history(order, action="Перезапуск Продажи: ")

                                # Удаляем старый ордер
                                remove_order(order_id)

                                # Создаем новый ордер
                                price = float(order["price"])
                                quantity = float(order["quantity"])
                                new_price = round(price * 0.99, 4)
                                new_order = create_orders(order["symbol"], new_price, quantity)

                                if new_order:
                                    new_order["originalID"] = order.get("originalID", order["orderID"])

                                    with open(ORDERS_FILE, "r", encoding="utf-8") as file:
                                        updated_orders = json.load(file)

                                    updated_orders.append(new_order)

                                    with open(ORDERS_FILE, "w", encoding="utf-8") as file:
                                        json.dump(updated_orders, file, indent=4, ensure_ascii=False)

                                    print(f"[INFO] Новый ордер с ID {new_order['orderID']} успешно добавлен.")

                                    # НЕ нужно снова писать новый ордер в history!
                                    # Только старый ордер должен попасть в лог
                                    order["is_recreated"] = True
                            else:
                                print(f"[ERROR] Не удалось удалить ордер {order_id}. Пересоздание отменено.")
                        else:
                            print(f"[ОТМЕНА] Отмена и пересоздание ордера {order_id} не подтверждены. Переход к следующему ордеру.")
                    else:
                        print(f"[INFO] Ордер {order_id} в статусе {status_from_api}. Статус не изменяем.")
                else:
                    print(f"[ERROR] Статус ордера {order_id} не получен.")
            else:
                print(f"[ERROR] Ошибка при получении статуса ордера {order_id}.")
    except Exception as e:
        print(f"[ERROR] Ошибка при сканировании ордеров на продажу: {e}")









# Запуск
if __name__ == "__main__":
    while True:
        scan_sell_orders()
        user_input = input('\nВведите "start" чтобы запустить снова или "exit" чтобы выйти: ').strip().lower()
        if user_input == "start":
            print("Перезапуск сканирования ордеров на продажу...")
        else:
            print('Выход из программы.')
            break

