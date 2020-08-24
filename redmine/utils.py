import datetime
from datetime import date, timedelta
from typing import Union


def get_last_versions(rd, project_id):
    versions = rd.version.filter(project_id=project_id)
    date_from = date.today() - timedelta(days=30)

    return reversed([v for v in versions if hasattr(v, 'due_date') and v.due_date >= date_from])


def get_custom_fields(rd, filtered=None) -> dict:
    if filtered and isinstance(filtered, list):
        filter_id = list(map(int, filtered))
        return {cf.id: cf for cf in rd.custom_field.all() if cf.field_format in ('user', 'list') and cf.id in filter_id}
    else:
        return {cf.id: cf for cf in rd.custom_field.all()}


def get_cf_values(rd, cf_id):
    cf = rd.custom_field.get(cf_id)
    if hasattr(cf, 'possible_values'):
        return cf.possible_values
    else:
        return []


def get_memberships(rd, project_id):
    return rd.project_membership.filter(project_id=project_id)


def gen_number_release() -> list:
    from datetime import date
    year, week, wday = date.today().isocalendar()
    numbers = []
    for i in range(30):
        for num in range(1, 15):
            numb = f'{year}.{week + i}.{num}'
            numbers.append(numb)
    return numbers


def get_current_project_version(rd, project_id):
    today = date.today()
    versions = [v for v in rd.version.filter(project_id=project_id) if hasattr(v, 'due_date') and v.due_date >= today]
    return versions[0] if len(versions) else None


def get_trackers_project(rd, project_id):
    project = rd.project.get(project_id, include=['trackers'])
    return project.trackers


def get_row_data(item, fields_data: Union[list, tuple]) -> list:
    row = []
    for attr in fields_data:
        value = '-'
        if hasattr(item, attr):
            value = getattr(item, attr)
        row.append(str(value))
    return row


def get_status_project(rd):
    return rd.issue_status.all()


def get_projects(rd):
    return rd.project.all()


def iso_year_start(iso_year):
    "The gregorian calendar date of the first day of the given ISO year"
    fourth_jan = datetime.date(iso_year, 1, 4)
    delta = datetime.timedelta(fourth_jan.isoweekday()-1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day):
    "Gregorian calendar date for the given ISO year, week and day"
    year_start = iso_year_start(iso_year)
    return year_start + datetime.timedelta(days=iso_day-1, weeks=iso_week-1)


def generate_versions(init_version, count=10):
    from datetime import date
    today = date.today()
    current_year = today.strftime('%y')

    for _ in range(count):
        init_version += 1
        name = f'y{current_year}w{init_version}'
        due_date = iso_to_gregorian(today.year, init_version, 7)
        yield name, due_date


def is_last_version_app():
    from requests import get as get_url
    from . import __version__ as current_version

    response = get_url('https://pypi.org/pypi/Redmine-CLI-Tool/json')
    if response.status_code != 200:
        return True
    data = response.json()
    pypi_version = tuple(map(int, str(data['info']['version']).split('.')))
    return current_version >= pypi_version