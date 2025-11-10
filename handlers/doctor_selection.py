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
from utils.dates_utils import format_dates_russian
from services.profession_searcher import ProfessionSearcher
from services.org_searcher import OrgSearcher
from services.fio_searcher import FioSearcher


router = Router()

class DoctorSelectionHandler:
    """Обработчик выбора врача (организация → специальность → врач)"""

    async def handle_ask_post(self, message: Message, state: FSMContext) -> Response:
        await state.set_state(PatientInfo.getting_post)
        return Response(
            text="К какому врачу вас записать? Назовите специализацию",
            tts="К какому врачу вас записать? - Назовите специализацию"
        )

    async def show_available_post(self, message: Message, state: FSMContext) -> Response:
        searcher = ProfessionSearcher()
        professions = searcher._load_professions()
        professions = list(filter(lambda row: row['show_in_help'] == '1', professions))

        examples_text = " \n  ".join([" - " + item['name'] for item in professions])
        examples_tts = " \n  ".join([" - " + item['name'] for item in professions])

        text = f"Вот список некоторых специализаций:\n{examples_text}"
        tts = f"Вот список некоторых специализаций: - {examples_tts}"
        print(text)
        return Response(
            text=text,
            tts=tts
        )

    async def handle_given_post(self, message: Message, state: FSMContext) -> Response:
        user_id = message.session.user_id
        post_name = message.command
        searcher = ProfessionSearcher()
        result = searcher.search(post_name)

        if result is None:
            return Response(
                text="Специализация не найдена, попробуйте сказать 'Терапевт'",
                tts="Специализация не найдена, - попробуйте сказать - 'Терапевт'"
            )

        elif isinstance(result, dict):
            # Один результат
            post_id = result['id']
            redis_service.hset(f"user:{user_id}:session", "post_id", post_id, 2000)
            await state.set_state(PatientInfo.show_mo)
            await state.update_data(next_step='unknown')
            return await self.handle_show_mo(message, state)

        elif isinstance(result, list):
            # Несколько результатов
            options = []
            for item in result:
                if isinstance(item, dict):
                    if 'profession' in item:
                        # Элемент с оценкой
                        options.append(item['profession']['name'])
                    else:
                        # Прямой объект профессии
                        options.append(item['name'])

            options_text = "\n".join(options)
            options_text_ttl = "\n - ".join(options)
            return Response(
                text=f"Не удалось распознать, назовите один из вариантов:\n{options_text}",
                tts=f"Не удалось распознать, - назовите один из вариантов:\n - {options_text_ttl}"
            )


    async def handle_show_mo(self, message: Message, state: FSMContext) -> Response:
        user_id = message.session.user_id

        await state.set_state(PatientInfo.getting_mo)
        medic_orgs = redis_service.hget(f"user:{user_id}:session", "medic_orgs")
        post_id = redis_service.hget(f"user:{user_id}:session", "post_id")

        if post_id is None:
            await state.set_state(PatientInfo.getting_post)
            return Response(
                text=f"Не выбрана должность врача. Выберите должность",
                tts=f"Не выбрана должность врача. - Выберите должность"
            )

        if medic_orgs is None or post_id != 109:
            print(f"medic_orgs empty, or post_id wrong, load again. post_id: {post_id}")
            patient_data = await state.get_data()
            medic_orgs = patient_service.get_mo(patient_data, post_id)
            if len(medic_orgs) > 0:
                redis_service.hset(f"user:{user_id}:session", 'medic_orgs', medic_orgs, 900)

        if medic_orgs is None or len(medic_orgs) == 0:
            await state.set_state(PatientInfo.getting_post)
            return Response(
                text=f"Нет доступных организаций. Давайте подберем другого специалиста. К какому врачу вас записать?",
                tts=f"Нет доступных организаций, - Давайте подберем другого специалиста. - К какому врачу вас записать?"
            )

        organizations_list, organizations_list_ttl = prepareOrgsList(medic_orgs)

        text = f"Список доступных организаций:\n{organizations_list}\n\nВыберите медицинскую организацию, указав ее номер или ее адрес. Лучше назвать номер пункта в списке"
        tts = f"Выберите медицинскую организацию, указав ее номер или назвав адрес полностью: - \n{organizations_list_ttl}\n\n"
        return Response(
            text=text,
            tts=tts
        )

    async def handle_given_mo(self, message: Message, state: FSMContext) -> Response:
        user_id = message.session.user_id
        user_answer = message.original_text.lower()
        patient_data = await state.get_data()
        entities = message.nlu.entities
        medic_orgs = redis_service.hget(f"user:{user_id}:session", "medic_orgs")
        organizations_list, organizations_list_ttl = prepareOrgsList(medic_orgs)

        if organizations_list is None:
            await state.set_state(PatientInfo.zero)
            return Response(
                text=f"Нет доступных организаций, попробуйте позже",
                tts=f"Нет доступных организаций, - попробуйте позже"
            )

        if user_answer in [
            'список',
            'повтори',
            'повторить',
            'еще раз',
            'перечисли',
            'какая есть',
            'какая есть адреса',
            'какие есть организации',
            'покажи список',
            'а какие есть',
        ]:
            return Response(
                text=f"Выберите медицинскую организацию, указав номер пункта из списка или ее адрес:\n\n{organizations_list}",
                tts=f"Выберите медицинскую организацию, - указав номер пункта из списка или ее адрес:\n\n{organizations_list_ttl}"
            )

        choice = None
        mo = None
        if entities and len(entities) == 1 and entities[0].type == 'YANDEX.NUMBER':
            choice = entities[0].value
            try:
                if choice is None or not (0 <= choice - 1 < len(medic_orgs)):
                    raise KeyError
                mo = medic_orgs[choice - 1]
            except KeyError:
                print(f"handle_given_mo error choice by num")
                return Response(
                    text=f"Ответ не распознан\nВыберите медицинскую организацию, указав номер пункта из списка или ее адрес:\n\n{organizations_list}",
                    tts=f"Ответ не распознан\n - Выберите медицинскую организацию, - указав номер пункта из списка или ее адрес:\n\n{organizations_list_ttl}"
                )

        geo_entity = next(filter(lambda x: x.type == 'YANDEX.GEO', entities), None)
        if geo_entity:
            parts = [geo_entity.value.city, geo_entity.value.street, geo_entity.value.house_number]
            entity_input = ', '.join(part for part in parts if part is not None)
            searcher = OrgSearcher(medic_orgs)
            result = searcher.search(entity_input)
            if isinstance(result, dict):
                mo = result
            else:
                return Response(
                    text=f"Ответ не распознан\nВыберите медицинскую организацию, указав номер пункта из списка или ее адрес:\n\n{organizations_list}",
                    tts=f"Ответ не распознан\nВыберите медицинскую организацию, указав номер пункта из списка или ее адрес:\n\n{organizations_list_ttl}"
                )

        if mo is None:
            searcher = OrgSearcher(medic_orgs)
            result = searcher.search(user_answer)
            if isinstance(result, dict):
                mo = result
            else:
                return Response(
                    text=f"Ответ не распознан\nВыберите медицинскую организацию, указав номер пункта из списка или ее адрес:\n\n{organizations_list}",
                    tts=f"Ответ не распознан\n - Выберите медицинскую организацию, - указав номер пункта из списка или ее адрес:\n\n{organizations_list_ttl}"
                )

        post_id = redis_service.hget(f"user:{user_id}:session", "post_id")
        if post_id is None:
            await state.set_state(PatientInfo.getting_post)
            return Response(
                text=f"Не выбрана должность врача. Выберите должность",
                tts=f"Не выбрана должность врача. - Выберите должность"
            )

        redis_service.hset(f"user:{user_id}:session", "selected_org", mo, 900)
        oid = mo['oid']
        medics = patient_service.get_medics(patient_data, oid, post_id)

        if medics is None or len(medics) == 0:
            await state.set_state(PatientInfo.show_mo)
            return Response(
                text=f"Слотов в данной организации нет, выбрать другую организацию?",
                tts=f"Слотов в данной организации нет, - выбрать другую организацию?"
            )

        redis_service.hset(f"user:{user_id}:session", "available_specialists", medics, 900)

        # Вывести список врачей
        specialists = medics.keys()
        specialists = '\n'.join(specialists)
        await state.set_state(PatientInfo.getting_medic)
        return Response(
            text=f"Выберите врача:\n{specialists}",
            tts=f"Выберите врача:\n{specialists}"
        )

    async def handle_given_medic(self, message: Message, state: FSMContext) -> Response:
        user_id = message.session.user_id
        user_text = message.original_text.lower()
        entity = next((e for e in message.nlu.entities if e.type == 'YANDEX.FIO'), None)
        specialists = redis_service.hget(f"user:{user_id}:session", "available_specialists")

        if entity is None:
            if len(specialists) == 1 and user_text == "да":
                specialist_fio = next(iter(specialists))
                specialist_snils = specialists.get(specialist_fio)
                if specialist_snils is None:
                    return Response(
                        text=f"Врач не распознан. Повторите",
                        tts=f"Врач не распознан. - Повторите"
                    )

                redis_service.hset(f"user:{user_id}:session", 'selected_specialist',
                                   {'fio': specialist_fio, 'snils': specialist_snils}, 900)

                await state.set_state(PatientInfo.getting_expected_date)
                return Response(
                    text=f"На какую дату вас записать?",
                    tts=f"На какую дату вас записать?"
                )
            elif len(specialists) == 1 and user_text in ['нет', 'назад', 'отмена']:
                return await self.handle_show_mo(message, state)

            return Response(
                text=f"Врач не распознан. Повторите",
                tts=f"Врач не распознан. - Повторите"
            )

        name = entity.value
        last_name = name.last_name.capitalize() if name.last_name else ''
        first_name = name.first_name.capitalize() if name.first_name else ''
        middle_name = name.patronymic_name.capitalize() if name.patronymic_name else ''
        specialist_fio = f"{last_name} {first_name} {middle_name}"

        searcher = FioSearcher(list(specialists.keys()))
        result = searcher.search(specialist_fio)

        if result:
            specialist_fio = result
        else:
            return Response(
                text=f"Врач не распознан. Повторите",
                tts=f"Врач не распознан. - Повторите"
            )

        specialist_snils = specialists.get(specialist_fio)
        if specialist_snils is None:
            return Response(
                text=f"Врач не распознан. Повторите",
                tts=f"Врач не распознан. - Повторите"
            )

        redis_service.hset(f"user:{user_id}:session", 'selected_specialist', {'fio': specialist_fio, 'snils': specialist_snils}, 900)

        await state.set_state(PatientInfo.getting_expected_date)
        return Response(
            text=f"На какую дату вас записать?",
            tts=f"На какую дату вас записать?"
        )


def setup_doctor_selection_handlers(
        router: Router
):
    handlers = DoctorSelectionHandler()

    router.message.register(
        handlers.handle_ask_post,
        PatientInfo.ask_post
    )

    router.message.register(
        handlers.show_available_post,
        PatientInfo.getting_post,
        F.command == "список"
    )

    router.message.register(
        handlers.handle_given_post,
        PatientInfo.getting_post
    )

    router.message.register(
        handlers.handle_show_mo,
        PatientInfo.show_mo
    )

    router.message.register(
        handlers.handle_given_mo,
        PatientInfo.getting_mo
    )

    router.message.register(
        handlers.handle_given_medic,
        PatientInfo.getting_medic
    )