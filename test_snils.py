from validators.snils_number_validator import SnilsNumberValidator
from pydantic import BaseModel, field_validator, ValidationError

test_cases = [
    "112-233-445 95",  # Стандартный формат
    "11223344595",     # Только цифры
    "112-233-445-95",  # С лишними дефисами
    "112 233 445 95",  # С пробелами
]
for test in test_cases:
    try:
        validator = SnilsNumberValidator(snils=test)
        print(f"✓ {test} -> {validator.snils}")
    except ValidationError as e:
        print(f"✗ {test} -> {e}")

invalid_cases = [
    "112-233-445 96",  # Неверная контрольная сумма
    "1234567890",  # Слишком короткий
    "123456789012",  # Слишком длинный
    "abc-def-ghi jk",  # Не цифры
]

print("\nНекорректные СНИЛС:")
for test in invalid_cases:
    try:
        validator = SnilsNumberValidator(snils=test)
        print(f"✓ {test} -> {validator.snils}")
    except ValidationError as e:
        print(f"✗ {test} -> {e.errors()[0]['msg']}")