import json
import logging

import redis

from .users import User


logger = logging.getLogger(__name__)
redis_client = redis.Redis(host='redis', port=6379, db=0)


class Database:
    """Класс БД.
    Записывает и считывает данные о пользователях.
    Если пользователь новый - создает новый экземпляр
    класса User.
    """
    @staticmethod
    def load_or_create_user(user_id: str, user_name: str = None) -> User:
        """Выгружает существующего пользователя
        из БД или создает нового.
        :param user_id: id пользователя тг.
        :param user_name: first name пользователя тг.
        :raises FileNotFoundError: еще нет БД.
        :return: экземпляр класса User.
        """
        data_from_redis = redis_client.get(user_id)
        if data_from_redis:
            # десериализация данных в словарь
            data_loaded = json.loads(data_from_redis.decode('utf-8'))
            logger.debug('Old user is getting')
            user = User.from_dict(data_loaded)
        else:
            logger.debug('New user is creating')
            user = User(user_id, user_name)  # создаем нового юзера
            user_data = json.dumps(user.to_dict(), indent=2)
            redis_client.set(user.user_id, user_data)  # записываем его в редис
        return user

    @staticmethod
    def save_sub(user: User):
        """Сохраняет данные о подписках пользователя в БД.
        """
        logger.debug("Save user's info")
        user_data = json.dumps(user.to_dict(), indent=2)
        redis_client.set(user.user_id, user_data)

    @classmethod
    def get_all_users(cls) -> list[User]:
        """Выдает информацию о зарегистрированных пользователях.
        :return: Список экземпляров класса User всех пользователей.
        """
        logger.debug('DB is getting all users')
        all_users_id = redis_client.scan_iter(match='*', count=100)
        res = [cls.load_or_create_user(user_id.decode('utf-8')) for user_id in all_users_id]
        return res
