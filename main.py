import argparse
import sys
from datetime import date, timedelta

import click
import profig
from redminelib import Redmine


cfg = profig.Config('app.cfg')
cfg.init('redmine.host', 'localhost')
cfg.init('redmine.username', '')
cfg.init('redmine.password', '')
cfg.init('redmine.token', '')
cfg.init('project.id', '')
cfg.init('release.tracker_id', '')
cfg.init('release.done_status_id', '')


def get_rd():
    return Redmine(cfg['redmine.host'],
                   username=cfg['redmine.username'], password=cfg['redmine.password'], key=cfg['redmine.token'])


def get_last_versions():
    rd = get_rd()
    versions = rd.version.filter(project_id=cfg['project.id'])
    date_from = date.today() - timedelta(days=30)

    return reversed([v for v in versions if hasattr(v, 'due_date') and v.due_date >= date_from])


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
        print(v)


@cli.group()
def release():
    """Управление релизами"""
    pass


@release.command()
def create():
    """Создать релиз"""
    number = click.prompt('Введите номер релиза')
    user = get_rd().user.get('current')
    versions = get_last_versions()
    versions_map = {str(v): v for v in versions}
    release_version = click.prompt('Введите версию', type=click.Choice(choices=versions_map.keys()))
    release_service = click.prompt('Введите сервис', type=click.Choice(choices=['Billing', 'Vam']))

    release_version = versions_map[release_version]
    release_subject = f'Релиз {number}'
    click.echo('Задача:')
    click.echo(f'Наименование: {release_subject}')
    click.echo(f'Версия: {release_version}')
    if click.confirm('Создать задачу'):
        get_rd().issue.create(
            project_id=cfg['project.id'],
            tracker_id=cfg['release.tracker_id'],
            subject=release_subject,
            fixed_version_id=release_version.id,
            assigned_to_id=user.id
        )


@release.command()
@click.option('--all', 'all_list', is_flag=True, default=False)
@click.option('-l', '--limit', 'limit', type=int, show_default=30)
@click.option('--me', 'me', is_flag=True, default=False)
def list(all_list, limit, me):
    """Список релизов"""
    rd = get_rd()
    click.echo('Не опубликованные релизы')
    for iss in rd.issue.filter(project_id=cfg['project.id'], tracker_id=cfg['release.tracker_id'],
                               sort='created_on:desc', limit=limit, assigned_to_id='me' if me else '*'):
        if iss.status.id != int(cfg['release.done_status_id']) or all_list:
            echo_text = f'#{iss.id} {str(iss)} {iss.status.name}'
            click.echo(echo_text)


if __name__ == '__main__':
    cfg.sync()
    cli()
