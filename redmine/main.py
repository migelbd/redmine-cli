import os

import click
import profig
import questionary
from redminelib import Redmine
from prettytable import PrettyTable
from redmine.utils import get_last_versions, gen_number_release, get_memberships, get_custom_fields, get_cf_values, \
    get_current_project_version, get_trackers_project, get_row_data
from webbrowser import open as open_web_url

HOME_PATH = os.getenv('USERPROFILE')
CFG_PATH = os.path.join(HOME_PATH, '.redmine.cfg')
cfg = profig.Config(CFG_PATH, encoding='utf-8')

cfg.init('redmine.host', 'localhost')
cfg.init('redmine.username', '')
cfg.init('redmine.password', '')
cfg.init('redmine.token', '')
cfg.init('project.id', '')
cfg.init('release.tracker_id', 6)
cfg.init('release.subject', 'Релиз %s')
cfg.init('release.done_status_id', 12)
cfg.init('release.filter_custom_fields', [13, 2], list)
cfg.init('issue.filter_custom_fields', [13, 2], list)
cfg.init('user.me_query_id', 0, int)


def get_rd():
    return Redmine(cfg['redmine.host'],
                   username=cfg['redmine.username'], password=cfg['redmine.password'], key=cfg['redmine.token'])


@click.group('RedmineCli')
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)
    ctx.obj['redmine'] = get_rd()


@cli.command()
@click.option('-f', 'file', is_flag=True, help='Показать путь к файлу')
def config(file):
    """Настройки"""
    if file:
        click.echo(CFG_PATH)
    else:
        config_data = {}
        config_data['redmine.host'] = questionary.text('Укажите URL').ask()
        config_data['redmine.token'] = questionary.text('Укажите Token').ask()
        if not config_data['redmine.token']:
            config_data['redmine.username'] = questionary.text('Укажите Логин').ask()
            config_data['redmine.password'] = questionary.text('Укажите Пароль').ask()

        config_data['project.id'] = questionary.text('Укажите ProjectID').ask()

        for name, value in config_data.items():
            click.echo(f'{name}: {value}')
        if questionary.confirm('Всё верно?').ask():
            cfg.update(config_data.items())
            cfg.sync()


@cli.command('versions')
@click.pass_context
def versions_list(ctx):
    """Версии проекта"""
    rd = ctx.obj['redmine']
    versions = get_last_versions(rd, cfg['project.id'])
    current_version = get_current_project_version(rd, cfg['project.id'])
    click.secho(f'Текущая версия: {str(current_version)}', bold=True)
    click.echo('----')
    for v in versions:
        click.echo(v)


@cli.group()
def release():
    """Управление релизами"""
    pass


@release.command('create')
@click.option('-o', '--open', 'open_url', is_flag=True, default=False, help='После создания открыть в браузере')
@click.pass_context
def release_create(ctx, open_url):
    """Создать релиз"""
    rd = ctx.obj['redmine']
    user = rd.user.get('current')
    versions = get_last_versions(rd, cfg['project.id'])
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
        if open_url:
            open_web_url(f"{str(cfg['redmine.host']).strip('/')}/issues/{result.id}", new=True)


@release.command('list')
@click.option('--all', 'all_list', is_flag=True, default=False)
@click.option('-l', '--limit', 'limit', type=int, show_default=30)
@click.option('--me', 'me', is_flag=True, default=False)
@click.pass_context
def release_list(ctx, all_list, limit, me):
    """Список релизов"""
    rd = ctx.obj['redmine']
    tb = PrettyTable(('#', 'Наименование', 'Статус', 'Назначено', 'Автор',))
    if not all_list:
        click.echo('Не опубликованные релизы')
    for iss in rd.issue.filter(project_id=cfg['project.id'], tracker_id=cfg['release.tracker_id'],
                               sort='created_on:desc', limit=limit, assigned_to_id='me' if me else '*'):
        if iss.status.id != int(cfg['release.done_status_id']) or all_list:
            row = get_row_data(iss, ['id', 'subject', 'status', 'assigned_to', 'author'])
            tb.add_row(row)

    click.echo(tb.get_string())


@cli.command('custom_field')
@click.pass_context
def c_fields(ctx):
    """Настраевыемые поля"""
    rd = ctx.obj['redmine']
    for cf_id, cf in get_custom_fields(rd).items():
        click.echo(f'ID: {cf_id} = {str(cf)}')


@cli.command('members')
@click.pass_context
def memberships(ctx):
    """Участники проекта"""
    rd = ctx.obj['redmine']
    tb = PrettyTable(['#', 'ФИО', 'Роль'])
    for m in get_memberships(rd, cfg['project.id']):
        row = get_row_data(m.user, ('id', 'name'))
        row.append(', '.join([r.name for r in m.roles]))
        tb.add_row(row)

    click.echo(tb.get_string())


@cli.group()
def issue():
    """Задачи"""
    pass


@issue.command('list')
@click.option('--me', 'assigned_current', is_flag=True, default=False, help='Назначеные мне')
@click.option('--open', 'is_open', is_flag=True, default=False, help='Открытые задачи')
@click.option('-l', '--limit', 'limit', show_default=30, default=30, help='Лимит')
@click.option('-v', '--version', 'version', is_flag=True, default=False, help='Выбрать версию')
@click.pass_context
def issue_list(ctx, assigned_current, is_open, limit, version):
    """Список задач"""
    tb = PrettyTable(('#', 'Наименование', 'Статус', 'Готовность', 'Назначена', 'Автор', 'Версия',))
    rd = ctx.obj['redmine']
    versions = get_last_versions(rd, cfg['project.id'])
    versions_map = {str(v): v for v in versions}
    current_user = rd.user.get('current')
    assigned_to_id = current_user.id if assigned_current else None
    fixed_version_id = None
    filter_data = dict(
        project_id=cfg['project.id'],
        status_id='*',
        limit=limit,
        sort='id:desc'
    )
    if is_open:
        filter_data['status_id'] = 'open'

    if assigned_current:
        filter_data['assigned_to_id'] = assigned_to_id

    if version:
        selected_version = questionary.select('Выбирите версию:', choices=list(versions_map.keys()),
                                              default=get_current_project_version(rd, cfg['project.id'])).ask()
        fixed_version_id = versions_map[selected_version].id
    fields_data = (
        'id',
        'subject',
        'status',
        'done_ratio',
        'assigned_to',
        'author',
        'fixed_version',
    )

    for iss in rd.issue.filter(**filter_data):
        try:
            if version and hasattr(iss, 'fixed_version') and getattr(iss, 'fixed_version').id != fixed_version_id:
                continue
            if version and not hasattr(iss, 'fixed_version'):
                continue
            tb.add_row(get_row_data(iss, fields_data))
        except Exception as e:
            click.echo(str(e), err=True)
    click.echo(tb.get_string())


@issue.command('create')
@click.option('-o', '--open', 'open_url', is_flag=True, default=False, help='После создания открыть в браузере')
@click.pass_context
def issue_create(ctx, open_url):
    """Создать задачу"""
    rd = ctx.obj['redmine']

    versions = get_last_versions(rd, cfg['project.id'])
    versions_map = {str(v): v for v in versions}
    current_user = rd.user.get('current')
    memberships = {str(m.user): m.user.id for m in get_memberships(rd, cfg['project.id'])}
    trackers = get_trackers_project(rd, cfg['project.id'])
    trackers_map = {str(t): t for t in trackers}
    selected_tracker = questionary.select('Трекер', choices=list(trackers_map.keys())).ask()
    tracker_id = trackers_map.get(selected_tracker).id

    subject = questionary.text('Тема задачи').ask()
    description = questionary.text('Описание задачи').ask()
    assigned = questionary.autocomplete('Назначена', choices=list(memberships.keys()), default=str(current_user)).ask()
    fixed_version = questionary.select('Версия', choices=list(versions_map.keys())).ask()

    custom_fields = []
    for cf_id, cf in get_custom_fields(rd, filtered=cfg['issue.filter_custom_fields']).items():
        default_select = None

        possible_values = [v.get('value') for v in get_cf_values(rd, cf_id)]
        if cf.field_format == 'user':
            default_select = str(current_user)
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
        selected_fixed_version = versions_map[fixed_version]
        result = rd.issue.create(
            project_id=cfg['project.id'],
            tracker_id=tracker_id,
            subject=subject,
            fixed_version_id=selected_fixed_version.id,
            assigned_to_id=memberships.get(assigned),
            description=description,
            custom_fields=custom_fields
        )
        click.echo(click.style(f'Создана задача № {result.id}', bold=True))
        if open_url:
            open_web_url(f"{str(cfg['redmine.host']).strip('/')}/issues/{result.id}", new=True)


@issue.command('query')
@click.option('-l', '--limit', 'limit', default=50)
@click.option('-o', '--offset', 'offset', default=0)
@click.option('-s', '--save', 'saved', is_flag=True, default=False)
@click.pass_context
def issue_query(ctx, limit, offset, saved):
    """Сохраненные запросы"""
    rd = ctx.obj['redmine']
    tb = PrettyTable(('#', 'Наименование', 'Статус', 'Готовность', 'Назначена', 'Автор', 'Версия',))

    if saved:
        q_text = 'Выберите сохраненый запрос. Выбор будет сохранен в настройки'
    else:
        q_text = 'Выберите сохраненный запрос'
    if saved and cfg['user.me_query_id']:
        selected_query = rd.query.get(cfg['user.me_query_id'])
    else:
        query_map = {str(q): q for q in rd.query.all()}
        selected_query_name = questionary.select(q_text, list(query_map.keys())).ask()
        selected_query = query_map[selected_query_name]
        if saved:
            cfg.update([['user.me_query_id', selected_query.id]])
            cfg.sync()

    fields_data = (
        'id',
        'subject',
        'status',
        'done_ratio',
        'assigned_to',
        'author',
        'fixed_version',
    )
    for iss in rd.issue.filter(offset=offset, limit=limit, project_id=selected_query.project_id,
                               query_id=selected_query.id):
        row = get_row_data(iss, fields_data)
        tb.add_row(row)

    click.echo(tb.get_string())


@cli.command('open')
@click.argument('issue_id')
@click.pass_context
def open_issue(ctx, issue_id):
    """Открыть задачу в браузере"""
    rd = ctx.obj['redmine']
    try:
        issue = rd.issue.get(issue_id)
        open_web_url(f"{str(cfg['redmine.host']).strip('/')}/issues/{issue.id}", new=True)
    except Exception as e:
        click.echo(str(e), err=True)


def main():
    cfg.sync()
    cli(obj={})


if __name__ == '__main__':
    main()
