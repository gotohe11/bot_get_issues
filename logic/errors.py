class CommandError(Exception):
    """ Базовый класс для ошибок форматирования команд """


class CommandNotFound(CommandError):
    """ Команда с заданным именем не определена """

    def __repr__(self):
        return 'Command not found'


class CommandArgsError(CommandError):
    """ Что-то не так с аргументами (например, неправильное количество) """

    def __repr__(self):
        return 'Wrong number of arguments provided'


class IncorrectOder(CommandError):
    """ Была введена команда печати до получения списка тикетов """

    def __repr__(self):
        return 'Firstly, try the command "/get <owner>/<repo>".'
