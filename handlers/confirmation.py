from aliceio import F, Router
from aliceio.fsm.context import FSMContext
from aliceio.types import Message, Response
from utils.declension_fio import declension
from fsm.states import PatientInfo
from utils.dates_utils import format_dates_russian
from services.redis_service import redis_service
from handlers.appointment import PatientAppointmentHandlers
from handlers.patient_introduction import PatientIntroductionHandlers
from handlers.doctor_selection import DoctorSelectionHandler
from handlers.schedule_selection import ScheduleSelectionHandler
from pytrovich.enums import Case
import re

router = Router()

# # Списки подтверждающих и отрицающих фраз
# CONFIRM_PHRASES = ["да", "ага", "конечно", "давай", "хорошо", "ок", "окей", "yes", "yeah", "угу", "согласен", "согласна"]
# DENY_PHRASES = ["нет", "не", "не надо", "не нужно", "отмена", "отменить", "no", "not", "отказ"]
#
# def contains_confirmation(text, phrases):
#     # Создаем множество слов из текста
#     words_set = set(re.findall(r'\b\w+\b', text.lower()))
#     # Создаем множество фраз для подтверждения (в нижнем регистре)
#     phrases_set = set(phrase.lower() for phrase in phrases)
#     # Проверяем пересечение множеств
#     return bool(words_set & phrases_set)


class ConfirmationHandlers:
    #
    # YES
    async def handle_yes(self, message: Message, state: FSMContext) -> Response:
        user_text = message.original_text.lower()
        user_data = await state.get_data()
        next_step = user_data.get("next_step", None)
        previus_step = user_data.get("previus_step", None)

        print(f"next_step: {next_step}")
        print(f"previus_step: {previus_step}")

        # Начать записывать вас к врачу (процесс запрос слотов и тд)?
        if next_step == 'PatientInfo.ask_post':
            await state.set_state(PatientInfo.ask_post)
            await state.update_data(next_step=None, previus_step=None)
            doctor_selection_handler = DoctorSelectionHandler()
            return await doctor_selection_handler.handle_ask_post(message, state)

        # Записать вас к конкретному врачу? (сама запись)
        if next_step == 'PatientInfo.appointment':
            await state.set_state(PatientInfo.appointment)
            await state.update_data(next_step=None, previus_step=None)
            patient_appointment = PatientAppointmentHandlers()
            return await patient_appointment.handle_appointment(message, state)

        # Записать другого человека?
        elif next_step == 'ask_appointment_other':
            user_id = message.session.user_id
            await state.clear()
            redis_service.delete_by_pattern(f"user:{user_id}")
            await state.set_state(PatientInfo.getting_name)
            await state.update_data(next_step=None, previus_step=None)
            return Response(
                text="Назовите его фамилию, имя и отчество.",
                tts="Назовите его фамилию, имя и отчество."
            )

        # Записать вас на предложенную дату? [переход на выбор времени]
        elif next_step == 'answer_choose_time':
            await state.set_state(PatientInfo.getting_expected_time)
            await state.update_data(next_step=None, previus_step=None)
            schedule_selection_handler = ScheduleSelectionHandler()
            return await schedule_selection_handler.answer_choose_time(message, state)

        # Записать вас на предложенную дату? [переход на запрос ожидаемого времени]
        elif next_step == 'ask_expected_time':
            await state.set_state(PatientInfo.getting_expected_time)
            await state.update_data(next_step=None, previus_step=None)
            schedule_selection_handler = ScheduleSelectionHandler()
            return await schedule_selection_handler.ask_expected_time(message, state)

        print('NOT confirm')
        return Response(
            text="Извините, данный маршрут еще в разработке",
            tts="Извините, данный маршрут еще в разработке"
        )

    #
    # NOO
    async def handle_no(self, message: Message, state: FSMContext) -> Response:
        user_text = message.original_text.lower()
        user_data = await state.get_data()
        next_step = user_data.get("next_step", None)
        previus_step = user_data.get("previus_step", None)


        print(f"next_step: {next_step}")
        print(f"previus_step: {previus_step}")

        # Записать вас?
        if previus_step == 'ask_appointment_you':
            user_id = message.session.user_id
            redis_service.delete_by_pattern(f"user:{user_id}")
            await state.set_state(PatientInfo.confirmation)
            await state.update_data(
                next_step='ask_appointment_other',
                previus_step='cancel_all',
            )
            return Response(
                text="Вы хотите записать другого человека?",
                tts="Вы хотите записать другого человека?"
            )

        if previus_step in ['ask_appointment_time', 'ask_expected_time', 'ask_expected_date']:
            await state.update_data(next_step=None, previus_step=None)
            await state.set_state(PatientInfo.getting_expected_date)
            return Response(
                text="На какую дату вас записать?",
                tts="На какую дату вас записать?"
            )

        if previus_step == 'ask_time':
            await state.update_data(next_step=None, previus_step=None)
            await state.set_state(PatientInfo.getting_time)
            schedule_selection_handler = ScheduleSelectionHandler()
            return await schedule_selection_handler.answer_choose_time(message, state)

        await state.set_state(PatientInfo.zero)
        return Response(
            text="Хорошо, если передумаете - просто скажите 'Записаться на прием'.",
            tts="Хорошо, eсли передумаете - просто скажите - 'Записаться на прием'."
        )


    async def idontnow(self, message: Message, state: FSMContext) -> Response:
        return Response(
            text="Извините, ответ не распознан. Пожалуйста, ответьте 'да' или 'нет'.",
            tts="Извините, ответ не распознан. - Пожалуйста, ответьте 'да' или 'нет'."
        )

# Регистрация обработчиков
def setup_confirmations_handlers(
    router: Router
):
    handlers = ConfirmationHandlers()

    router.message.register(
        handlers.handle_yes,
        PatientInfo.confirmation,
        (F.command == "да") |
        (F.command == "ага") |
        (F.command == "угу") |
        (F.command == "конечно") |
        (F.command == "давай") |
        (F.command == "хорошо") |
        (F.command == "ок") |
        (F.command == "окей") |
        (F.command == "согласен") |
        (F.command == "согласна") |
        (F.command == "верно") |
        (F.command == "правильно") |
        (F.command == "отлично") |
        (F.command == "да-да") |
        (F.command == "ладно") |
        (F.command == "подтверждаю") |
        (F.command == "готов")
    )

    router.message.register(
        handlers.handle_no,
        PatientInfo.confirmation,
        (F.command == "нет") |
        (F.command == "не") |
        (F.command == "не надо") |
        (F.command == "не нужно") |
        (F.command == "отмена") |
        (F.command == "отменить") |
        (F.command == "отказ") |
        (F.command == "нет-нет") |
        (F.command == "не согласен") |
        (F.command == "не согласна") |
        (F.command == "нет, спасибо") |
        (F.command == "спасибо, не надо") |
        (F.command == "спасибо, не нужно")
    )

    router.message.register(
        handlers.idontnow,
        PatientInfo.confirmation
    )
