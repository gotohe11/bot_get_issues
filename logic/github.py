import requests


class GithubError(Exception):
    """Base class for API-related exceptions."""
    pass


class ProjectNotFoundError(GithubError):
    """Raised when the requested resource is not found."""
    pass


def make_issues_list(project_name: str) -> list[tuple[int | str]]:
    """Ходит на github за исусами.
    :param project_name: имя репозитория.
    :raises ProjectNotFoundError: проект не найден.
    :raises GithubError: другие ошибки подключения
        к github.
    :return: Пронумерованный список исусов репозитория.
    """
    base_url = f'https://api.github.com/repos/{project_name}/issues'
    total_list = []
    page_counter = 1
    issues_counter = 1
    while True:
        temp_list = []
        add_url = f'{base_url}?page={page_counter}'
        try:
            response = requests.get(add_url)
            status_code = response.status_code
            if status_code == 404:
                raise ProjectNotFoundError
            if status_code != 404 and status_code != 200:
                raise GithubError
        except ProjectNotFoundError:
            raise ProjectNotFoundError
        except Exception:
            raise GithubError('Something went wrong. Try again.')

        for item in response.json():
            if 'pull_request' not in item.keys():
                # in item['created_at'] and item['updated_at'] - [0:10] takes only date info
                temp_list.append((issues_counter, item['title'], item['created_at'][0:10],
                                  item['updated_at'][0:10], item['comments']))
                issues_counter += 1

        if temp_list:
            total_list.extend(temp_list)
            page_counter += 1
        else:
            break

    return total_list
