import argparse
import sys
from datetime import date, timedelta

import click
import profig
import questionary
from redminelib import Redmine

cfg = profig.Config('app.cfg')
cfg.init('redmine.host', 'localhost')
cfg.init('redmine.username', '')
cfg.init('redmine.password', '')
cfg.init('redmine.token', '')
cfg.init('project.id', '')
cfg.init('release.tracker_id', '')
cfg.init('release.done_status_id', '')
cfg.init('release.filter_custom_fields', [], list)


def get_rd():
    return Redmine(cfg['redmine.host'],
                   username=cfg['redmine.username'], password=cfg['redmine.password'], key=cfg['redmine.token'])


def get_last_versions():
    rd = get_rd()
    versions = rd.version.filter(project_id=cfg['project.id'])
    date_from = date.today() - timedelta(days=30)

    return reversed([v for v in versions if hasattr(v, 'due_date') and v.due_date >= date_from])


def get_custom_fields(filtered=False) -> dict:
    rd = get_rd()
    if filtered:
        filter_id = list(map(int, cfg['release.filter_custom_fields']))
        return {cf.id: cf for cf in rd.custom_field.all() if cf.field_format in ('user', 'list') and cf.id in filter_id}
    else:
        return {cf.id: cf for cf in rd.custom_field.all()}


def get_cf_values(cf_id):
    cf = get_rd().custom_field.get(cf_id)
    if hasattr(cf, 'possible_values'):
        return cf.possible_values
    else:
        return []


def get_memberships(project_id):
    return get_rd().project_membership.filter(project_id=project_id)


@click.group('RedmineCli')
def cli():
    pass


@cli.command()
def config():
    config_data = {}
    config_data['redmine.host'] = click.prompt('Укажите URL')
    config_data['redmine.token'] = click.prompt('Укажите Token')
    if not config_data['redmine.token']:
        config_data['redmine.username'] = click.prompt('Укажите Логин')
        config_data['redmine.password'] = click.prompt('Укажите Пароль')

    config_data['project.id'] = click.prompt('Укажите ProjectID')
    config_data['release.tracker_id'] = click.prompt('Укажите ID трекера с релизами')
    config_data['release.done_status_id'] = click.prompt('Укажите ID конечного статуса')

    for name, value in config_data.items():
        click.echo(f'{name}: {value}')
    if click.confirm('Всё верно?'):
        cfg.update(config_data.items())
        cfg.sync()


@cli.command()
def version():
    version = get_last_versions()

    for v in version:
        click.echo(v)


@cli.group()
def release():
    """Управление релизами"""
    pass


def gen_number_release() -> list:
    from datetime import date
    year, week, wday = date.today().isocalendar()
    numbers = []
    for i in range(30):
        for num in range(1, 15):
            numb = f'{year}.{week + i}.{num}'
            numbers.append(numb)
    return numbers


@release.command()
def create():
    """Создать релиз"""
    # number = click.prompt('Введите номер релиза')
    user = get_rd().user.get('current')
    versions = get_last_versions()
    versions_map = {str(v): v for v in versions}

    release_version = questionary.select('Версия', choices=list(versions_map.keys())).ask()
    number = questionary.autocomplete('Номер релиза', choices=gen_number_release()).ask()
    description = questionary.text('Описание задачи').ask()

    memberships = {str(m.user): m.user.id for m in get_memberships(cfg['project.id'])}

    custom_fields = []
    for cf_id, cf in get_custom_fields(filtered=True).items():
        default_select = None

        possible_values = [v.get('value') for v in get_cf_values(cf_id)]
        if cf.field_format == 'user':
            default_select = str(user)
            possible_values = memberships.keys()
        if not len(possible_values):
            continue
        if len(possible_values) > 10:
            value = questionary.autocomplete(str(cf), choices=possible_values, default=default_select).ask()
        else:
            value = questionary.select(str(cf), choices=possible_values, default=default_select).ask()

        if cf.field_format == 'user':
            value = memberships.get(value)
            if not value:
                continue

        custom_fields.append({'id': cf_id, 'value': value})

    is_confirm = questionary.confirm('Создать задачу?').ask()
    if is_confirm:
        release_version = versions_map[release_version]
        release_subject = f'Релиз {number}'
        result = get_rd().issue.create(
            project_id=cfg['project.id'],
            tracker_id=cfg['release.tracker_id'],
            subject=release_subject,
            fixed_version_id=release_version.id,
            assigned_to_id=user.id,
            description=description,
            custom_fields=custom_fields
        )
        click.echo(click.style(f'Создана задача № {result.id}', bold=True, blink=True))


@release.command('list')
@click.option('--all', 'all_list', is_flag=True, default=False)
@click.option('-l', '--limit', 'limit', type=int, show_default=30)
@click.option('--me', 'me', is_flag=True, default=False)
def ls(all_list, limit, me):
    """Список релизов"""
    rd = get_rd()
    click.echo('Не опубликованные релизы')
    for iss in rd.issue.filter(project_id=cfg['project.id'], tracker_id=cfg['release.tracker_id'],
                               sort='created_on:desc', limit=limit, assigned_to_id='me' if me else '*'):
        if iss.status.id != int(cfg['release.done_status_id']) or all_list:
            echo_text = f'#{iss.id} {str(iss)} {iss.status.name}'
            click.echo(echo_text)


@cli.command('custom_field')
def c_fields():
    for cf_id, cf in get_custom_fields().items():
        click.echo(f'ID: {cf_id} = {str(cf)}')
        if cf_id == 2:
            print(dir(cf))

@cli.command('members')
def memerships():
    for m in get_memberships(cfg['project.id']):
        print(m.user)

if __name__ == '__main__':
    cfg.sync()
    cli()
