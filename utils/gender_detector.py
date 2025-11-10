from pytrovich.detector import PetrovichGenderDetector
from pytrovich.enums import Gender as _PGender

_GENDER_DETECTOR = PetrovichGenderDetector()

async def detect_gender_by_name(first_name: str | None = None,
                          last_name: str | None = None,
                          middle_name: str | None = None) -> str | None:
    
    """Определяет пол ("M" или "F") по имени/фамилии/отчеству с помощью pytrovich.
    Любой параметр можно опустить (None или ""), при ошибке возвращает None.
    """
    
    kwargs = {}
    if first_name:
        kwargs["firstname"] = first_name
    if last_name:
        kwargs["lastname"] = last_name
    if middle_name:
        kwargs["middlename"] = middle_name

    if not kwargs:
        return None

    try:
        g = _GENDER_DETECTOR.detect(**kwargs)
    except Exception:
        return None

    if g == _PGender.MALE:
        return "M"
    if g == _PGender.FEMALE:
        return "F"
    return None