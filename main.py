import click
import profig
import questionary
from redminelib import Redmine

from utils import get_last_versions, gen_number_release, get_memberships, get_custom_fields, get_cf_values

cfg = profig.Config('app.cfg')
cfg.init('redmine.host', 'localhost')
cfg.init('redmine.username', '')
cfg.init('redmine.password', '')
cfg.init('redmine.token', '')
cfg.init('project.id', '')
cfg.init('release.tracker_id', '')
cfg.init('release.subject', 'Релиз %s')
cfg.init('release.done_status_id', '')
cfg.init('release.filter_custom_fields', [], list)


def get_rd():
    return Redmine(cfg['redmine.host'],
                   username=cfg['redmine.username'], password=cfg['redmine.password'], key=cfg['redmine.token'])


@click.group('RedmineCli')
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)
    ctx.obj['redmine'] = get_rd()


@cli.command()
def config():
    """Настройки"""
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
@click.pass_context
def version(ctx):
    """Версии проекта"""
    rd = ctx.obj['redmine']
    versions = get_last_versions(rd, cfg['project.id'])
    for v in versions:
        click.echo(v)


@cli.group()
def release():
    """Управление релизами"""
    pass


@release.command()
@click.pass_context
def create(ctx):
    """Создать релиз"""
    rd = ctx.obj['redmine']
    user = rd.user.get('current')
    versions = get_last_versions()
    versions_map = {str(v): v for v in versions}

    release_version = questionary.select('Версия', choices=list(versions_map.keys())).ask()
    number = questionary.autocomplete('Номер релиза', choices=gen_number_release()).ask()
    description = questionary.text('Описание задачи').ask()

    memberships = {str(m.user): m.user.id for m in get_memberships(rd, cfg['project.id'])}

    assigned = questionary.autocomplete('Назначена', choices=list(memberships.keys()), default=str(user)).ask()

    custom_fields = []
    for cf_id, cf in get_custom_fields(rd, filtered=cfg['release.filter_custom_fields']).items():
        default_select = None

        possible_values = [v.get('value') for v in get_cf_values(rd, cf_id)]
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
        result = rd.issue.create(
            project_id=cfg['project.id'],
            tracker_id=cfg['release.tracker_id'],
            subject=cfg['release.subject'] % number,
            fixed_version_id=release_version.id,
            assigned_to_id=memberships.get(assigned),
            description=description,
            custom_fields=custom_fields
        )
        click.echo(click.style(f'Создана задача № {result.id}', bold=True, blink=True))


@release.command('list')
@click.option('--all', 'all_list', is_flag=True, default=False)
@click.option('-l', '--limit', 'limit', type=int, show_default=30)
@click.option('--me', 'me', is_flag=True, default=False)
@click.pass_context
def ls(ctx, all_list, limit, me):
    """Список релизов"""
    rd = ctx.obj['redmine']
    if not all_list:
        click.echo('Не опубликованные релизы')
    for iss in rd.issue.filter(project_id=cfg['project.id'], tracker_id=cfg['release.tracker_id'],
                               sort='created_on:desc', limit=limit, assigned_to_id='me' if me else '*'):
        if iss.status.id != int(cfg['release.done_status_id']) or all_list:
            echo_text = f'#{iss.id} {str(iss)} {iss.status.name}'
            click.echo(echo_text)


@cli.command('custom_field')
def c_fields():
    """Настраевыемые поля"""
    for cf_id, cf in get_custom_fields().items():
        click.echo(f'ID: {cf_id} = {str(cf)}')
        if cf_id == 2:
            print(dir(cf))


@cli.command('members')
@click.pass_context
def memberships(ctx):
    """Участники проекта"""
    rd = ctx.obj['redmine']
    for m in get_memberships(rd, cfg['project.id']):
        click.echo(str(m.user))


@cli.group()
def issue():
    """Задачи"""
    pass


@issue.command('list')
@click.option('--me', 'assigned_current', is_flag=True, default=True)
@click.option('--open', 'is_open', is_flag=True, default=True)
@click.option('--closed', 'is_open', is_flag=True, default=False)
@click.option('-v', 'is_open', is_flag=True, default=False)
@click.pass_context
def issue_list(ctx, assigned_current, is_open):
    """Список задач"""
    rd = ctx.obj['redmine']
    current_user = rd.user.get('current')
    assigned_to_id = current_user.id if assigned_current else None
    for issue in rd.issue.filter(project_id=cfg['project.id'], status_id='open' if is_open else 'closed', assigned_to_id=assigned_to_id):
        click.secho(f'#{issue.id} {str(issue)}', bold=True)


if __name__ == '__main__':
    cfg.sync()
    cli(obj={})
