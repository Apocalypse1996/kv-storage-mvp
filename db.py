from __future__ import annotations

import datetime
import os
import tempfile
import uuid as uuid
import jsonpickle

from glob import glob
from pathlib import Path
from typing import List, TextIO
from pydantic import BaseModel, Field, ConfigDict

DATA_KEY = 'Data'
TRANSACTIONS_KEY = 'Transactions'


class DBManager:
    base_dir = 'db_static'

    @classmethod
    def open_db(cls) -> TextIO:
        Path(cls.base_dir).mkdir(parents=True, exist_ok=True)
        path = os.path.abspath(f'{cls.base_dir}/db.json')

        try:
            connection = open(path, mode='r+')
        except FileNotFoundError:
            connection = open(path, mode='w+')

        try:
            data = cls.read_db(connection)
            if not data:
                cls.write_db(connection, {DATA_KEY: {}, TRANSACTIONS_KEY: []})
            return connection
        except Exception:
            connection.close()
            raise

    @classmethod
    def read_db(cls, c: TextIO):
        c.seek(0)
        data = c.read()
        c.seek(0)
        return jsonpickle.loads(data or 'null')

    @classmethod
    def write_db(cls, c: TextIO, data):
        if isinstance(data, dict):
            json_data = jsonpickle.dumps(data)
            c.seek(0)
            c.truncate(0)
            c.write(json_data)
            c.seek(0)

    @classmethod
    def get(cls, key: str):
        """Пункт ТЗ: получить значение по ключу."""
        connection = cls.open_db()

        try:
            data = cls.read_db(connection)[DATA_KEY]
            return data.get(key)
        except Exception:
            raise
        finally:
            connection.close()

    @classmethod
    def get_keys_by_value(cls, value: str) -> list:
        """Пункт ТЗ: найти все ключи, у которых значения равны искомому;"""
        connection = cls.open_db()

        try:
            data = cls.read_db(connection)[DATA_KEY]
            return list(dict(filter(lambda item: item[1] == value, data.items())).keys())
        except Exception:
            raise
        finally:
            connection.close()

    @classmethod
    def bulk_create_or_update(cls, data: dict) -> Transaction:
        """Пункт ТЗ: сохранить значение по ключу;"""

        operations = []
        for key, value in data.items():
            operations.append(TransactionOperation(key=str(key), value=str(value), is_edit=True))
        return Transaction(operations=operations).commit()

    @classmethod
    def bulk_delete(cls, keys: list) -> Transaction:
        """Пункт ТЗ: удалить значение по ключу."""

        operations = []
        for key in keys:
            operations.append(TransactionOperation(key=str(key), is_delete=True))
        return Transaction(operations=operations).commit()


class TransactionOperation(BaseModel):
    """Операции, из которых состоит транзакция"""

    key: str
    value: str = None
    old_value: str = None
    is_edit: bool = False
    is_delete: bool = False

    def modify_data(self, data):
        """Модифицируем данные базы без сохранения"""

        self.old_value = data[DATA_KEY].get(self.key)
        if self.is_edit:
            data[DATA_KEY][self.key] = self.value
        if self.is_delete:
            try:
                del data[DATA_KEY][self.key]
            except KeyError:
                pass
        return data

    def rollback_data(self, data):
        """Откатываем данные базы без сохранения"""

        if self.old_value is not None:
            data[DATA_KEY][self.key] = self.old_value
        else:
            try:
                del data[DATA_KEY][self.key]
            except KeyError:
                pass
        return data


def transaction_lock(foo):
    """Создаём временный файл, что отслеживать блокировку или райзим ошибку, если он ужу есть."""

    # Пункт ТЗ:
    # если открывается транзакция, то сервис становится read-only для других
    # клиентов до коммита или роллбэка;
    # - на попытку записи другим клиентом во время открытой транзакции приложение
    # отвечает ошибкой.
    def wrapper(*args, **kwargs):
        if glob(os.path.abspath('db_static/lock*')):
            raise TransactionLockedException()

        with tempfile.NamedTemporaryFile(dir='db_static', prefix='lock'):
            return foo(*args, **kwargs)

    return wrapper


class Transaction(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    uuid: str = Field(default_factory=uuid.uuid4)
    dt: str = Field(default_factory=datetime.datetime.utcnow().timestamp)
    operations: List[TransactionOperation]

    @transaction_lock
    def commit(self):
        """Пункт ТЗ: сделать коммит (коммитятся все вложенные операции)."""

        connection = DBManager.open_db()

        try:
            data = DBManager.read_db(connection)

            for operation in self.operations:
                data = operation.modify_data(data)

            data[TRANSACTIONS_KEY].append(self)

            connection.seek(0)
            DBManager.write_db(connection, data)
        except Exception:
            raise
        finally:
            connection.close()

        return self

    @classmethod
    @transaction_lock
    def rollback_latest(cls):
        """Пункт ТЗ: сделать роллбэк (откатывается последняя транзакция);"""

        connection = DBManager.open_db()

        try:
            data = DBManager.read_db(connection)
            transactions = data[TRANSACTIONS_KEY]

            try:
                transaction = transactions[-1]
            except IndexError:
                return None

            for operation in transaction.operations:
                data = operation.rollback_data(data)

            data[TRANSACTIONS_KEY].remove(transaction)
            DBManager.write_db(connection, data)
        except Exception:
            raise
        finally:
            connection.close()

        return transaction


class TransactionLockedException(BaseException):
    pass
