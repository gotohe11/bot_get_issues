import sys
from tabulate import tabulate
from datetime import date
import functools
import json

from . import errors, github, users, subscriptions, database

DB = database.Database()   # класс ДБ, путь сохранение - по умолчанию
USER = None    # несет экземпляр класса юзер

INFO = []
COMMANDS = {}


def pretty_print_issues(res_list, num_start, num_finish=100):
    """
    Prints a list of issues sorted by creation date (by default),
    in the form of a table.
    :param num_start: required number of issues
    :param num_finish: required number of issues
    :return: data table
    """
    columns = ['N', 'title', 'created_at', 'updated_at', 'comments']
    print(tabulate(res_list[num_start:num_finish], headers=columns))


def dec_command(cmd_name, help_info):
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
def help_command():
    res = ['Available commands:'] + [' - '.join(item) for item in INFO]
    print(*res, sep='\n')
    return '\n'.join(res)


@dec_command('exit',  'exit;')
def exit_command():
    sys.exit()


def _get_issues_list_from_github(project_name):
    success = False
    while not success:
        try:
            issues_list = github.make_issues_list(project_name)
        except github.ProjectNotFoundError:
            print(f'Project "{project_name}" not found, check your spelling.')
            res_list = []
            break
        except github.GithubError as err:
            print(f'Error communicating with Github: {err}')
            break
        success = True
        return issues_list


@dec_command('get', 'gets repo issues list and prints the amount of them, '
             'format: get <owner>/<repo> (for example, "get gotohe11/get_issue");')
def get_command(project_name):
    global USER

    issues_list = _get_issues_list_from_github(project_name)
    if issues_list:
        USER.last_project = subscriptions.Subscription(project_name, issues_list, 0)
        msg = (f'There are {len(issues_list)} issues in the "{project_name}" repository.'
               f' Use /sub, /next or /print commands.')
        print(msg)
        return msg
    else:
        return f'Project "{project_name}" not found, check your spelling.'



@dec_command('print',
             'prints the N-th issue (if there is no N, prints 10 newest issues), '
             'format: print <N>;')
def print_command(issue_number=None):
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

    pretty_print_issues(issues_list, skip, skip+limit)   # печатаем
    USER.last_project.read_issues(skip+limit)  # замена последнего просмотренного исуса текущего проекта

    # замена последнего просмотренного исуса проекта если он в подписках у пользователя
    project_name = USER.last_project.name
    if project_name in USER.subs:    # если юзер подписан на репо, то меняем последний просмотренный исус
        USER.subs[project_name].read_issues(skip+limit)
        DB.save_sub(USER)     # записываем в файлик

    return issues_list[skip:skip+limit]


@dec_command('next',
             'prints the next 10 issues or the remainder;')
def next_command():
    global USER
    if not USER.last_project:
        raise errors.IncorrectOder('Firstly, try "/get <owner>/<repo>" command.')

    issues_list = USER.last_project.issues_list
    num_1 = USER.last_project.last_issue_num
    num_2 = num_1 + 10
    if num_1 < 0 or num_1 >= len(issues_list):
        raise errors.CommandArgsError('You have seen the whole issues list.')
    else:
        pretty_print_issues(issues_list, num_1, num_2)
        USER.last_project.read_issues(num_2)    # замена последнего просмотренного исуса текущего проекта

        # замена последнего просмотренного исуса проекта если он в подписках у пользователя
        project_name = USER.last_project.name
        if project_name in USER.subs:  # если юзер подписан на репо, то меняем последний просмотренный исус
                USER.subs[project_name].read_issues(num_2)
                DB.save_sub(USER)  # записываем в файлик

        return issues_list[num_1:num_2]



def login_command(user_id, user_name=None):   # имя получилось нечувств к регистру
    global USER
    USER = DB.load_or_create_user(user_id, user_name)
    msg = f'Hello, {USER.name}!'
    print(msg)
    return USER


@dec_command('sub',
              'to subscribe to the project, '
              'format: sub <owner>/<repo>;')
def sub_command(project_name=None):
    global USER

    if not project_name:
        raise errors.CommandArgsError('You forgot to text a project name.')

    if USER.last_project and project_name == USER.last_project.name:
        project_obj = USER.last_project
    else:
        try:    # создаем подписку
            issues_list = _get_issues_list_from_github(project_name)    # заново грузим исусы
            if not issues_list:
                raise github.GithubError
            project_obj = subscriptions.Subscription(project_name, issues_list, 0)
        except github.GithubError:
            raise github.GithubError('Some problem with GitHub.')
    try:
        USER.add_subsc(project_obj)
        DB.save_sub(USER)  # просто переписываем весь список подписок юзера заново
        msg = f'{USER.name}, you subscribed to "{project_name}" repository.'
        print(msg)
        return msg
    except NameError as er:
        return er.args[0]



@dec_command('unsub',
             'to unsubscribe from the project, '
             'format: unsub <owner>/<repo>;')
def unsub_command(project_name=None):
    global USER

    if not project_name:
        raise errors.CommandArgsError('You forgot to text a project name.')

    try:
        USER.remove_subsc(project_name)    # удаляем ненужную подписку из списка подписок юзера
        DB.save_sub(USER)   # просто переписываем весь список подписок Юзера заново
        msg = f'{USER.name}, you unsubscribed from the "{project_name}" repository.'
        print(msg)
        return msg
    except NameError as er:
        return er.args[0]



def _update_one_sub(subscription, since_date=None):
    result_list = []
    temp_list_issues = _get_issues_list_from_github(subscription.name)  # заново грузим весь репозиторий
    if not temp_list_issues:
        raise github.GithubError

    if not since_date:  # догружаем у каждой подписки все исусы, которые еще не видел юзер
        if subscription.last_issue_num < len(temp_list_issues):  # сравниваем с последним просмотренным исусом
            print(subscription.name + ' repository:')
            result_list.append(subscription.name + ' repository:')
            pretty_print_issues(temp_list_issues, subscription.last_issue_num, len(temp_list_issues))
            result_list.extend(temp_list_issues[subscription.last_issue_num:len(temp_list_issues)])
            subscription.issues_list = temp_list_issues
            subscription.last_issue_num = len(temp_list_issues)

    else:    # if since_date
        numbers_new_issues_list = []  # собираем все номера непросмотренных исусов подписки для печати
        for issue in temp_list_issues:
            # issue[2] = issue's created_at data
            if date.fromisoformat(issue[2]) > date.fromisoformat(since_date):
                numbers_new_issues_list.append(issue[0])  # issue[0] = issue's N
            else:
                break
        if numbers_new_issues_list:
            print(subscription.name + ' repository:')
            result_list.append(subscription.name + ' repository:')
            pretty_print_issues(temp_list_issues, numbers_new_issues_list[0] - 1, numbers_new_issues_list[-1])
            result_list.extend(temp_list_issues[numbers_new_issues_list[0] - 1:numbers_new_issues_list[-1]])
            subscription.issues_list = temp_list_issues
            subscription.last_issue_num = numbers_new_issues_list[-1]

    return result_list



@dec_command('update',
             'prints issues in all projects you subscribe since the last visit'
             'or date, format: update <date>;')
def update_command(since_date=None):
    """
    Prints new issues since {since_date} or since last time visit (last_issue_num)
    """
    global USER
    if not USER.subs:
        msg = 'You do not have any subscriptions yet.'
        print(msg)
        return msg

    if since_date:
        try:
            date.fromisoformat(since_date)
        except ValueError as er:
            msg = 'Invalid isoformat string for date. Try again.'
            print(msg)
            return msg

    result = []
    for sub_name, subscription in USER.subs.items():
        temp = _update_one_sub(subscription, since_date)
        if temp:
            result.append(temp)
        else:
            msg = f'There is nothing to update in "{subscription.name}" repository.'
            print(msg)
            result.append(msg)

    DB.save_sub(USER)
    return result



def check_updates(user):
        if user.subs:
            new_issues_list = []
            for subs_name, subscription in user.subs.items():
                last_issue_date = subscription.issues_list[0][2]    # берем дату самого нового исуса у подписки
                print(f'check {subscription.name} updates')
                result = _update_one_sub(subscription, last_issue_date)
                new_issues_list.extend(result)
                DB.save_sub(user)

            return new_issues_list



@dec_command('status', 'prints info about current user;')
def status_command():
    global USER

    subs_list = []
    if USER.subs:
        msg = f'{USER.name}, you have {len(USER.subs)} subscription(s):'
        print(msg)
        subs_list.append(msg)
        for i, sub in enumerate(USER.subs.values(), 1):
            temp = (i, sub.name, f'{len(sub.issues_list)} issues', f'last time read issue - {sub.last_issue_num}')
            subs_list.append(temp)
            print(', '.join(str(i) for i in temp))
    else:
        msg = f'{USER.name}, you have no subscriptions yet.'
        print(msg)
        return msg
    return subs_list


@dec_command('users',
             'prints a list of all registered users.')
def users_command():
    try:
        with open(DB.path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError as er:
        msg = 'No users yet.'
        print(msg)
        return msg
    print('Registered users:')
    print(*data.keys(), sep=', ')
    return list(data.keys())


def ask_user():
    return input('Enter the command '
                 '(for more information about commands input "/help"): ')


def _run_one(command: str):
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
        print(er)
        raise errors.CommandArgsError('Wrong number of arguments provided.')


def run():
    """ Запускает пользовательский (консольный) интерфейс приложения.
    Чтобы "запуск" не был совсем тривиальным, реализуем перезапрос в случае
    ошибок.
    """
    while True:
        user_command = ask_user()
        if not user_command:
            continue
        try:
            _run_one(user_command)
        except errors.CommandError as exc:
            print(exc)


if __name__ == "__main__":
    run()
