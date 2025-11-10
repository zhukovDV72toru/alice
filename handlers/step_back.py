from aliceio import F, Router
from aliceio.fsm.context import FSMContext
from aliceio.types import Message, Response
from fsm.states import PatientInfo
from aliceio.fsm.state import State, StatesGroup
from aliceio.filters import StateFilter
from handlers.patient_introduction import PatientIntroductionHandlers
from handlers.doctor_selection import DoctorSelectionHandler

router = Router()


class StepBackHandlers:
    async def step_back(self, message: Message, state: FSMContext) -> Response:
        current_state = await state.get_state()
        print(f"STEP BACK {current_state}")
        patient_introduction_handler = PatientIntroductionHandlers()

        if current_state == PatientInfo.getting_dob:
            await state.set_state(PatientInfo.zero)
            return await patient_introduction_handler.new_session(message, state)

        if current_state == PatientInfo.getting_phone:
            await state.set_state(PatientInfo.zero)
            return await patient_introduction_handler.new_session(message, state)

        if current_state == PatientInfo.getting_snils:
            await state.set_state(PatientInfo.zero)
            return await patient_introduction_handler.new_session(message, state)

        if current_state == PatientInfo.getting_post:
            await state.set_state(PatientInfo.zero)
            return await patient_introduction_handler.new_session(message, state)

        if current_state == PatientInfo.getting_mo:
            await state.set_state(PatientInfo.ask_post)
            doctor_selection_handler = DoctorSelectionHandler()
            return await doctor_selection_handler.handle_ask_post(message, state)

        if current_state == PatientInfo.getting_medic:
            await state.set_state(PatientInfo.show_mo)
            doctor_selection_handler = DoctorSelectionHandler()
            return await doctor_selection_handler.handle_show_mo(message, state)

        if current_state == PatientInfo.getting_expected_date:
            await state.set_state(PatientInfo.show_mo)
            doctor_selection_handler = DoctorSelectionHandler()
            return await doctor_selection_handler.handle_show_mo(message, state)

        if current_state == PatientInfo.getting_expected_time:
            await state.set_state(PatientInfo.show_mo)
            doctor_selection_handler = DoctorSelectionHandler()
            return await doctor_selection_handler.handle_show_mo(message, state)

        if current_state == PatientInfo.getting_date:
            await state.set_state(PatientInfo.show_mo)
            doctor_selection_handler = DoctorSelectionHandler()
            return await doctor_selection_handler.handle_show_mo(message, state)

        if current_state == PatientInfo.getting_time:
            await state.set_state(PatientInfo.show_mo)
            doctor_selection_handler = DoctorSelectionHandler()
            return await doctor_selection_handler.handle_show_mo(message, state)


        # TODO сделать шаг назад для выбора времени, даты

        return await patient_introduction_handler.new_session(message, state)


def setup_step_back_handlers(
        router: Router
):
    handlers = StepBackHandlers()

    step_help_commands = (
        (F.command == "назад") |
        (F.command == "шаг надад") |
        (F.command == "вернуться") |
        (F.command == "вернуться назад")
    )

    router.message.register(handlers.step_back, StateFilter(PatientInfo), step_help_commands)
