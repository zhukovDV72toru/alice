from datetime import datetime
from typing import List, Optional


def format_date_russian(date_string, input_format='%d.%m.%Y', with_year=False):
    months_ru = [
        'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ]

    date_obj = datetime.strptime(date_string, input_format)
    if with_year:
        return f"{date_obj.day} {months_ru[date_obj.month - 1]} {date_obj.year}"
    else:
        return f"{date_obj.day} {months_ru[date_obj.month - 1]}"


def format_dates_russian(date_strings, with_year=False):
    months_ru = [
        'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ]


    if with_year:
        return [
            f"{datetime.strptime(d, '%d.%m.%Y').day} {months_ru[datetime.strptime(d, '%d.%m.%Y').month - 1]} {datetime.strptime(d, '%d.%m.%Y').year}"
            for d in date_strings
        ]
    else:
        return [
            f"{datetime.strptime(d, '%d.%m.%Y').day} {months_ru[datetime.strptime(d, '%d.%m.%Y').month - 1]}"
            for d in date_strings
        ]




def find_nearest_date(
        date_strings: List[str],
        expected_date: datetime,
        allow_earlier: bool = False,
        date_format: str = "%d.%m.%Y"
) -> Optional[datetime]:
    """
    Находит ближайшую дату к expected_date из списка строк.

    Args:
        date_strings: Список строк с датами
        expected_date: Ожидаемая дата для сравнения
        allow_earlier: Разрешить поиск дат ранее expected_date
        date_format: Формат даты в строке (по умолчанию DD.MM.YYYY)
    Returns:
        Ближайшая дата или None, если не найдено подходящих дат
    """
    nearest_date = None
    min_diff = float('inf')

    for date_str in date_strings:
        try:
            date_obj = datetime.strptime(date_str.strip(), date_format)

            # Проверяем ограничение по дате
            if not allow_earlier and date_obj < expected_date:
                continue

            # Вычисляем разницу
            diff = abs((date_obj - expected_date).total_seconds())

            if diff < min_diff:
                min_diff = diff
                nearest_date = date_obj

        except ValueError:
            continue

    return nearest_date


def find_nearest_time(
        time_strings: List[str],
        target_time_str: str,
        allow_earlier: bool = False,
        time_format: str = "%H:%M"

) -> Optional[str]:
    """
    Упрощенная версия, работающая только с часами и минутами, без учета перехода через полночь
    """

    def time_to_minutes(time_str: str) -> Optional[int]:
        """Преобразует строку времени в количество минут с начала дня"""
        try:
            time_obj = datetime.strptime(time_str.strip(), time_format).time()
            return time_obj.hour * 60 + time_obj.minute
        except ValueError:
            return None

    target_minutes = time_to_minutes(target_time_str)
    if target_minutes is None:
        return None

    valid_times = []

    for time_str in time_strings:
        minutes = time_to_minutes(time_str)
        if minutes is not None:
            valid_times.append((time_str, minutes))

    if not valid_times:
        return None

    # Фильтруем по allow_earlier
    if not allow_earlier:
        valid_times = [(s, m) for s, m in valid_times if m >= target_minutes]
        if not valid_times:
            return None

    # Находим ближайшее время
    nearest_time_str, _ = min(
        valid_times,
        key=lambda item: abs(item[1] - target_minutes)
    )

    return nearest_time_str