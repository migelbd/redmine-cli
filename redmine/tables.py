from rich.table import Table, Style, box


def get_table_for_issues() -> Table:
    tb = Table(show_header=True, header_style='bold magenta')
    tb.add_column('№', style='dim')
    tb.add_column('Наименование')
    tb.add_column('Статус')
    tb.add_column('Готовность', justify='center')
    tb.add_column('Назначено')
    tb.add_column('Автор')
    tb.add_column('Версия')

    return tb


def get_table_for_release() -> Table:
    tb = Table(show_header=True, header_style='bold magenta')
    tb.add_column('№', style='dim')
    tb.add_column('Наименование')
    tb.add_column('Статус')
    tb.add_column('Назначено')
    tb.add_column('Автор')

    return tb


def get_table_for_versions() -> Table:
    tb = Table(show_header=True, header_style='bold magenta', caption='Версии проекта')
    tb.add_column('№', style='dim')
    tb.add_column('Дата')
    tb.add_column('Создано')
    return tb