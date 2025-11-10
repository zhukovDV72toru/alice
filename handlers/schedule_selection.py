from aliceio import F, Router
from aliceio.fsm.context import FSMContext
from aliceio.types import Message, Response
from fsm.states import PatientInfo
from utils.declension_fio import declension
from utils.date_parser import get_iso_date_from_entities
from services.redis_service import redis_service
from services.patient_service import patient_service
from pytrovich.enums import Case
from datetime import datetime, timedelta
from utils.date_parser import get_time_from_entities
from utils.orgsPrepare import prepareOrgsList
from utils.dates_utils import format_dates_russian, find_nearest_date, find_nearest_time, format_date_russian
from services.profession_searcher import ProfessionSearcher
from services.org_searcher import OrgSearcher
from services.fio_searcher import FioSearcher
from typing import Any, Dict, List, Optional, Tuple

from handlers.doctor_selection import DoctorSelectionHandler

router = Router()


class ScheduleSelectionHandler:
    """Обработчик выбора расписания (дата, время)"""

    async def handle_given_expected_date(self, message: Message, state: FSMContext) -> Response:
        print('handle_given_expected_date')
        user_id = message.session.user_id
        entity = message.nlu.entities
        patient_data = await state.get_data()
        expected_date = await get_iso_date_from_entities(entity)

        print(f"entity: {entity}")
        print(f"expected_date: {expected_date}")
        print(f"user_text: {message.original_text.lower()}")

        if expected_date is None:
            user_text = message.original_text.lower()
            if any(phrase in user_text for phrase in ['сегодня', 'на ближайшую', 'ближайшую', 'ближайшая',' ближайшее', 'как можно быстрее', 'как можно скорее']):
                expected_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            elif any(phrase in user_text for phrase in ['завтра', 'на завтра']):
                expected_date = datetime.now() + timedelta(days=1)
            elif any(phrase in user_text for phrase in ['послезавтра', 'после завтра']):
                expected_date = datetime.now() + timedelta(days=2)
            elif any(phrase in user_text for phrase in ['выходные', 'выходной', 'на выходные', 'ближайшие выходные']):
                today = datetime.now().date()
                days_until_saturday = (5 - today.weekday()) % 7 or 7
                expected_date = today + timedelta(days=days_until_saturday)
            else:
                expected_date = None
                user_text = message.original_text.lower()
                if user_text in [
                    'список',
                    'помощь',
                    'пример',
                    'какие даты',
                    'какие есть даты',
                    'какая есть дата',
                    'какая есть',
                    'какие есть',
                    'свободные даты',
                    'свободная дата',
                    'покажи список',
                    'а какие есть',
                ]:
                    # Поиск ближайших
                    post_id = redis_service.hget(f"user:{user_id}:session", "post_id")
                    if post_id is None:
                        await state.set_state(PatientInfo.getting_post)
                        return Response(
                            text=f"Не выбрана должность врача. Выберите должность",
                            tts=f"Не выбрана должность врача. Выберите должность"
                        )
                    specialist = redis_service.hget(f"user:{user_id}:session", "selected_specialist")
                    if specialist is None:
                        await state.set_state(PatientInfo.getting_post)
                        return Response(
                            text=f"Не выбран врач. Выберите должность",
                            tts=f"Не выбран врач. Выберите должность"
                        )
                    specialist_snils = specialist['snils']
                    expected_date = datetime.now()
                    slots = patient_service.get_slots(patient_data, specialist_snils, post_id, expected_date)
                    if slots is None or len(slots) == 0:
                        return Response(
                            text=f"Слотов на ближайшее время нет, попробуйте другую дату",
                            tts=f"Слотов на ближайшую неделю нет, попробуйте другую дату"
                        )

                    redis_service.hset(f"user:{user_id}:session", "available_slots", slots, 900)
                    return await self.answer_choose_date(message, state)
                return Response(
                    text=f"Дата некорректна, выберите другую",
                    tts=f"Дата некорректна, - выберите другую"
                )


        today = datetime.now().date()
        next_year_date = today + timedelta(days=365)
        if expected_date.date() < today or expected_date.date() > next_year_date:
            return Response(
                text=f"Дата некорректна, выберите другую",
                tts=f"Дата некорректна, - выберите другую"
            )

        specialist = redis_service.hget(f"user:{user_id}:session", "selected_specialist")
        if specialist is None:
            await state.set_state(PatientInfo.getting_post)
            return Response(
                text=f"Не выбран врач. Выберите должность",
                tts=f"Не выбран врач. Выберите должность"
            )
        specialist_snils = specialist['snils']

        post_id = redis_service.hget(f"user:{user_id}:session", "post_id")
        if post_id is None:
            await state.set_state(PatientInfo.getting_post)
            return Response(
                text=f"Не выбрана должность врача. Выберите должность",
                tts=f"Не выбрана должность врача. - Выберите должность"
            )

        expected_date_str = expected_date.date().strftime('%d.%m.%Y')
        expected_time = expected_date.strftime('%H:%M')
        expected_time = None if expected_time == "00:00" else expected_time

        slots = patient_service.get_slots(patient_data, specialist_snils, post_id, expected_date)
        if slots is None or len(slots) == 0:
            return Response(
                text=f"Слотов на этот период нет, выберите другую дату",
                tts=f"Слотов на этот период нет, - выберите другую дату"
            )

        redis_service.hset(f"user:{user_id}:session", "available_slots", slots, 900)
        redis_service.hset(f"user:{user_id}:session", "expected_date", expected_date_str, 900)
        redis_service.hset(f"user:{user_id}:session", "expected_time", expected_time, 900)

        dates = list(slots.keys())

        if expected_date_str in dates:
            times_slots = slots[expected_date_str]
            times = list(times_slots.keys())
            redis_service.hset(f"user:{user_id}:session", "selected_date", expected_date_str, 900)

            if expected_time and expected_time in times:
                return await self.answer_guessed_all(message, state, expected_date_str, expected_time)

            if expected_time:
                nearest_time = find_nearest_time(times, expected_time, True)
                if nearest_time:
                    return await self.answer_nearest_time(message, state, expected_date_str, nearest_time)
                else:
                    return await self.answer_choose_time(message, state, "Выбранного времени нет")
            else:
                return await self.ask_expected_time(message, state)

        else:
            nearest_date = find_nearest_date(dates, expected_date)
            if nearest_date:
                redis_service.hset(f"user:{user_id}:session", "nearest_date", nearest_date.date().strftime('%d.%m.%Y'), 900)
                return await self.answer_suggest_another_date(message, state, expected_date_str, nearest_date.strftime('%d.%m.%Y'), expected_time)

        return Response(
            text=f"Слотов на этот период нет, выберите другую дату. Скажите 'Список' для вывода доступных дат",
            tts=f"Слотов на этот период нет, - выберите другую дату. - - Скажите - 'Список' - для вывода доступных дат"
        )

    async def handle_given_expected_time(self, message: Message, state: FSMContext) -> Response:
        print('handle_given_expected_time')
        user_id = message.session.user_id
        entity = message.nlu.entities
        expected_time = await get_time_from_entities(entity)
        print(f"expected_time: {expected_time}")

        if expected_time is None:
            user_text = message.original_text.lower()
            if any(phrase in user_text for phrase in ['сегодня', 'на ближайшую', 'ближайшую', 'на ближайшее', 'ближайшая', 'ближайшее', 'как можно быстрее', 'как можно скорее', 'ближайшее время', 'на ближайшее время']):
                expected_time = datetime.now().strftime('%H:%m')
            else:
                expected_time = None
                user_text = message.original_text.lower()
                if user_text in [
                    'список',
                    'помощь',
                    'пример',
                    'какие даты',
                    'какие есть даты',
                    'какая есть дата',
                    'какая есть',
                    'какое есть',
                    'какое есть время',
                    'какие есть',
                    'свободные даты',
                    'свободная дата',
                    'покажи список',
                    'а какие есть',
                ]:

                    return await self.answer_choose_time(message, state)

        if expected_time is None:
            return Response(
                text=f"Не удалось распознать время, повторите",
                tts=f"Не удалось распознать время, - повторите"
            )

        slots = redis_service.hget(f"user:{user_id}:session", "available_slots")
        selected_date_str = redis_service.hget(f"user:{user_id}:session", "selected_date")

        print(f"selected_date_str: {selected_date_str}")

        times_slots = slots[selected_date_str]
        times = list(times_slots.keys())
        if expected_time in times:
            return await self.answer_guessed_all(message, state, selected_date_str, expected_time)
        else:
            nearest_time = find_nearest_time(times, expected_time, True)
            if nearest_time:
                return await self.answer_nearest_time(message, state, selected_date_str, nearest_time)
            else:
                await state.set_state(PatientInfo.getting_expected_time)
                return Response(
                    text=f"Слотов на этот период нет, выберите другую дату. Скажите 'Список' для вывода доступных дат",
                    tts=f"Слотов на этот период нет, - выберите другую дату. - Скажите  - 'Список' -  для вывода доступных дат"
                )

    async def answer_guessed_all(self, message: Message, state: FSMContext, selected_date: str,
                                 selected_time: str) -> Response:
        print('answer_guessed_all')
        user_id = message.session.user_id
        redis_service.hset(f"user:{user_id}:session", "selected_date", selected_date, 900)
        redis_service.hset(f"user:{user_id}:session", "selected_time", selected_time, 900)

        specialist = redis_service.hget(f"user:{user_id}:session", "selected_specialist")
        if specialist is None:
            await state.set_state(PatientInfo.getting_post)
            return Response(
                text=f"Не выбран врач. Выберите должность",
                tts=f"Не выбран врач. - Выберите должность"
            )

        slots = redis_service.hget(f"user:{user_id}:session", "available_slots")
        times_slots = slots[selected_date]
        selected_slot = times_slots[selected_time]

        redis_service.hset(f"user:{user_id}:session", "selected_slot", selected_slot, 500)
        await state.set_state(PatientInfo.confirmation)
        await state.update_data(
            next_step='PatientInfo.appointment',
            previus_step='ask_expected_date',
        )

        specialist_fio = specialist['fio']
        fio = declension(specialist_fio, Case.DATIVE)
        return Response(
            text=f"Записать вас к {fio} {selected_date} в {selected_time}?",
            tts=f"Записать вас к {fio} - {format_date_russian(selected_date)} - в {selected_time}?",
        )

    async def answer_nearest_time(self, message: Message, state: FSMContext, selected_date: str,
                                  selected_time: str) -> Response:
        print('answer_nearest_time')
        user_id = message.session.user_id
        redis_service.hset(f"user:{user_id}:session", "selected_date", selected_date, 900)
        redis_service.hset(f"user:{user_id}:session", "selected_time", selected_time, 900)
        await state.set_state(PatientInfo.confirmation)
        await state.update_data(
            next_step='PatientInfo.appointment',
            previus_step='ask_expected_time',
        )

        specialist = redis_service.hget(f"user:{user_id}:session", "selected_specialist")
        if specialist is None:
            await state.set_state(PatientInfo.getting_post)
            return Response(
                text=f"Не выбран врач. Выберите должность",
                tts=f"Не выбран врач. - Выберите должность"
            )

        slots = redis_service.hget(f"user:{user_id}:session", "available_slots")
        times_slots = slots[selected_date]
        selected_slot = times_slots[selected_time]
        redis_service.hset(f"user:{user_id}:session", "selected_slot", selected_slot, 500)

        specialist_fio = specialist['fio']
        fio = declension(specialist_fio, Case.DATIVE)
        return Response(
            text=f"Ближайшая запись к {fio} доступна на  {selected_date} в {selected_time}. Записать?",
            tts=f"Ближайшая запись к {fio} доступна на - {format_date_russian(selected_date)} - в {selected_time}. Записать?",
        )

    async def answer_suggest_another_date(self, message: Message, state: FSMContext, expected_date: str, nearest_date: str, expected_time: str) -> Response:
        print('answer_suggest_another_date')
        user_id = message.session.user_id
        await state.set_state(PatientInfo.confirmation)

        if expected_time:
            slots = redis_service.hget(f"user:{user_id}:session", "available_slots")
            times_slots = slots[nearest_date]
            times = list(times_slots.keys())

            redis_service.hset(f"user:{user_id}:session", "selected_date", nearest_date, 900)
            selected_time = None

            if expected_time in times:
                selected_time = expected_time
            else:
                selected_time = find_nearest_time(times, expected_time, True)

            if selected_time:
                await state.update_data(next_step='PatientInfo.appointment', previus_step='ask_expected_date')
                redis_service.hset(f"user:{user_id}:session", "selected_time", selected_time, 900)
                selected_slot = times_slots[selected_time]
                redis_service.hset(f"user:{user_id}:session", "selected_slot", selected_slot, 500)
                return Response(
                    text=f"Слота на {expected_date} нет, записать вас на {nearest_date} в {selected_time}?",
                    tts=f"Слота на {format_date_russian(expected_date)} нет, - записать вас на {format_date_russian(nearest_date)} - в {selected_time}?"
                )

        await state.update_data(next_step='ask_expected_time', previus_step='ask_expected_date')

        user_text = message.original_text.lower()

        redis_service.hset(f"user:{user_id}:session", "selected_date", nearest_date, 900)
        if any(phrase in user_text for phrase in
               ['на ближайшую', 'ближайшую', 'ближайшая', 'как можно быстрее', 'как можно скорее']):
            return Response(
                text=f"Записать вас на {nearest_date}?",
                tts=f"Записать вас на {format_date_russian(nearest_date)}?"
            )
        else:
            return Response(
                text=f"Слота на {expected_date} нет, записать вас на {nearest_date}?",
                tts=f"Слота на {expected_date} нет, - записать вас на {format_date_russian(nearest_date)}?"
            )



    async def answer_choose_date(self, message: Message, state: FSMContext) -> Response:
        print('answer_choose_date')
        user_id = message.session.user_id
        # Остаться на текущем шаге
        # await state.set_state(PatientInfo.getting_date)
        await state.update_data(next_step=None, previus_step=None)

        specialist = redis_service.hget(f"user:{user_id}:session", "selected_specialist")
        if specialist is None:
            await state.set_state(PatientInfo.getting_post)
            return Response(
                text=f"Не выбран врач. Выберите должность",
                tts=f"Не выбран врач. - Выберите должность"
            )
        specialist_fio = specialist['fio']

        slots = redis_service.hget(f"user:{user_id}:session", "available_slots")
        dates = list(slots.keys())
        dates_ttl = format_dates_russian(dates)
        dates_list_ttl = ";\n - ".join(dates_ttl)
        date_list = ";\n".join(dates)
        specialist_in_dat = declension(specialist_fio, Case.DATIVE)

        return Response(
            text=f"Выберите одну из дат для записи к {specialist_in_dat}:\n{date_list}",
            tts=f"Выберите одну из дат для записи к {specialist_in_dat}: - \n{dates_list_ttl}"
        )

    async def handle_cancel_given_date(self, message: Message, state: FSMContext) -> Response:
        print('handle_cancel_given_date')
        user_id = message.session.user_id
        user_text = message.original_text.lower()
        if any(phrase in user_text for phrase in ['отмена', 'отменить', 'отбой', 'назад']):
            doctor_selection_handler = DoctorSelectionHandler()
            return await doctor_selection_handler.handle_show_mo(message, state)

        return Response(
            text="Не удалось распознать дату. Пожалуйста, повторите в формате ДД.ММ.ГГГГ.",
            tts="Не удалось распознать дату.- Пожалуйста, - повторите в формате - день - месяц - год."
        )

    async def handle_cancel_given_date_to_select_date(self, message: Message, state: FSMContext) -> Response:
        print('handle_cancel_given_date_to_select_date')
        user_id = message.session.user_id
        user_text = message.original_text.lower()
        if any(phrase in user_text for phrase in ['отмена', 'отменить', 'отбой', 'назад']):
            await state.set_state(PatientInfo.getting_expected_date)
            return Response(
                text=f"На какую дату вас записать?",
                tts=f"На какую дату вас записать?"
            )
        return Response(
            text="Не удалось распознать ответ",
            tts="Не удалось распознать ответ"
        )


    async def answer_choose_time(self, message: Message, state: FSMContext, additional_text: Optional[str] = None) -> Response:
        print('answer_choose_time')
        user_id = message.session.user_id
        selected_date_str = redis_service.hget(f"user:{user_id}:session", "selected_date")
        print(f"selected_date_str: {selected_date_str}")
        await state.set_state(PatientInfo.getting_time)
        await state.update_data(next_step=None, previus_step=None)

        slots = redis_service.hget(f"user:{user_id}:session", "available_slots")
        times_slots = slots[selected_date_str]
        times = list(times_slots.keys())
        times_list = ";\n".join(times)
        times_list_ttr = ";\n - ".join(times)

        if additional_text:
            return Response(
                text=f"{additional_text}\nВыберите время:\n{times_list}",
                tts=f"{additional_text}\nВыберите время: - \n{times_list_ttr}"
            )
        else:
            return Response(
                text=f"Выберите время:\n{times_list}",
                tts=f"Выберите время: - \n{times_list_ttr}"
            )

    async def ask_expected_time(self, message: Message, state: FSMContext) -> Response:
        print('ask_expected_time')
        user_id = message.session.user_id
        selected_date_str = redis_service.hget(f"user:{user_id}:session", "selected_date")
        print(f"selected_date_str: {selected_date_str}")
        await state.set_state(PatientInfo.getting_expected_time)

        return Response(
            text=f"На какое время вас записать?",
            tts=f"На какое время вас записать?"
        )


    async def handle_given_date(self, message: Message, state: FSMContext) -> Response:
        print('handle_given_date')
        user_id = message.session.user_id
        entity = message.nlu.entities
        selected_date = await get_iso_date_from_entities(entity)

        user_text = message.original_text.lower()
        if any(phrase in user_text for phrase in ['отмена', 'отменить', 'отбой', 'назад']):
            doctor_selection_handler = DoctorSelectionHandler()
            return await doctor_selection_handler.handle_show_mo(message, state)

        if not selected_date:
            return Response(
                text="Не удалось распознать дату. Пожалуйста, повторите в формате ДД.ММ.ГГГГ.",
                tts="Не удалось распознать дату.- Пожалуйста, - повторите в формате - день - месяц - год."
            )

        selected_date = selected_date.strftime('%d.%m.%Y')
        slots = redis_service.hget(f"user:{user_id}:session", "available_slots")

        try:
            times_slots = slots[selected_date]
        except KeyError:
            await state.set_state(PatientInfo.getting_medic)
            await state.set_state(PatientInfo.getting_expected_date)
            return Response(
                text=f"Ответ не распознан, на какую дату вас записать?",
                tts=f"Ответ не распознан, - на какую дату вас записать?"
            )

        redis_service.hset(f"user:{user_id}:session", "selected_date", selected_date, 900)
        return await self.answer_choose_time(message, state)

    async def handle_given_time(self, message: Message, state: FSMContext) -> Response:
        print('handle_given_time')
        user_id = message.session.user_id
        entity = message.nlu.entities
        selected_time = await get_time_from_entities(entity)
        print(f"selected_time: {selected_time}")

        if selected_time is None:
            return Response(
                text=f"Не удалось распознать время, повторите",
                tts=f"Не удалось распознать время, - повторите"
            )

        slots = redis_service.hget(f"user:{user_id}:session", "available_slots")
        specialist = redis_service.hget(f"user:{user_id}:session", "selected_specialist")
        specialist_fio = specialist['fio']
        selected_date = redis_service.hget(f"user:{user_id}:session", "selected_date")

        try:
            if slots is None:
                raise KeyError
            times_slots = slots[selected_date]
            if times_slots is None:
                raise KeyError
        except KeyError:
            await state.set_state(PatientInfo.zero)
            return Response(
                text=f"Произошла ошибка, попробуйте сначала",
                tts=f"Произошла ошибка, - попробуйте сначала"
            )

        try:
            times_slots = slots[selected_date]
            if times_slots is None:
                raise KeyError
            selected_slot = times_slots[selected_time]
        except KeyError:
            return Response(
                text=f"Не удалось распознать время, повторите",
                tts=f"Не удалось распознать время, - повторите"
            )

        redis_service.hset(f"user:{user_id}:session", "selected_slot", selected_slot, 500)
        selected_time = selected_slot['time']

        await state.set_state(PatientInfo.confirmation)
        await state.update_data(
            next_step='PatientInfo.appointment',
            previus_step='ask_appointment_time',
        )

        fio = declension(specialist_fio, Case.DATIVE)
        return Response(
                text=f"Записать вас к {fio} {selected_date} в {selected_time}?",
                tts=f"Записать вас к {fio} - {format_date_russian(selected_date)}  - в {selected_time}?",
        )


def setup_schedule_handlers(
        router: Router
):
    handlers = ScheduleSelectionHandler()

    router.message.register(
        handlers.handle_given_expected_date,
        PatientInfo.getting_expected_date
    )

    router.message.register(
        handlers.handle_given_expected_time,
        PatientInfo.getting_expected_time
    )

    router.message.register(
        handlers.handle_given_date,
        PatientInfo.getting_date,
        F.nlu.entities
    )

    router.message.register(
        handlers.handle_cancel_given_date_to_select_date,
        PatientInfo.getting_date
    )

    router.message.register(
        handlers.handle_given_time,
        PatientInfo.getting_time,
        F.nlu.entities
    )

    router.message.register(
        handlers.handle_cancel_given_date_to_select_date,
        PatientInfo.getting_time
    )