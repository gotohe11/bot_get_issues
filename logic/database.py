import json
import os.path

from logic.users import User


class Database:
    """Класс БД.
    Записывает и считывает данные о пользователях.
    Если пользователь новый - создает новый экземпляр
    класса User.
    :param path: путь к файлу с БД.
    """
    def __init__(self, path=os.path.expanduser('~/users_data.json')):
        self.path = path

    def load_or_create_user(self, user_id: str, user_name: str) -> User:
        """Выгружает существующего пользователя
        из БД или создает нового.
        :param user_id: id пользователя тг.
        :param user_name: first name пользователя тг.
        :raises FileNotFoundError: еще нет БД.
        :return: экземпляр класса User.
        """
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except FileNotFoundError:
            with open(self.path, 'w', encoding='utf-8') as file:
                data = {}
                json.dump(data, file, indent=2)
        if data and user_id in data:
            user = User.from_dict(data[user_id])
        else:
            user = User(user_id, user_name)
            Database.save_user(self, user)
        return user

    def save_user(self, user: User):
        """Сохраняет данные пользователя в БД.
        """
        with open(self.path, 'r+', encoding='utf-8') as file:
            data = json.load(file)
            data[user.user_id] = user.__dict__
            file.seek(0)
            json.dump(data, file, indent=2)
            file.truncate()

    def save_sub(self, user: User):
        """Сохраняет данные о подписках пользователя в БД.
        """
        with open(self.path, 'r+', encoding='utf-8') as file:
            data = json.load(file)
            data[user.user_id]['subs'] = {k: v.__dict__ for k, v in user.subs.items()}
            file.seek(0)
            json.dump(data, file, indent=2)
            file.truncate()
