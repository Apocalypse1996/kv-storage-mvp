import datetime
import os
import uuid as uuid
import jsonpickle

from pathlib import Path
from functools import wraps
from typing import List
from pydantic import BaseModel, Field

Path("db_static").mkdir(parents=True, exist_ok=True)

DB_PATH = os.path.abspath('db_static/db.json')
TRANSACTIONS_PATH = os.path.abspath('db_static/transactions.json')


def read_db(path=DB_PATH, default_content='{}'):
    """Открываем файл и передаём функции его содержимое"""

    def read(foo):
        @wraps(foo)
        def wrapper(*args, **kwargs):
            if not os.path.isfile(path):
                with open(path, mode='w') as connection:
                    connection.write(default_content)

            with open(path, mode='r') as connection:
                return foo(*args, **kwargs, data=jsonpickle.loads(connection.read()))

        return wrapper

    return read


class TransactionOperation(BaseModel):
    """Операции, из которых состоит транзакция"""

    key: str
    value: str = None
    old_value: str = None
    is_edit: bool = False
    is_delete: bool = False

    def modify_data(self, data):
        self.old_value = data.get(self.key)
        if self.is_edit:
            data[self.key] = self.value
        if self.is_delete:
            try:
                del data[self.key]
            except KeyError:
                pass
        return data

    def rollback_data(self, data):
        if self.old_value is not None:
            data[self.key] = self.old_value
        else:
            try:
                del data[self.key]
            except KeyError:
                pass
        return data


class Transaction(BaseModel):
    uuid: str = Field(default_factory=uuid.uuid4)
    dt: str = Field(default_factory=datetime.datetime.utcnow().timestamp)
    operations: List[TransactionOperation]

    @read_db()
    def _open(self, data: dict):
        """Пункт: открыть транзакцию"""

        for operation in self.operations:
            data = operation.modify_data(data)
        return data

    @read_db(path=TRANSACTIONS_PATH, default_content='[]')
    def _save(self, data: list):
        data.append(self)
        data = jsonpickle.dumps(data)
        with open(TRANSACTIONS_PATH, mode='w') as connection:
            connection.write(data)

    @read_db(path=TRANSACTIONS_PATH, default_content='[]')
    def _delete(self, data: list):
        data.remove(self)
        data = jsonpickle.dumps(data)
        with open(TRANSACTIONS_PATH, mode='w') as connection:
            connection.write(data)

    def commit(self):
        """Пункт: сделать коммит (коммитятся все вложенные операции)."""

        data = jsonpickle.dumps(self._open())
        with open(DB_PATH, mode='w') as connection:
            connection.write(data)
        self._save()
        return self

    @classmethod
    @read_db(path=TRANSACTIONS_PATH, default_content='[]')
    def get_transactions(cls, data: list):
        return data

    @read_db()
    def rollback(self, data: dict):
        for operation in self.operations:
            data = operation.rollback_data(data)
        data = jsonpickle.dumps(data)

        with open(DB_PATH, mode='w') as connection:
            connection.write(data)

        self._delete()
        return self

    @classmethod
    def rollback_latest(cls):
        """Пункт: сделать роллбэк (откатывается последняя транзакция);"""
        transactions = cls.get_transactions()
        try:
            transaction = transactions[-1]
        except IndexError:
            return None

        return transaction.rollback()


class DBManagerReadonlyException(BaseException):
    pass


class DBManager:
    is_readonly = False

    @classmethod
    @read_db()
    def get(cls, key: str, data: dict):
        """получить значение по ключу."""
        return data.get(key)

    @classmethod
    @read_db()
    def get_keys_by_value(cls, value: str, data: dict) -> list:
        """найти все ключи, у которых значения равны искомому."""
        return list(dict(filter(lambda item: item[1] == value, data.items())).keys())

    @classmethod
    def _commit_transaction(cls, operations: List[TransactionOperation]) -> Transaction:
        """
        если открывается транзакция, то сервис становится read-only для других клиентов до коммита или роллбэка;
        на попытку записи другим клиентом во время открытой транзакции приложение отвечает ошибкой.
        """

        if cls.is_readonly:
            raise DBManagerReadonlyException()

        cls.is_readonly = True
        try:
            return Transaction(operations=operations).commit()
        except Exception:
            raise
        finally:
            cls.is_readonly = False

    @classmethod
    def bulk_create_or_update(cls, data: dict) -> Transaction:
        """сохранить значение по ключу."""

        operations = []
        for key, value in data.items():
            operations.append(TransactionOperation(key=str(key), value=str(value), is_edit=True))
        return cls._commit_transaction(operations)

    @classmethod
    def bulk_delete(cls, keys: list) -> Transaction:
        """сохранить значение по ключу."""

        operations = []
        for key in keys:
            operations.append(TransactionOperation(key=str(key), is_delete=True))
        return cls._commit_transaction(operations)
