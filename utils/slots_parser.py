from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any
from lxml import etree

def group_slots_by_date(slots):
    result = defaultdict(list)

    for slot in slots:
        # Парсим строку в объект datetime
        dt = datetime.fromisoformat(slot.replace('Z', '+00:00'))

        # Извлекаем дату и время отдельно
        date_str = dt.strftime('%d.%m.%Y')
        time_str = dt.strftime('%H:%M')

        # Добавляем время в список для соответствующей даты
        result[date_str].append(time_str)

    # Сортируем времена для каждой даты
    for date in result:
        result[date].sort()
    return dict(result)

def prepare_slots(slots_elements, namespaces):
    slots = defaultdict(dict)
    for slot in slots_elements:
        slot_id = slot.xpath('ns:Slot_Id/text()', namespaces=namespaces)
        visit_time = slot.xpath('ns:VisitTime/text()', namespaces=namespaces)
        room = slot.xpath('ns:Room/text()', namespaces=namespaces)

        slot_id = slot_id[0] if slot_id else None
        visit_time = visit_time[0] if visit_time else None
        room = room[0] if room else None

        if not slot_id or not visit_time:
            continue

        dt = datetime.fromisoformat(visit_time.replace('Z', '+00:00'))
        date_str = dt.strftime('%d.%m.%Y')
        time_str = dt.strftime('%H:%M')

        slots[date_str][time_str] = {'time': time_str, 'room': room, 'slot_id': slot_id, 'date': date_str}

    return slots
