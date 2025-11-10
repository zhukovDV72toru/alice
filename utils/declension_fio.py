from pytrovich.enums import NamePart, Gender, Case
from pytrovich.maker import PetrovichDeclinationMaker
from pytrovich.detector import PetrovichGenderDetector


def declension(fio, case):
    """
    Преобразует ФИО из именительного падежа в заданный падеж
    """
    maker = PetrovichDeclinationMaker()
    parts = fio.split()

    if len(parts) == 0:
        return fio

    last = parts[0] if parts[0] else ''
    first = parts[1] if parts[0] else ''
    middle = parts[2] if parts[0] else ''

    detector = PetrovichGenderDetector()
    gender = detector.detect(lastname=last, firstname=first, middlename=middle)

    last = maker.make(NamePart.LASTNAME, gender, Case.DATIVE, last)
    first = maker.make(NamePart.FIRSTNAME, gender, Case.DATIVE, first)
    middle = maker.make(NamePart.MIDDLENAME, gender, Case.DATIVE, middle)

    return f"{last} {first} {middle}"
