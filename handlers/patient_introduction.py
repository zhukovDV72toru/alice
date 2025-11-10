from aliceio import F, Router
from aliceio.fsm.context import FSMContext
from aliceio.types import Message, Response

from fsm.states import PatientInfo
from utils.date_parser import get_birth_date_from_entities
from utils.dates_utils import format_date_russian
from utils.gender_detector import detect_gender_by_name
from datetime import datetime, date
from services.redis_service import redis_service
from services.patient_service import patient_service
from validators.phone_number_validator import PhoneNumberValidator
from validators.snils_number_validator import SnilsNumberValidator
from pydantic import ValidationError
from celery_app.tasks.long_operations import process_get_mo
import uuid

router = Router()


class PatientIntroductionHandlers:
    async def new_session(self, message: Message, state: FSMContext) -> Response:
        user_id = message.session.user_id
        patient_data = await state.get_data()

        # Если есть фамилия, дата рождения -> переходим к выбору МО
        if patient_data.get('last_name') and patient_data.get('birth_date'): # and patient_data.get('phone')
            name_with_middle = patient_data.get('first_name').capitalize() + " " + (
                patient_data.get('middle_name').capitalize() if patient_data.get('middle_name') else '')
            session_id = str(uuid.uuid4())
            patient_data['fer_session_id'] = session_id
            patient_id = patient_service.find_patient(patient_data)
            if patient_id:
                await state.set_state(PatientInfo.confirmation)
                await state.update_data(
                    next_step='PatientInfo.ask_post',
                    previus_step='ask_appointment_you',
                    fer_session_id=session_id
                )

                redis_service.hset(f"user:{user_id}:session", "patient_id", patient_id, 900)
                result = process_get_mo.delay(user_id, patient_data, 109)
                result.forget()
                return Response(
                    text=f"Здравствуйте, {name_with_middle}, записать вас к врачу?",
                    tts=f"Здравствуйте, {name_with_middle}, записать вас к врачу?"
                )

        await state.clear()
        redis_service.delete_by_pattern(f"user:{user_id}")
        await state.set_state(PatientInfo.getting_name)
        text = (
            "Здравствуйте. Я помогу вам записаться на прием к врачу в городе Тюмень и Тюменской области.\n"
            "Для записи нужно будет последовательно указать личные данные, выбрать организацию и врача, время посещения.\n"
            "Продолжая диалог, вы даете согласие на обработку своих персональных данных и дистанционное сопровождение.\n"
            "Пожалуйста, назовите фамилию, имя и отчество для начала процесса запуска."
        )
        tts = (
            "Здравствуйте. Я помогу вам записаться на прием к врачу в городе Тюмень и Тюменской области.\n"
            "Продолжая диалог, вы даете согласие на обработку своих персональных данных и дистанционное сопровождение.\n"
            "Пожалуйста, назовите фамилию, имя и отчество пациента."
        )
        return Response(
            text=text,
            tts=tts
        )

    async def handle_given_name(self, message: Message, state: FSMContext) -> Response:
        last_name = None
        first_name = None
        middle_name = None

        if message.nlu is None or message.nlu.entities is None:
            # user_text = message.original_text.lower()
            # print(f"user fio by original: {user_text}")
            # fio_parts = user_text.split(' ')
            # last_name = fio_parts[0] if len(fio_parts) > 0 else ''
            # first_name = fio_parts[1] if len(fio_parts) > 1 else ''
            # middle_name = ' '.join(fio_parts[2:]) if len(fio_parts) > 2 else ''
            return Response(
                text="Имя не распознано, пожалуйста, повторите",
                tts="Имя не распознано, пожалуйста, повторите"
            )
                        
        else:
            entity = next((e for e in message.nlu.entities if e.type == 'YANDEX.FIO'), None)
            if entity:
                name = entity.value
                last_name = name.last_name
                first_name = name.first_name
                middle_name = name.patronymic_name
                print(f"user fio by entity: {last_name} {first_name} {middle_name}")

            # if last_name is None or first_name is None:
            #     user_text = message.original_text.lower()
            #     fio_parts = user_text.strip().split()
            #     last_name = fio_parts[0] if len(fio_parts) > 0 else ''
            #     first_name = fio_parts[1] if len(fio_parts) > 1 else ''
            #     middle_name = ' '.join(fio_parts[2:]) if len(fio_parts) > 2 else ''
            #     print(f"user fio by entity to user_text: {last_name} {first_name} {middle_name}")
            
            if last_name is None or first_name is None or middle_name is None:
                return Response(
                    text="Пожалуйста, скажите полное имя",
                    tts="Пожалуйста, скажите полное имя"
                )

        # if last_name is None or first_name is None:
        #     return Response(
        #         text=f"Имя не распознано, пожалуйста, повторите",
        #         tts=f"Имя не распознано, пожалуйста, повторите"
        #     )

        await state.update_data(
            first_name=first_name.capitalize(),
            middle_name=middle_name.capitalize() if middle_name else None,
            last_name=last_name.capitalize(),
            gender=await detect_gender_by_name(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name
            )
        )

        await state.set_state(PatientInfo.getting_dob)
        fio = f"{last_name.capitalize()} {first_name.capitalize()}{' ' + middle_name.capitalize() if middle_name else ''}"
        return Response(
            text=f"Имя пациента: {fio}.\nСкажите вашу дату рождения в формате ДД.ММ.ГГГГ.",
            tts=f"Имя пациента: - {fio}.\n - Скажите вашу дату рождения в формате  - день - месяц - год."
        )

    async def handle_given_dob(self, message: Message, state: FSMContext) -> Response:
        user_id = message.session.user_id
        patient_data = await state.get_data()
        entity = message.nlu.entities
        birth_date = await get_birth_date_from_entities(entity)
        if not birth_date:
            return Response(
                text="Не удалось распознать дату рождения. Пожалуйста, повторите в формате ДД.ММ.ГГГГ.",
                tts="Не удалось распознать дату рождения.- Пожалуйста, - повторите в формате - день - месяц - год."
            )

        today = date.today()
        if birth_date > today:
            return Response(
                text="Дата рождения не может быть в будущем. Пожалуйста, введите корректную дату.",
                tts="Дата рождения не может быть в будущем.- Пожалуйста, - введите корректную дату."
            )
        age = today.year - birth_date.year

        if age < 12:
            return Response(
                text="Извините, сервис доступен только для лиц старше 12 лет.",
                tts="Извините, - сервис доступен только для лиц старше 12 лет."
            )

        if age > 120:
            return Response(
                text="Пожалуйста, проверьте правильность введенной даты рождения. Указанный возраст превышает 120 лет.",
                tts="Пожалуйста, - проверьте правильность введенной даты рождения. - Указанный возраст превышает 120 лет."
            )
        birth_date = birth_date.isoformat()
        await state.update_data(birth_date=birth_date)

        session_id = str(uuid.uuid4())
        patient_data['fer_session_id'] = session_id
        patient_data['birth_date'] = birth_date
        print(f"patient_data: {patient_data}")
        patient_id = patient_service.find_patient_by_fio(patient_data)

        if patient_id:
            await state.set_state(PatientInfo.confirmation)
            await state.update_data(
                next_step='PatientInfo.ask_post',
                previus_step='ask_appointment_you',
                fer_session_id=session_id
            )
            redis_service.hset(f"user:{user_id}:session", "patient_id", patient_id, 900)
            result = process_get_mo.delay(user_id, patient_data, 109)
            result.forget()
            return Response(
                text=f"Вы готовы выбрать медицинскую организацию?",
                tts=f"Вы готовы выбрать медицинскую организацию?"
            )

        await state.set_state(PatientInfo.getting_phone)

        birth_date = format_date_russian(birth_date, input_format='%Y-%m-%d',with_year=True)
        return Response(
            text=f"Дата рождения: {birth_date}.\nСкажите номер телефона",
            tts=f"Дата рождения: - {birth_date}.\n - Скажите номер телефона"
        )

    async def handle_given_phone(self, message: Message, state: FSMContext) -> Response:
        user_id = message.session.user_id
        patient_data = await state.get_data()

        if message.nlu.tokens:
            phone_raw = ''.join(message.nlu.tokens)
        else:
            return Response(
                text="Не удалось распознать номер телефона. Пожалуйста, повторите.",
                tts="Не удалось распознать номер телефона.- Пожалуйста, - повторите."
            )

        try:
            phone = PhoneNumberValidator(phone=phone_raw).phone
            print(f"Валидный номер")
        except ValueError as e:
            return Response(
                text="Не удалось распознать номер телефона. Пожалуйста, повторите.",
                tts="Не удалось распознать номер телефона.- Пожалуйста, - повторите."
            )

        await state.update_data(phone=phone)
        session_id = str(uuid.uuid4())
        patient_data['fer_session_id'] = session_id
        patient_data['phone'] = phone
        print(f"handle_given_phone: try find_patient_by_phone")
        patient_id = patient_service.find_patient_by_phone(patient_data)
        print(f"handle_given_phone: {patient_id}")
        if patient_id:
            await state.set_state(PatientInfo.confirmation)
            await state.update_data(
                next_step='PatientInfo.ask_post',
                previus_step='ask_appointment_you',
                fer_session_id=session_id
            )
            redis_service.hset(f"user:{user_id}:session", "patient_id", patient_id, 900)
            result = process_get_mo.delay(user_id, patient_data, 109)
            result.forget()
            return Response(
                text=f"Номер телефона: {phone}. Все верно?",
                tts=f"Номер телефона: - {phone}. - Все верно?"
            )

        await state.set_state(PatientInfo.getting_snils)
        return Response(
            text=f"Номер телефона: {phone}. Введите СНИЛС",
            tts=f"Номер телефона: - {phone}. - Введите СНИЛС"
        )

    async def handle_given_snils(self, message: Message, state: FSMContext) -> Response:
        user_id = message.session.user_id
        patient_data = await state.get_data()
        snils_raw = message.command.lower()

        try:
            snils = SnilsNumberValidator(snils=snils_raw).snils
            print(f"Валидный номер snils")
        except ValidationError as e:
            if e.errors()[0]['msg'] == "Value error, СНИЛС должен содержать 11 цифр":
                return Response(
                    text="СНИЛС должен содержать 11 цифр",
                    tts="СНИЛС должен содержать 11 цифр"
                )

            if e.errors()[0]['msg'] == "Value error, Неверная контрольная сумма СНИЛС":
                return Response(
                    text="Неверная контрольная сумма СНИЛС",
                    tts="Неверная контрольная сумма СНИЛС"
                )

            return Response(
                text="СНИЛС не распознан",
                tts=e.errors()[0]['msg']
            )

        await state.update_data(snils=snils)
        session_id = str(uuid.uuid4())
        patient_data['fer_session_id'] = session_id
        patient_data['snils'] = snils
        formatted_snils = f"{snils[:3]}-{snils[3:6]}-{snils[6:9]} {snils[9:]}"
        patient_id = patient_service.find_patient_by_snils(patient_data)
        if patient_id:
            await state.set_state(PatientInfo.confirmation)
            await state.update_data(
                next_step='PatientInfo.ask_post',
                previus_step='ask_appointment_you',
                fer_session_id=session_id
            )
            redis_service.hset(f"user:{user_id}:session", "patient_id", patient_id, 900)
            result = process_get_mo.delay(user_id, patient_data, 109)
            result.forget()
            return Response(
                text=f"СНИЛС: {formatted_snils}. Все верно?",
                tts=f"СНИЛС: - {formatted_snils}. - Все верно?"
            )

        await state.set_state(PatientInfo.zero)
        return Response(
            text=f"СНИЛС: {formatted_snils}. Найти пациента не удалось, повторите позже",
            tts=f"СНИЛС: - {formatted_snils}. - Найти пациента не удалось, - повторите позже"
        )


# Регистрация обработчиков
def setup_patient_introduction_handlers(
        router: Router
):
    handlers = PatientIntroductionHandlers()

    router.message.register(handlers.new_session, F.session.new)

    router.message.register(
        handlers.new_session,
        PatientInfo.zero,
        F.command == "записаться на прием"
    )

    router.message.register(
        handlers.new_session,
        (F.command == "записаться на прием") |
        (F.command == "запиши на прием") |
        (F.command == "запиши к врачу")
    )

    router.message.register(
        handlers.new_session,
        PatientInfo.zero
    )

    router.message.register(
        handlers.handle_given_name,
        PatientInfo.getting_name
    )

    router.message.register(
        handlers.handle_given_dob,
        PatientInfo.getting_dob,
        F.nlu.entities
    )

    router.message.register(
        handlers.handle_given_phone,
        PatientInfo.getting_phone
    )

    router.message.register(
        handlers.handle_given_snils,
        PatientInfo.getting_snils
    )
