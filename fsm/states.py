from aliceio.fsm.state import State, StatesGroup


class PatientInfo(StatesGroup):
    zero = State()
    getting_name = State()
    getting_dob = State()
    getting_phone = State()
    getting_snils = State()

    confirmation = State()
    ask_post = State()
    getting_post = State()
    show_mo = State()
    getting_mo = State()
    getting_medic = State()

    getting_expected_date = State()
    getting_expected_time = State()
    getting_date = State()
    getting_time = State()

    appointment = State()
    awaiting_appointment_status = State()