import json, re, requests, sys, os

API_KEY = "API"

def get_request(endpoint):                      # Создания URL-запроса на ataix.kz
    url = f"https://api.ataix.kz{endpoint}"
    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY
    }
    response = requests.get(url, headers=headers, timeout=20)
    if response.status_code == 200:
        return response.json()
    else:
        return f"Ошибка: {response.status_code}, {response.text}"

def find_name_currencies(text, word):   # Поиск уникальных валют на бирже
    words = re.findall(r'\b\w+\b', text)
    unique_currencies = set()  # Используем множество для хранения уникальных валют
    for i in range(len(words) - 1):
        if words[i] == word:
            next_word = re.sub(r'[^a-zA-Zа-яА-Я]', '', words[i + 1])
            unique_currencies.add(next_word)
    return unique_currencies

name_currencies = find_name_currencies(json.dumps(get_request("/api/symbols")), "base") # Создани списка уникальных валют торгуемых на бирже
print("Доступный баланс на бирже в токенах USDT")
for currency in name_currencies:    # Вывод имен валют и их баланс на счету
    balance_info = get_request(f"/api/user/balances/{currency}")
    balance = re.search(r"'available':\s*'([\d.]+)'", str(balance_info))
    if balance:
        print(currency , "\t\t" , balance.group(1))

def find_symbols(text, word):
    words = re.findall(r'\b\w+(?:/\w+)?\b', text)
    pair_sym = []
    for i in range(len(words) - 1):
        if words[i] == word:
            next_word = words[i + 1]
            pair_sym.append(next_word)
    return pair_sym

def find_prices(text, word):
    pattern = rf'{word}[\s\W]*([-+]?\d*\.\d+|\d+)'
    matches = re.findall(pattern, text)
    price = []
    for match in matches:
        price.append(match)
    return price

currencies_less_0_6 = []
price_less_0_6_list = {}
symbols = find_symbols(json.dumps(get_request("/api/symbols")), "symbol")
price = find_prices(json.dumps(get_request("/api/prices")), "lastTrade")
print("\n\nТорговая пара с USDT где минимальная цена меньше или равно 0.6 USDT:")
for i in range(len(symbols)):
    if "USDT" in symbols[i] and float(price[i]) <= 0.6:
        print(f"{symbols[i]}\t{price[i]}")
        currencies_less_0_6.append(symbols[i])
        price_less_0_6_list[symbols[i]] = price[i]

while True:
    current_cur = input("Выберите торговую пару (TRX, IMX, 1INCH) --> ").upper()
    if  current_cur + "/USDT" in currencies_less_0_6:
        current_cur = current_cur
        price_less_0_6 = price_less_0_6_list[current_cur + "/USDT"]
        break
    elif current_cur == "EXIT":
        sys.exit()
    else:
        print("Такой торговой пары нет в списке")

print(current_cur, "\t\t", price_less_0_6)
price_2pc = round(float(price_less_0_6)*0.98, 4)
price_5pc = round(float(price_less_0_6)*0.95, 4)
price_8pc = round(float(price_less_0_6)*0.92, 4)
print(f"Следующим шагом будет создано три ордера на покупку токена {current_cur},\nбудет куплено по одному токену с уменьшением цены на\n2%({price_2pc}$), 5%,({price_5pc}$) 8%({price_8pc}$)\nЕсли Вы согласны напишите \"yes\"")

while True:
    x = input("--> ")
    if x == "yes":
        break
    elif x == "exit":
        sys.exit()

def post_orders(symbol, price):                      # Создания URL-запроса на ataix.kz
    url = "https://api.ataix.kz/api/orders"
    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "symbol": symbol,
        "side": "buy",
        "type": "limit",
        "quantity": 1,
        "price": price
    }
    response = requests.post(url, headers=headers, json=data, timeout=20)
    if response.status_code == 200:
        return response.json()
    else:
        return f"Ошибка: {response.status_code}, {response.text}"

order_2pc = post_orders(current_cur + "/USDT", price_2pc)
order_data_2pc = {
    "orderID": order_2pc["result"]["orderID"],
    "status": order_2pc["result"].get("status", "NEW")  # Если статус не найден, ставим "NEW"
}

order_5pc = post_orders(current_cur + "/USDT", price_5pc)
order_data_5pc = {
    "orderID": order_5pc["result"]["orderID"],
    "status": order_5pc["result"].get("status", "NEW")  # Если статус не найден, ставим "NEW"
}

order_8pc = post_orders(current_cur + "/USDT", price_8pc)
order_data_8pc = {
    "orderID": order_8pc["result"]["orderID"],
    "status": order_8pc["result"].get("status", "NEW")  # Если статус не найден, ставим "NEW"
}
orders_list = [order_2pc, order_5pc, order_8pc]
# Файл для хранения данных
filename = "orders_data.json"

# Загружаем старые данные, если файл существует
if os.path.exists(filename):
    with open(filename, "r") as file:
        try:
            orders = json.load(file)
        except json.JSONDecodeError:
            orders = []
else:
    orders = []

# Добавляем новые заказы в список
for order in orders_list:
    order_data = {
        "orderID": order["result"]["orderID"],
        "price": order["result"]["price"],
        "quantity": order["result"]["quantity"],
        "symbol": order["result"]["symbol"],
        "created": order["result"]["created"],
        "status": order["result"].get("status", "NEW")  # Если статуса нет, ставим "NEW"
    }
    orders.append(order_data)

# Записываем в файл
with open(filename, "w") as file:
    json.dump(orders, file, indent=4)

print("[+]Ордера успешно созданы. Для проверки результата посетите сайт ATAIX, вкладка \"Мои ордера\". Данные успешно сохранены в", filename)