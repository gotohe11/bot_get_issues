"""Осуществляет главную логику программы.
Здесь прописаны все функции для исполнения команд тг-бота.
"""

import functools
import json
import logging
from collections.abc import Callable
from datetime import date
from typing import Any


from . import errors
from . import database
from . import github
from logic.subscriptions import Subscription
from logic.users import User


logger = logging.getLogger(__name__)

DB = database.Database()  # класс ДБ, путь сохранение - по умолчанию
USER = None  # несет экземпляр класса юзер

INFO = []
COMMANDS = {}


def dec_command(cmd_name: str, help_info: str) -> Callable[[str], Any]:
    """Декорирует функции-команды тг-бота.
    Автоматически добавляет команду и соответсвующую ей
    ф-ию в словарь COMMANDS для вызова и информацию
    о командах в INFO.
    :param cmd_name: команда тг-бота.
    :param help_info: информация о команде для пользователя.
    :return: Декорируемую ф-ию.
    """
    def decorator(func):
        INFO.append(('/' + cmd_name, help_info))
        COMMANDS['/' + cmd_name] = func
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            value = func(*args, **kwargs)
            return value
        return wrapper
    return decorator


@dec_command('help',   'commands info;')
def help_command() -> str:
    """Команда тг-бота с информацией о других командах для пользователя.
    """
    res = ['Available commands:'] + [' - '.join(item) for item in INFO]
    return '\n'.join(res)


def _get_issues_list_from_github(project_name: str) -> list[tuple[int | str]]:
    """Загружает с github список исусов репозитория.
    :param project_name: имя репозитория.
    :raises ProjectNotFoundError: 404, репозиторий
        не был найден.
    :raises GithubError: ошибка подключения к github.
    :return: Пронумерованный список исусов репозитория
        с датами создания/обновления и количеством
        комментариев.
    """
    success = False
    while not success:
        try:
            issues_list = github.make_issues_list(project_name)
        except github.ProjectNotFoundError:
            logging.exception(f'Project "{project_name}" not found, check your spelling.')
            res_list = []
            break
        except github.GithubError as err:
            logging.exception(f'Error communicating with Github: {err}')
            break
        success = True
        return issues_list


@dec_command('get', (
        'gets repo issues list and prints the amount of them, '
        'format: get <owner>/<repo> (for example, "get gotohe11/get_issue");'
))
def get_command(project_name: str) -> str:
    """Команда тг-бота /get.
    Загружает список исусов репозитория с github,
    добавляет данный список в последний просмотренный
    (текущий) для дальнейших операций над ним.
    :param project_name: имя репозитория.
    :return: Сообщения о подгруженном репозитории
        или ошибке.
    """
    global USER

    issues_list = _get_issues_list_from_github(project_name)
    if issues_list:
        USER.last_project = Subscription(project_name, issues_list, 0)
        msg = (f'There are {len(issues_list)} issues in the "{project_name}" repository.'
               f' Use /sub, /next or /print commands.')
        return msg
    else:
        return f'Project "{project_name}" not found, check your spelling.'


@dec_command('print', (
        'prints the N-th issue (if there is no N, '
        'prints 10 newest issues), format: print <N>;'
))
def print_command(issue_number: int = None) -> list[tuple[int | str]]:
    """Команда тг-бота /print.
    Печатает указанный номер исуса текущего репозитория
    пользователя (USER.last_project) или первые
    10 исусов.
    :param issue_number: номер исуса для печати.
    :raises IncorrectOder: ошибка пользователя при
        неверной последовательности ввода команд.
    :raises CommandArgsError: ошибка пользователя при
        введении неверных аргументов с тг-командой.
    :return: Список исусов на печать.
    """
    global USER
    if not USER.last_project:
        raise errors.IncorrectOder('Firstly, try "/get <owner>/<repo>" command.')

    issues_list = USER.last_project.issues_list
    if issue_number is None:
        # prints first 10, if no args
        limit = 10
        skip = 0
    else:
        limit = 1
        try:
            skip = int(issue_number) - 1
        except ValueError:
            raise errors.CommandArgsError('Enter a number with "/print" '
                                          'command, not a string.')
        if skip >= len(issues_list) or skip < 0:
            raise errors.CommandArgsError('Number out of issues list range.')

    # замена последнего просмотренного исуса текущего проекта
    USER.last_project.read_issues(skip+limit)
    project_name = USER.last_project.name
    # если юзер подписан на репо, то меняем последний просмотренный исус
    if project_name in USER.subs:
        USER.subs[project_name].read_issues(skip+limit)
        DB.save_sub(USER)  # записываем в файлик

    return issues_list[skip:skip+limit]


@dec_command('next',
             'prints the next 10 issues or the remainder;')
def next_command() -> list[tuple[int | str]]:
    """Команда тг-бота /next.
    Печатает последующие 10 исусов текущего
    репозитория пользователя (USER.last_project).
    :raises IncorrectOder: ошибка пользователя при
        неверной последовательности ввода команд.
    :raises CommandArgsError: ошибка пользователя при введении
        команды, когда все исусы уже просмотрены.
    :return: Список исусов на печать.
    """
    global USER
    if not USER.last_project:
        raise errors.IncorrectOder('Firstly, try "/get <owner>/<repo>" command.')

    issues_list = USER.last_project.issues_list
    num_1 = USER.last_project.last_issue_num
    num_2 = num_1 + 10
    if num_1 < 0 or num_1 >= len(issues_list):
        raise errors.CommandArgsError('You have seen the whole issues list.')
    else:
        # замена последнего просмотренного исуса текущего проекта
        USER.last_project.read_issues(num_2)
        project_name = USER.last_project.name
        # если юзер подписан на репо, то меняем последний просмотренный исус
        if project_name in USER.subs:
                USER.subs[project_name].read_issues(num_2)
                DB.save_sub(USER)  # записываем в файлик
        return issues_list[num_1:num_2]


# имя получилось нечувств к регистру
def login_command(user_id: str, user_name: str = None) -> User:
    """Регистрация/авторизация пользователя.
    Регистрирует нового пользователя в БД
    или загружает информацию о существующем.
    :param user_id: id пользователя тг.
    :param user_name: first_name пользователя тг.
    :return: Экземпляр класса User.
    """
    global USER
    USER = DB.load_or_create_user(user_id, user_name)
    logger.info(f'Login {USER.name}.')
    return USER


@dec_command('sub',
             'to subscribe to the project, format: sub <owner>/<repo>;')
def sub_command(project_name: str = None) -> str:
    """Команда тг-бота /sub.
    Подписывает пользователя на репозиторий.
    :raises CommandArgsError: ошибка пользователя при введении
        команды.
    :raises GithubError: ошибка загрузки исусов с github.
    :return: Сообщение об удачно выполненной подписке на
        репозиторий или об ошибке в процессе.
    """
    global USER
    if not project_name:
        raise errors.CommandArgsError('You forgot to text a project name.')

    if USER.last_project and project_name == USER.last_project.name:
        project_obj = USER.last_project
    else:
        try:  # создаем подписку
            issues_list = _get_issues_list_from_github(project_name)  # заново грузим исусы
            if not issues_list:
                raise github.GithubError
            project_obj = Subscription(project_name, issues_list, 0)
        except github.GithubError:
            raise github.GithubError('Some problem with GitHub.')

    try:
        USER.add_subsc(project_obj)
        DB.save_sub(USER)  # просто переписываем весь список подписок юзера заново
        msg = f'{USER.name}, you subscribed to "{project_name}" repository.'
        logger.info(msg)
        return msg
    except NameError as er:
        logger.exception(er.args[0])
        return er.args[0]


@dec_command('unsub',
             'to unsubscribe from the project, format: unsub <owner>/<repo>;')
def unsub_command(project_name: str = None) -> str:
    """Команда тг-бота /unsub.
    Отписывает пользователя от репозитория.
    :param project_name: имя репозитория.
    :raises CommandArgsError: ошибка пользователя при введении
        команды.
    :return: Сообщение об удачно выполненной операции
        или об ошибке в процессе.
    """
    global USER
    if not project_name:
        raise errors.CommandArgsError('You forgot to text a project name.')

    try:
        USER.remove_subsc(project_name)  # удаляем ненужную подписку из списка подписок юзера
        DB.save_sub(USER)  # просто переписываем весь список подписок юзера заново
        msg = f'{USER.name}, you unsubscribed from the "{project_name}" repository.'
        logger.info(msg)
        return msg
    except NameError as er:
        logger.exception(er.args[0])
        return er.args[0]


def _update_one_sub(subscription: Subscription, since_date: str = None) -> list[Any]:
    """Обновляет подписку.
    Обновляет данные переданного экземпляра
    класса Subscription с указанной даты
    или с последнего просмотренного исуса.
    :param subscription: экз.класса Subscription.
    :param since_date: дата, с которой пользователь
        хочет обновить исусы подписки.
    :raises GithubError: ошибка загрузки исусов с github.
    :return: Список новых исусов подписки с
        заголовком или пустой список.
    """
    result_list = []
    temp_list_issues = _get_issues_list_from_github(subscription.name)  # заново грузим весь репозиторий
    if not temp_list_issues:
        raise github.GithubError

    start_num = new_last_num = None
    if since_date:
        # собираем номера непросмотренных исусов подписки для печати
        numbers_new_issues_list = []
        for issue in temp_list_issues:
            # issue[2] = issue's created_at data
            if date.fromisoformat(issue[2]) > date.fromisoformat(since_date):
                numbers_new_issues_list.append(issue[0])  # issue[0] = issue's N
            else:
                break
        if numbers_new_issues_list:
            start_num = numbers_new_issues_list[0] - 1
            new_last_num = numbers_new_issues_list[-1]

    else:  # if not since_date
        # сравниваем с последним просмотренным исусом
        if subscription.last_issue_num < len(temp_list_issues):
            start_num = subscription.last_issue_num
            new_last_num = len(temp_list_issues)

    if new_last_num:
        result_list.append(subscription.name + ' repository:')
        result_list.extend(temp_list_issues[start_num:new_last_num])
        subscription.issues_list = temp_list_issues
        subscription.last_issue_num = new_last_num

    return result_list


@dec_command('update', (
        'prints issues in all projects you subscribe '
        'since the last visit or date, format: update <date>;'
))
def update_command(since_date: str = None) -> list[Any] | str:
    """Команда тг-бота /update.
    Обновляет данные подписок у пользователя
    с указанной даты или с последнего
    просмотренного исуса.
    :param since_date: дата, с которой пользователь
        хочет обновить исусы подписок.
    :raises ValueError: ошибка пользователя при вводе
        даты обновления.
    :return: Список новых исусов подписок с
        заголовками или пустой список,
        или строка с сообщением.
    """
    global USER
    if not USER.subs:
        msg = 'You do not have any subscriptions yet.'
        logger.info(msg)
        return msg

    if since_date:
        try:
            date.fromisoformat(since_date)
        except ValueError as er:
            msg = 'Invalid isoformat string for date. Try again.'
            logger.exception(msg)
            return msg

    result = []
    for sub_name, subscription in USER.subs.items():
        temp = _update_one_sub(subscription, since_date)
        if temp:
            result.append(temp)
        else:
            msg = f'There is nothing to update in "{subscription.name}" repository.'
            logger.info(msg)
            result.append(msg)

    DB.save_sub(USER)
    return result


def check_updates(user: User) -> list[Any]:
    """Проверяет и обновляет подписки пользователя.
    :param user: экземпляр класса User.
    :return: Список новых исусов подписок с
        заголовками или пустой список.
    """
    if user.subs:
        new_issues_list = []
        for subs_name, subscription in user.subs.items():
            # берем дату самого нового исуса у подписки
            last_issue_date = subscription.issues_list[0][2]
            logger.info(f'Checking {subscription.name} updates')
            result = _update_one_sub(subscription, last_issue_date)
            new_issues_list.extend(result)
            DB.save_sub(user)

        return new_issues_list



@dec_command('status', 'prints info about current user;')
def status_command() -> list[tuple[int | str]]:
    """Выводит информацию о подписках пользователя.
    :return: Список с информацией о состоянии
        подписок пользователя.
    """
    global USER
    subs_list = []
    if USER.subs:
        msg = f'{USER.name}, you have {len(USER.subs)} subscription(s):'
        subs_list.append(msg)
        for i, sub in enumerate(USER.subs.values(), 1):
            temp = (i, sub.name, f'{len(sub.issues_list)} issues',
                    f'last time read issue - {sub.last_issue_num}')
            subs_list.append(temp)
    else:
        msg = f'{USER.name}, you have no subscriptions yet.'
        logger.info(msg)
        return msg

    return subs_list


@dec_command('users',
             'prints a list of all registered users.')
def users_command() -> list[str] | str:
    """Выводит инф-ию о зарегистрированных пользователях.
    :raises: FileNotFoundError: ошибка чтения файла.
    :return: Список пользователей или сообщение об
        их отсутствии.
    """
    try:
        with open(DB.path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError as er:
        msg = 'No users yet.'
        logger.exception(msg)
        return msg

    return list(data.keys())


def run_one(command: str) -> Callable[[str], Any]:
    """Обработчик введенных команд.
    :param command: введенная пользователем
        команда.
    :raises CommandNotFound: отсутствует ключ-команда
        в COMMANDS.
    :raises CommandArgsError: передача пользователем
        неверных аргументов с командой.
    :return: Значение по ключу-команде в
        словаре COMMANDS.
    """
    parts = command.lower().split()
    cmd = parts[0]
    if len(parts) > 1:
        args = parts[1:]
    else:
        args = []

    if cmd not in COMMANDS:
        raise errors.CommandNotFound('Command not found.')

    try:
        return COMMANDS[cmd](*args)
    except TypeError as er:
        logger.exception(er)
        raise errors.CommandArgsError('Wrong number of arguments provided.')
