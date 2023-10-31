from __future__ import annotations

import datetime
import os
import uuid as uuid

import jsonpickle

from pathlib import Path
from typing import List, TextIO
from pydantic import BaseModel, Field, ConfigDict

Path("db_static").mkdir(parents=True, exist_ok=True)

TRANSACTIONS_LOCKED_KEY = 'transactions_locked'


class DBManager:
    path = os.path.abspath('db_static/db.json')

    @classmethod
    def open_db(cls) -> TextIO:
        try:
            connection = open(cls.path, mode='r+')
        except FileNotFoundError:
            connection = open(cls.path, mode='w+')

        try:
            data = cls.read_db(connection)
            if not data:
                cls.write_db(connection, {'Data': {}, 'Transactions': []})
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
        """получить значение по ключу."""
        connection = cls.open_db()
        try:
            data = cls.read_db(connection)['Data']
            return data.get(key)
        except Exception:
            raise
        finally:
            connection.close()

    @classmethod
    def get_keys_by_value(cls, value: str) -> list:
        """найти все ключи, у которых значения равны искомому."""
        connection = cls.open_db()

        try:
            data = cls.read_db(connection)['Data']
            return list(dict(filter(lambda item: item[1] == value, data.items())).keys())
        except Exception:
            raise
        finally:
            connection.close()

    @classmethod
    def bulk_create_or_update(cls, data: dict) -> Transaction:
        """сохранить значение по ключу."""

        operations = []
        for key, value in data.items():
            operations.append(TransactionOperation(key=str(key), value=str(value), is_edit=True))
        return Transaction(operations=operations).commit()

    @classmethod
    def bulk_delete(cls, keys: list) -> Transaction:
        """сохранить значение по ключу."""

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

        self.old_value = data['Data'].get(self.key)
        if self.is_edit:
            data['Data'][self.key] = self.value
        if self.is_delete:
            try:
                del data['Data'][self.key]
            except KeyError:
                pass
        return data

    def rollback_data(self, data):
        """Откатываем данные базы без сохранения"""

        if self.old_value is not None:
            data['Data'][self.key] = self.old_value
        else:
            try:
                del data['Data'][self.key]
            except KeyError:
                pass
        return data


class Transaction(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    uuid: str = Field(default_factory=uuid.uuid4)
    dt: str = Field(default_factory=datetime.datetime.utcnow().timestamp)
    operations: List[TransactionOperation]
    connection: TextIO = None

    def _open_transaction(self):
        """Открываем транзакцию"""

        if self._transactions_is_locked():
            raise TransactionLockedException()
        self._lock_transactions()

        if self.connection:
            return self.connection

        try:
            self.connection = DBManager.open_db()
        except Exception:
            self._unlock_transactions()
            raise

    def _close_transaction(self):
        """Зкарываем транзакцию"""

        self.connection.close()
        self.connection = None
        self._unlock_transactions()

    @classmethod
    def _transactions_is_locked(cls):
        return os.environ.get(TRANSACTIONS_LOCKED_KEY, False) == '1'

    @classmethod
    def _lock_transactions(cls):
        os.environ[TRANSACTIONS_LOCKED_KEY] = '1'

    @classmethod
    def _unlock_transactions(cls):
        try:
            del os.environ[TRANSACTIONS_LOCKED_KEY]
        except KeyError:
            pass

    def commit(self):
        """Пункт: сделать коммит (коммитятся все вложенные операции)."""

        self._open_transaction()

        try:
            data = DBManager.read_db(self.connection)

            for operation in self.operations:
                data = operation.modify_data(data)

            data['Transactions'].append(self)

            self.connection.seek(0)
            DBManager.write_db(self.connection, data)
        except Exception:
            raise
        finally:
            self._close_transaction()

        return self

    def rollback(self):
        """Откатываем транзакцию"""

        self._open_transaction()

        try:
            data = DBManager.read_db(self.connection)

            for operation in self.operations:
                data = operation.rollback_data(data)

            for i, transaction in enumerate(data['Transactions']):
                if transaction.uuid == self.uuid:
                    del data['Transactions'][i]
                    break

            DBManager.write_db(self.connection, data)
        except Exception:
            raise
        finally:
            self._close_transaction()

        return self

    @classmethod
    def rollback_latest(cls):
        """Пункт: сделать роллбэк (откатывается последняя транзакция);"""

        connection = DBManager.open_db()
        try:
            transactions = DBManager.read_db(connection)['Transactions']
            try:
                transaction = transactions[-1]
            except IndexError:
                return None
        except Exception:
            connection.close()
            raise

        transaction.connection = connection

        return transaction.rollback()


class TransactionLockedException(BaseException):
    pass
