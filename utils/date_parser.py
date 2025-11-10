from datetime import date, datetime

async def get_birth_date_from_entities(entities):
    """
    Возвращает ISO‑дату (YYYY-MM-DD) из первой найденной
    сущности типа YANDEX.DATETIME в списке `entities`.
    Если такой сущности нет – возвращает None.
    """
    for ent in entities:
        if ent.type == 'YANDEX.DATETIME':
            dt = ent.value
            if dt.year is not None and dt.month is not None and dt.day is not None:
                year = dt.year
                if year < 1000:
                    year += 1900
                return date(year, dt.month, dt.day)
    return None
async def get_iso_date_from_entities(entities):
    """
    Возвращает ISO‑дату (YYYY-MM-DD) из первой найденной
    сущности типа YANDEX.DATETIME в списке `entities`.
    Если такой сущности нет – возвращает None.
    """
    for ent in entities:
        if ent.type == 'YANDEX.DATETIME':
            dt = ent.value
            if dt.year is None:
                year = datetime.now().year
            else:
                year = dt.year
                if year < 1000:
                    year += 2000
            if year is not None and dt.month is not None and dt.day is not None:
                if dt.hour is not None and dt.minute is not None:
                    return datetime(year, dt.month, dt.day, dt.hour, dt.minute, 0)
                else:
                    return datetime(year, dt.month, dt.day)
    return None

async def get_time_from_entities(entities):
    """
    Возвращает строку времени в формате часы:минуты из первой найденной
    сущности типа YANDEX.DATETIME в списке `entities`.
    Если такой сущности нет – возвращает None.
    """
    for ent in entities:
        if ent.type == 'YANDEX.DATETIME':
            dt = ent.value
            if dt.hour is not None and dt.minute is not None:
                hour_str = str(dt.hour).zfill(2)
                minute_str = str(dt.minute).zfill(2)
                return f"{hour_str}:{minute_str}"

    if len(entities) <= 3 and all(entity.type == 'YANDEX.NUMBER' for entity in entities) and len(entities) > 0:
        hour = entities[0].value
        minute = entities[1].value
        if 0 <= hour < 24 and 0 <= minute <= 59:
            hour_str = str(hour).zfill(2)
            minute_str = str(minute).zfill(2)
            return f"{hour_str}:{minute_str}"
    return None
