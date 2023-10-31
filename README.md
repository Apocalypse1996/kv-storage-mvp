# Запустить веб-приложение локально:
1. Перейти в папку с проектом;
2. создать и запустить виртуальное окружение;
3. установить зависимости requirements.txt;
4. Запусить wsgi.py

# Запустить, через докер: 
1. Перейти в папку с проектом/devops
2. docker-compose up --build

# Операции

import requests
<br />
import json
<br />
from db import Transaction, TransactionOperation
<br />
<br />
base_url = 'http://127.0.0.1:8080'
<br />
headers = {
    'Content-Type': 'application/json'
}
<br />
##### сохранить значение по ключу
requests.post(f'{base_url}/edit/', headers=headers, data=json.dumps(
    {
        'key_1': '1',
        'key_2': '2',
        'key_3': '3',
        'key_4': '4',
        'key_5': '5',
    }
))
<br />
##### получить значение по ключу
response = requests.get(f'{base_url}/get/value_by_key/', params={'q': 'key_1'})
<br />
print(response.json())
<br />
##### удалить значение по ключу
requests.post(f'{base_url}/delete/', headers=headers, data=json.dumps(['key_1', 'key_2', 'key_3']))
<br />
##### найти все ключи, у которых значения равны искомому
response = requests.get(f'{base_url}/get/keys_by_value/', params={'q': '1'})
<br />
print(response.json())
<br />
##### открыть транзакцию (можно открыть вложенные одна в другую транзакции, как матрешка);
transaction = Transaction(operations=[
    TransactionOperation(key='key_1', value='1', is_edit=True),
    TransactionOperation(key='key_2', value='2', is_edit=True),
    TransactionOperation(key='key_2', value='2', is_delete=True),
])
<br />

##### сделать коммит (коммитятся все вложенные операции).
transaction.commit()
<br />

##### сделать роллбэк (откатывается последняя транзакция)
Transaction.rollback_latest()

#### Примечание
1. Блокировка транзакций просиходит, только при вызове операций .commit() или .rollback_latest(), 
так как они изменяют состояние БД. Смотрим db.transaction_lock
