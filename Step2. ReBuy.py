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
def write_to_history(order, action="ПЕРЕЗАПУСК Buy: ", no_lowering=False):
    try:
        order_id = order.get('orderID') or order.get('id')
        original_id = order.get('originalID') or order_id

        # Проверяем только для "ПОКУПКА:"
        if action.strip().startswith("ПОКУПКА"):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as file:
                    history_lines = file.readlines()

                for line in history_lines:
                    if f"ПОКУПКА:  OrderID {order_id}" in line:
                        print(f"[INFO] Ордер {order_id} уже записан в history.txt. Пропускаем запись.")
                        return  # Уже записан — выходим
            except FileNotFoundError:
                # Файл может отсутствовать — это нормально
                pass

        price_to_record = order.get('price')
        commission = order.get('cumCommission', '0')

        with open(HISTORY_FILE, "a", encoding="utf-8") as file:
            log_line = (
                f"{action} OrderID {order_id}, "
                f"цена {price_to_record}, "
                f"кол-во {order['quantity']}, "
                f"символ {order['symbol']}, "
                f"время {order['created']}, "
                f"originalID {original_id}, "
                f"комиссия {commission}\n"
            )
            file.write(log_line)

        print(f"[DEBUG] Ордер {order_id} записан в history.txt с ценой {price_to_record} и комиссией {commission}.")
    except Exception as e:
        print(f"[ERROR] Ошибка при записи в history.txt: {e}")















def update_order_status(order_id, status, updated_data=None):
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as file:
            orders = json.load(file)

        for order in orders:
            if order["orderID"] == order_id:
                old_status = order["status"]
                order["status"] = status

                if status == "filled" and old_status != "filled":
                    if updated_data:
                        # Обновляем ордер актуальными данными из API
                        order["cumCommission"] = updated_data.get("cumCommission", order.get("cumCommission", "0"))
                        order["price"] = updated_data.get("averagePrice", order.get("price"))
                        order["created"] = updated_data.get("created", order.get("created"))
                        order["quantity"] = updated_data.get("cumQuantity", order.get("quantity"))  # если нужно

                    write_to_history(order, action="\nПОКУПКА: ", no_lowering=True)

                print(f"[DEBUG] Обновлен статус ордера {order_id} на {status}")
                break

        with open(ORDERS_FILE, "w", encoding="utf-8") as file:
            json.dump(orders, file, indent=4, ensure_ascii=False)
        print(f"[DEBUG] Статус и данные ордера {order_id} успешно обновлены в файле.")
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

def create_orders(pair, price, quantity, original_id=None):
    print(f"DEBUG: Создание ордера -> пара: {pair}, цена: {price} USDT, кол-во: {quantity}")

    order_data = {
        "symbol": pair,
        "side": "buy",
        "type": "limit",
        "quantity": quantity,
        "price": price
    }

    response = AtaixAPI.post("/api/orders", order_data)

    if isinstance(response, dict) and "result" in response:
        result = response["result"]
        new_order = {
            "orderID": result["orderID"],
            "price": result["price"],
            "quantity": result["quantity"],
            "symbol": result["symbol"],
            "created": result["created"],
            "status": result.get("status", "NEW"),
            "originalID": original_id if original_id else result["orderID"],
            "cumCommission": result.get("cumCommission", "0")  # <---- Теперь всегда добавляем
        }

        # Если сразу выполнен, пишем в историю
        if new_order["status"].lower() == "filled":
            new_order["price"] = result.get("averagePrice", new_order["price"])
            write_to_history(new_order, action="\nПОКУПКА: ", no_lowering=True)

        return new_order
    else:
        print("Ошибка при создании ордера.")
        return None









# Основная функция
def scan_orders():
    try:
        # Открываем файл ордеров
        with open(ORDERS_FILE, "r", encoding="utf-8") as file:
            orders = json.load(file)

        orders_to_restart = []

        # Обрабатываем каждый ордер из списка
        for order in orders:
            order_id = order["orderID"]
            side = order.get("side", "buy")
            status = order.get("status", "").lower()

            # Если ордер уже выполнен, пропускаем его
            if status == "filled":
                print(f"[INFO] Ордер {order_id} уже выполнен (filled). Пропускаем проверку.")
                continue

            print(f"[INFO] Проверяем ордер с ID: {order_id}, side: {side}")

            # Пропускаем ордера на продажу
            if side.lower() == "sell":
                print(f"[INFO] Ордер {order_id} на продажу (sell). Пропускаем.")
                continue

            # Запрашиваем актуальный статус ордера
            order_status_response = AtaixAPI.get(f"/api/orders/{order_id}")
            if order_status_response:
                status_from_api = order_status_response.get("result", {}).get("status")
                if status_from_api:
                    # Если ордер выполнен, обновляем статус и записываем в историю
                    if status_from_api == "filled":
                        print(f"[INFO] Ордер {order_id} выполнен (filled). Обновляем статус.")
                        update_order_status(order_id, "filled", updated_data=order_status_response["result"])
                        write_to_history(order_status_response["result"], action="\nПОКУПКА: ", no_lowering=True)
                    # Если ордер новый, добавляем в список для пересоздания
                    elif status_from_api == "new":
                        print(f"[INFO] Ордер {order_id} не выполнен (new). Готовим к отмене и пересозданию.")
                        orders_to_restart.append(order)
                    else:
                        print(f"[INFO] Ордер {order_id} в статусе {status_from_api}. Статус не изменяем.")
                else:
                    print(f"[ERROR] Статус ордера {order_id} не получен.")
            else:
                print(f"[ERROR] Ошибка при получении статуса ордера {order_id}.")

        # Обрабатываем ордера, которые нужно пересоздать
        if orders_to_restart:
            for order in orders_to_restart:
                print(f"\n[ВНИМАНИЕ] Найден ордер для отмены и пересоздания: {order['orderID']} (пара {order['symbol']}, цена {order['price']}, кол-во {order['quantity']})")
                user_input = input("Введите 'yes' чтобы подтвердить пересоздание этого ордера: ").strip().lower()
                if user_input == "yes":
                    order_id = order["orderID"]

                    # 1. Запрашиваем актуальные данные ордера
                    order_status_response = AtaixAPI.get(f"/api/orders/{order_id}")
                    if order_status_response and "result" in order_status_response:
                        result = order_status_response["result"]

                        # 2. Обновляем ордер локально в orders_data актуальными данными из API
                        try:
                            with open(ORDERS_FILE, "r", encoding="utf-8") as file:
                                orders_data = json.load(file)

                            for o in orders_data:
                                if o["orderID"] == order_id:
                                    o.update(result)  # Обновляем ордер с новыми данными из API
                                    break

                            # 3. Записываем обновленные данные обратно в файл
                            with open(ORDERS_FILE, "w", encoding="utf-8") as file:
                                json.dump(orders_data, file, indent=4, ensure_ascii=False)

                            print(f"[DEBUG] Ордер {order_id} обновлен актуальными данными перед перезапуском.")
                        except Exception as e:
                            print(f"[ERROR] Ошибка при обновлении ордера {order_id}: {e}")

                        # 4. Обновляем ордер локально для записи в историю
                        order.update(result)  # Обновляем данные ордера перед записью в историю

                    # 5. Пишем в историю
                    write_to_history(order, action="ПЕРЕЗАПУСК Buy: ")

                    # 6. Удаляем ордер
                    delete_response = AtaixAPI.delete(f"/api/orders/{order_id}")
                    if delete_response:
                        remove_order(order_id)

                        # 7. Пересоздаем ордер с новой ценой
                        price = float(order["price"])
                        quantity = float(order["quantity"])
                        original_id = order.get("originalID", order["orderID"])
                        new_price = round(price * 1.01, 4)  # Пересчитываем цену на 1% выше
                        new_order = create_orders(order["symbol"], new_price, quantity, original_id)

                        # 8. Обновляем файл с ордерами
                        if new_order:
                            with open(ORDERS_FILE, "r", encoding="utf-8") as file:
                                updated_orders = json.load(file)

                            updated_orders.append(new_order)

                            with open(ORDERS_FILE, "w", encoding="utf-8") as file:
                                json.dump(updated_orders, file, indent=4, ensure_ascii=False)

                            print(f"[INFO] Новый ордер с ID {new_order['orderID']} успешно добавлен.")
                else:
                    print(f"[ОТМЕНА] Ордер {order['orderID']} пропущен.")

    except Exception as e:
        print(f"[ERROR] Ошибка при сканировании ордеров: {e}")







# Запуск
if __name__ == "__main__":
    while True:
        scan_orders()
        user_input = input('\nВведите "start" чтобы запустить снова или "exit" чтобы выйти: ').strip().lower()
        if user_input == "exit":
            print("Выход из программы.")
            break
        elif user_input == "start":
            print("Перезапуск сканирования...")
        else:
            print('Выход из программы.')
            break

