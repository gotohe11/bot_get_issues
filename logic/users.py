from dataclasses import dataclass, field

from .subscriptions import Subscription


@dataclass
class User:
    """Класс пользователя.
    :param user_id: id тг-пользователя.
    :param name: first name тг-пользователя.
    :param subs: репозитории, на которые пользователь подписался.
    :param last_project: текущий репозиторий, который просматривает
        пользователь (полученный командой /get).
    """
    user_id: str
    name: str = field(default=None)
    subs: dict = field(default_factory=dict)
    last_project: Subscription = field(default=None)

    def add_subsc(self, sub_obj: Subscription):
        """Подписывает пользователя на репозиторий.
        :param sub_obj: экземпляр класса Subscription.
        :raises NameError: попытка подписаться на репозиторий,
            который уже есть в подписках.
        """
        if sub_obj.name in self.subs:
            raise NameError(f'You have already subscribed to '
                            f'the "{sub_obj.name}" repository.')
        dct = {sub_obj.name: sub_obj}
        self.subs.update(dct)

    def remove_subsc(self, project_name: str):
        """Отписывает пользователя от репозитория.
        :param project_name: имя репозитория.
        :raises NameError: попытка отписаться от репозитория,
            которого нет в подписках.
        """
        if project_name not in self.subs:
            raise NameError(f'You are not subscribed to '
                            f'the "{project_name}" repository.')
        del self.subs[project_name]

    @classmethod
    def from_dict(cls, dct: dict):
        """Создает из словаря экземпляр класса User.
        :param dct: данные о пользователе в виде словаря.
        :return: экземпляр класса User.
        """
        user_id = dct['user_id']
        name = dct['name']
        subs = {
            k: Subscription.from_dict(v)
            for k, v in dct['subs'].items()
        }
        return cls(user_id, name, subs)  # без посл просм проекта
