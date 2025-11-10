from typing import Any
import asyncio
from aliceio import F, Router
from celery.exceptions import TimeoutError as CeleryTimeoutError
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
from utils.dates_utils import format_date_russian
from services.profession_searcher import ProfessionSearcher
from services.org_searcher import OrgSearcher
from services.fio_searcher import FioSearcher
from celery_app.tasks.long_operations import process_create_appointment


router = Router()


class PatientAppointmentHandlers:
    async def handle_appointment(self, message: Message, state: FSMContext) -> Response:
        user_id = message.session.user_id
        patient_data = await state.get_data()
        selected_slot = redis_service.hget(f"user:{user_id}:session", "selected_slot")

        if selected_slot is None:
            print('handle_appointment error: slot empty')
            await state.set_state(PatientInfo.zero)
            return Response(
                text="Произошла ошибка, попробуйте сначала",
                tts="Произошла ошибка, - попробуйте сначала"
            )

        time = selected_slot['time']
        slot_id = selected_slot['slot_id']
        room = selected_slot['room']
        date = selected_slot['date']
        
        task = process_create_appointment.delay(patient_data, slot_id)
        await state.update_data(appointment_task_id=task.id)

        try:
            result_data = await asyncio.to_thread(task.get, timeout=3)
        except CeleryTimeoutError:
            await state.set_state(PatientInfo.awaiting_appointment_status)
            return Response(
                text="Оформляю запись, это может занять несколько секунд. Когда будете готовы, скажите «Проверить статус».",
                tts="Оформляю запись. - Это может занять несколько секунд. - Когда будете готовы, скажите - Проверить статус."
            )
        except Exception as exc:
            print(f"handle_appointment task error: {exc}")
            await state.update_data(appointment_task_id=None)
            task.forget()
            await state.set_state(PatientInfo.zero)
            return Response(
                text="Не удалось записаться, повторите позже",
                tts="Не удалось записаться, повторите позже",
                end_session=True
            )

        await state.update_data(appointment_task_id=None)
        task.forget()
        return await self._build_appointment_response(
            state,
            user_id,
            result_data,
            time,
            room,
            date
        )

    async def handle_check_appointment_status(self, message: Message, state: FSMContext) -> Response:
        user_id = message.session.user_id
        data = await state.get_data()
        task_id = data.get('appointment_task_id')

        if not task_id:
            await state.set_state(PatientInfo.zero)
            return Response(
                text="Не удалось найти запрос на запись. Попробуйте начать сначала",
                tts="Не удалось найти запрос на запись. - Попробуйте начать сначала",
                end_session=True
            )

        selected_slot = redis_service.hget(f"user:{user_id}:session", "selected_slot")
        if selected_slot is None:
            await state.set_state(PatientInfo.zero)
            return Response(
                text="Не удалось найти выбранное время. Попробуйте начать сначала",
                tts="Не удалось найти выбранное время. - Попробуйте начать сначала",
                end_session=True
            )

        task_result = process_create_appointment.AsyncResult(task_id)
        if not task_result.ready():
            return Response(
                text="Запрос еще обрабатывается. Пожалуйста, спросите о статусе чуть позже",
                tts="Запрос ещё обрабатывается. - Пожалуйста, спросите о статусе чуть позже"
            )

        if task_result.failed():
            await state.update_data(appointment_task_id=None)
            task_result.forget()
            await state.set_state(PatientInfo.zero)
            return Response(
                text="Не удалось записаться, повторите позже",
                tts="Не удалось записаться, повторите позже",
                end_session=True
            )

        await state.update_data(appointment_task_id=None)
        result_data = task_result.result
        task_result.forget()
        return await self._build_appointment_response(
            state,
            user_id,
            result_data,
            selected_slot['time'],
            selected_slot['room'],
            selected_slot['date']
        )

    async def handle_waiting_status_prompt(self, message: Message, state: FSMContext) -> Response:
        return Response(
            text="Запрос еще выполняется. Чтобы узнать результат, скажите «Проверить статус».",
            tts="Запрос ещё выполняется. - Чтобы узнать результат, скажите - Проверить статус."
        )

    async def _build_appointment_response(
        self,
        state: FSMContext,
        user_id: str,
        result_data: Any,
        time: str,
        room: str,
        date: str
    ) -> Response:
        result = None
        book_id = None
        if isinstance(result_data, dict):
            result = result_data.get('result')
            book_id = result_data.get('book_id')
        elif isinstance(result_data, (list, tuple)):
            if len(result_data) > 0:
                result = result_data[0]
            if len(result_data) > 1:
                book_id = result_data[1]

        print(result, book_id)

        if result == "SUCCESS":
            specialist = redis_service.hget(f"user:{user_id}:session", "selected_specialist")
            specialist_fio = specialist['fio']
            fio = declension(specialist_fio, Case.DATIVE)
            selected_date = redis_service.hget(f"user:{user_id}:session", "selected_date")
            await state.update_data(
                appointments={
                    selected_date: {
                        'book_id': book_id,
                        'selected_specialist': specialist,
                        'date': selected_date,
                        'time': time,
                        'room': room
                    }
                }
            )
            print(f"book_id: {book_id}")

            return Response(
                text=f"Вы записаны к {fio} {selected_date} в {time}, {room}",
                tts=f"Вы записаны к {fio} - {format_date_russian(selected_date)} - в {time}, - {room}",
                end_session=True
            )

        if result == "APPOINT_TIME_IS_BUSY":
            await state.set_state(PatientInfo.getting_medic)
            medics = redis_service.hget(f"user:{user_id}:session", "available_specialists")
            specialists = medics.keys()
            specialists = '\n'.join(specialists)
            return Response(
                text=f"Извините, запись невозможна. Время уже занято другим пациентом. Выберите врача:\n{specialists}",
                tts=f"Извините, запись невозможна. - Время уже занято другим пациентом. - Выберите врача:\n{specialists}",
                end_session=True
            )

        if result == "APPOINT_VISIT_TIME_HAS_PASSED":
            await state.set_state(PatientInfo.getting_medic)
            medics = redis_service.hget(f"user:{user_id}:session", "available_specialists")
            specialists = medics.keys()
            specialists = '\n'.join(specialists)
            return Response(
                text=f"Извините, запись невозможна. Время начала приема уже прошло. Выберите другое время.\nВыберите врача:\n{specialists}",
                tts=f"Извините, запись невозможна. - Время начала приема уже прошло. - Выберите другое время. -Выберите врача:\n{specialists}",
                end_session=True
            )

        if result == "APPOINT_PATIENT_REGISTERED_OTHER_SPECIALIST":
            await state.set_state(PatientInfo.getting_medic)
            medics = redis_service.hget(f"user:{user_id}:session", "available_specialists")
            specialists = medics.keys()
            specialists = '\n'.join(specialists)
            return Response(
                text=f"Извините, запись невозможна. Пациент уже записан на это время к другому специалисту. Выберите врача:\n{specialists}",
                tts=f"Извините, запись невозможна. - Пациент уже записан на это время к другому специалисту.  - Выберите врача: - {specialists}",
                end_session=True
            )

        if result == "APPOINT_PATIENT_REGISTERED_SPECIALIST":
            await state.set_state(PatientInfo.zero)
            redis_service.delete_by_pattern(f"user:{user_id}")
            return Response(
                text="Извините, запись невозможна. Пациент уже записан к этому специалисту.",
                tts="Извините, запись невозможна. - Пациент уже записан к этому специалисту.",
                end_session=True
            )

        if result == "APPOINT_TIME_AVAILABLE_PATIENT_OTHER_AGE":
            await state.set_state(PatientInfo.zero)
            redis_service.delete_by_pattern(f"user:{user_id}")
            return Response(
                text="Извините, запись невозможна. Выбранное время доступно только для записи пациентов в другом возрасте",
                tts="Извините, запись невозможна. Выбранное время доступно только для записи пациентов в другом возрасте",
                end_session=True
            )

        if result == "VACCINATION_COMPLETED":
            await state.set_state(PatientInfo.zero)
            redis_service.delete_by_pattern(f"user:{user_id}")
            return Response(
                text="Вакцинация уже выполнена гражданину",
                tts="Вакцинация уже выполнена гражданину",
                end_session=True
            )
        if result == "VACCINATION_TIME_NOT_COME":
            await state.set_state(PatientInfo.zero)
            redis_service.delete_by_pattern(f"user:{user_id}")
            return Response(
                text="Срок вакцинации не подошел",
                tts="Срок вакцинации не подошел",
                end_session=True
            )
        if result == "VACCINATIONS_MEDICAL_RECUSAL":
            await state.set_state(PatientInfo.zero)
            redis_service.delete_by_pattern(f"user:{user_id}")
            return Response(
                text="Медицинский отвод от прививок",
                tts="Медицинский отвод от прививок",
                end_session=True
            )

        print(f"handle_appointment error: {result}")
        await state.set_state(PatientInfo.zero)
        return Response(
            text="Не удалось записаться, повторите позже",
            tts="Не удалось записаться, повторите позже",
            end_session=True
        )

def setup_appointment_handlers(
        router: Router
):
    handlers = PatientAppointmentHandlers()

    router.message.register(
        handlers.handle_appointment,
        PatientInfo.appointment,
        F.nlu.entities
    )

    router.message.register(
        handlers.handle_check_appointment_status,
        PatientInfo.awaiting_appointment_status,
        (F.command == "проверить статус") |
        (F.command == "статус") |
        (F.command == "какой статус") |
        (F.command == "статус записи") |
        (F.command == "какой статус записи")
    )

    router.message.register(
        handlers.handle_waiting_status_prompt,
        PatientInfo.awaiting_appointment_status
    )