from aliceio import F, Router
from aliceio.fsm.context import FSMContext
from aliceio.types import Message, Response
from fsm.states import PatientInfo
from services.redis_service import redis_service
from aliceio.fsm.state import State, StatesGroup
from aliceio.filters import StateFilter
from handlers.doctor_selection import DoctorSelectionHandler

router = Router()


class HelpHandlers:
    async def help_handler(self, message: Message, state: FSMContext) -> Response:        
        """Обработчик команды помощи"""
        about_text = (
            "Навык для записи на прием к врачу в медицинские организации Тюменской области.\n"
            "Для запуска навыка скажи: Алиса запусти навык 'Запись к врачу Тюменская область'\n"
            "Вот что нужно сделать далее:\n"
            " - Укажите свои данные\n"
            " - Выберите медицинскую организацию и врача\n"
            " - Назначьте время\n"
            " - Подтвердите запись\n"
        )

        about_text_tts = (
            "Навык для записи на прием к врачу в медицинские организации Тюменской области.\n"
            "Для запуска навыка скажи: - Алиса запусти навык 'Запись к врачу Тюменская область'\n"
            "Вот что нужно сделать далее: - \n"
            " - Укажите свои данные\n"
            " - Выберите медицинскую организацию и врача\n"
            " - Назначьте время\n"
            " - Подтвердите запись\n"
        )
        
        return Response(
            text=about_text,
            tts=about_text_tts
        )
        
    async def restart_handler(self, message: Message, state: FSMContext) -> Response:
        """Обработчик сброса состояния и начала заново"""

        # TODO разделить начать сначала(без очистки организаций и смены фио)
        # и полную очистку данных пациента
            
        user_id = message.session.user_id
        
        # Очищаем состояние
        await state.clear()
        redis_service.delete_by_pattern(f"user:{user_id}")
        await state.set_state(PatientInfo.getting_name)
        
        return Response(
            text="Начинаем заново. Пожалуйста, назовите фамилию, имя и отчество.",
            tts="Начинаем заново. - Пожалуйста, назовите фамилию, имя и отчество."
        )
        
    async def about_handler(self, message: Message, state: FSMContext) -> Response:
        """Обработчик информации о навыке"""
        about_text = (
            "Навык для записи на прием к врачу в медицинские организации Тюменской области.\n"
            "Я помогаю записаться к врачу в Тюменской области. Процесс прост: вводите ФИО, дату рождения, телефон, выбираете врача, медорганизацию, время и подтверждаете запись.\n"
            "Для запуска навыка скажи: Алиса запусти навык 'Запись к врачу Тюменская область'\n"
            "Для записи на прием скажи: 'Запиши к врачу' и следуй указаниям навыка"
        )

        about_text_tts = (
            "Навык для записи на прием к врачу в медицинские организации Тюменской области.\n"
            "Я помогаю записаться к врачу в Тюменской области. Процесс прост: вводите ФИО, дату рождения, телефон, выбираете врача, медорганизацию, время и подтверждаете запись.\n"
            "Для запуска навыка скажи: - Алиса запусти навык 'Запись к врачу Тюменская область'\n"
            "Для записи на прием скажи:  - 'Запиши к врачу' и следуй указаниям навыка"
        )

        return Response(
            text=about_text,
            tts=about_text_tts
        )

    async def ping_pong_handler(self, message: Message, state: FSMContext) -> Response:
        """Обработчик пинга"""
        text = "pong"

        return Response(
            text=text,
            tts=text
        )

    async def step_help_handler(self, message: Message, state: FSMContext) -> Response:
        """Обработчик помощи на определенном шаге"""
        current_state = await state.get_state()

        if current_state == PatientInfo.getting_dob:
            text = f"Cкажите вашу дату рождения в формате ДД.ММ.ГГГГ."
            tts = f"Cкажите вашу дату рождения в формате - день - месяц - год. Месяц лучше называть названием, а не числом"
            return Response(text=text, tts=tts)

        if current_state == PatientInfo.getting_phone:
            text = f"Скажите номер телефона в формате +7(999)999-99-99"
            tts = f"Скажите номер телефона в формате плюс семь - и далее"
            return Response(text=text, tts=tts)

        if current_state == PatientInfo.getting_snils:
            text = f"Введите номер СНИЛС в формате 'как в документе'"
            tts = f"Введите номер СНИЛС в формате 'как в документе'"
            return Response(text=text, tts=tts)

        if current_state == PatientInfo.getting_post:
            handler = DoctorSelectionHandler()
            return await handler.show_available_post(message, state)

        if current_state == PatientInfo.getting_mo:
            text = f"Можно ввести намер пункта(например 'первый', 'третий'), или часть адреса. При похожих адресах распознавание может работать плохо - называйте номер пункта"
            tts = f"Можно ввести намер пункта(например 'первый', 'третий'), или часть адреса. При похожих адресах распознавание может работать плохо - называйте номер пункта"
            return Response(text=text, tts=tts)

        if current_state == PatientInfo.getting_medic:
            text = f"Назовите фамилию врача из списка"
            tts = f"Назовите фамилию врача из списка"
            return Response(text=text, tts=tts)

        if current_state == PatientInfo.getting_expected_date:
            text = f"Можно указать желаемую дату в формате д.м.г, если указанная дата недоступна для записи - будет предложена ближайшая. \nНаберите 'Список' для отображения списка доступных дат.\nНаберите 'ближайшая' для выбора ближайшей даты"
            tts = f"Можно указать желаемую дату в формате - день - месяц - год. Месяц лучше называть названием, а не числом. Если указанная дата недоступна для записи - будет предложена ближайшая. \nСкажите 'Список' для отображения списка доступных дат.\nСкажите 'ближайшая' для выбора ближайшей даты"
            return Response(text=text, tts=tts)

        if current_state == PatientInfo.getting_expected_time:
            text = f"Можно указать желаемое время в формате чч:мм, если указанное время недоступно для записи - будет предложено ближайшее. \nНаберите 'Список' для отображения списка доступных слотов"
            tts = f"Можно указать желаемое время в формате час - минута, если указанное время недоступно для записи - будет предложено ближайшее. \nСкажите 'Список' для отображения списка доступных слотов"
            return Response(text=text, tts=tts)

        if current_state == PatientInfo.getting_date:
            text = f"Можно указать желаемую дату в формате д.м.г, если указанная дата недоступна для записи - будет предложена ближайшая. \nНаберите 'Список' для отображения списка доступных дат.\nНаберите 'ближайшая' для выбора ближайшей даты"
            tts = f"Можно указать желаемую дату в формате в формате - день - месяц - год. Месяц лучше называть названием, а не числом. Если указанная дата недоступна для записи - будет предложена ближайшая. \nСкажите 'Список' для отображения списка доступных дат.\nСкажите 'ближайшая' для выбора ближайшей даты"
            return Response(text=text, tts=tts)

        if current_state == PatientInfo.getting_time:
            text = f"Можно указать желаемое время в формате чч:мм, если указанное время недоступно для записи - будет предложено ближайшее. \nНаберите 'Список' для отображения списка доступных слотов"
            tts = f"Можно указать желаемое время в формате в формате час - минута, если указанное время недоступно для записи - будет предложено ближайшее. \nСкажите 'Список' для отображения списка доступных слотов"
            return Response(text=text, tts=tts)

        print(f"STEP HELP NOT DEFINED: {current_state}")
        return await self.help_handler(message, state)


# Регистрация обработчиков
def setup_help_handlers(
    router: Router
):
    handlers = HelpHandlers()

    step_help_commands = (
        (F.command == "помощь") |
        (F.command == "help") |
        (F.command == "помоги") |
        (F.command == "что указать") |
        (F.command == "что сказать")
    )

    router.message.register(handlers.step_help_handler, StateFilter(PatientInfo), step_help_commands)

    router.message.register(
        handlers.help_handler,
        (F.command == "помощь") |
        (F.command == "помошь") |
        (F.command == "помощ") |
        (F.command == "help") |
        (F.command == "что ты умеешь") |
        (F.command == "что ты умеешь?") |
        (F.command == "что умеешь") |
        (F.command == "что умеешь?")
    )
    
    router.message.register(
        handlers.restart_handler,
        (F.command == "сброс") | 
        (F.command == "начать сначала") 
    )    
    
    router.message.register(
        handlers.about_handler,
        (F.command == "о навыке") | 
        (F.command == "о себе") 
    )

    router.message.register(
        handlers.ping_pong_handler,
        (F.original_utterance == "ping")
    )
