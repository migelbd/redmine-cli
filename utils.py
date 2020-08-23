from datetime import date, timedelta


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