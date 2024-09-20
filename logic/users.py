from dataclasses import dataclass, field
from . import subscriptions


@dataclass
class User:
    user_id: str
    name: str = field(default=None)
    subs: dict = field(default_factory=dict)
    last_project: subscriptions.Subscription = field(default=None)    # последний просмотренный проект без подписки


    def add_subsc(self, project_obj):
        if project_obj.name in self.subs:
            raise NameError(f'You have already subscribed to the "{project_obj.name}" repository.')
        dct = {project_obj.name: project_obj}
        self.subs.update(dct)


    def remove_subsc(self, project_name):
        if project_name not in self.subs:
            raise NameError(f'You are not subscribed to the "{project_name}" repository.')
        del self.subs[project_name]


    @classmethod
    def from_dict(cls, dct):
        user_id = dct['user_id']
        name = dct['name']
        subs = {
            k: subscriptions.Subscription.from_dict(v)
            for k, v in dct['subs'].items()
        }
        return cls(user_id, name, subs)    # без посл просм проекта

