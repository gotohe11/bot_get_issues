from dataclasses import dataclass, field, asdict


@dataclass
class Subscription:
    """Класс подписки.
    :param name: имя github репозитория (в формате: owner/repo).
    :param issues_list: список исусов репозитория.
    :param last_issue_num: последний просмотренный пользователем исус.
    """
    name: str
    issues_list: list = field(default_factory=list)
    last_issue_num: int = field(default=0, compare=False)

    @classmethod
    def from_dict(cls, dct: dict):
        """Создает из словаря экземпляр класса Subscription.
        :param dct: данные о подписке в виде словаря.
        :return: экземпляр класса Subscription.
        """
        if dct:
            name = dct['name']
            issues_list = [tuple(item) for item in dct['issues_list']]
            last_issue_num = dct['last_issue_num']
            return cls(name, issues_list, last_issue_num)

    def read_issues(self, num: int):
        """Меняет значение атрибута класса last_issue_num.
        """
        if num <= len(self.issues_list):
            self.last_issue_num = num
        else:
            self.last_issue_num = len(self.issues_list)

    def to_dict(self) -> dict:
        """Преобразует экземпляр класса в словарь.
        :return: экземпляр класса в виде словаря.
        """
        return asdict(self)
