# Запустить веб-приложение локально:
1. Перейти в папку с проектом
2. создать и запустить виртуальное окружение
3. установить зависимости requirements.txt
4. Запусить wsgi.py

# Запустить, через докер: 
1. Перейти в папку с проектом/devops
2. docker-compose up --build

# Операции

import requests
from db import Transaction, TransactionOperation

base_url = 'http://127.0.0.1:8080'
headers = {
    'Content-Type': 'application/json'
}

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

##### получить значение по ключу
requests.get(f'{base_url}/get/value_by_key/', params={'q': 'key_1'})

##### удалить значение по ключу
requests.post(f'{base_url}/delete/', headers=headers, data=json.dumps(['key_1', 'key_2', 'key_3']))

##### найти все ключи, у которых значения равны искомому
requests.get(f'{base_url}/get/keys_by_value/', params={'q': '1'})

##### открыть транзакцию (можно открыть вложенные одна в другую транзакции, как матрешка);
transaction = Transaction(operations=[
    TransactionOperation(key='key_1', value='1', is_edit=True),
    TransactionOperation(key='key_2', value='2', is_edit=True),
    TransactionOperation(key='key_2', value='2', is_delete=True),
])
transaction.open_transaction()

##### сделать коммит (коммитятся все вложенные транзакции).
transaction.commit()

##### сделать роллбэк
transaction.rollback() 

##### сделать роллбэк (откатывается последняя транзакция)
Transaction.rollback_latest()