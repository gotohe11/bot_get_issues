import json
import os.path

from . import users
from . import subscriptions


class Database:
    def __init__(self, path=os.path.expanduser('~/users_data.json')):
        self.path = path


    def load_or_create_user(self, user_id, user_name):
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except FileNotFoundError:
            with open(self.path, 'w', encoding='utf-8') as file:
                data = {}
                json.dump(data, file, indent=2)
        if data and user_id in data:
            user = users.User.from_dict(data[user_id])
        else:
            user = users.User(user_id, user_name)
            Database.save_user(self, user)
        return user



    def save_user(self, user):
        with open(self.path, 'r+', encoding='utf-8') as file:
            data = json.load(file)
            data[user.user_id] = user.__dict__
            file.seek(0)
            json.dump(data, file, indent=2)
            file.truncate()



    def save_sub(self, user):     # перезаписываем все подписки юзера
        with open(self.path, 'r+', encoding='utf-8') as file:
            data = json.load(file)
            data[user.user_id]['subs'] = {k: v.__dict__ for k, v in user.subs.items()}
            file.seek(0)
            json.dump(data, file, indent=2)
            file.truncate()
