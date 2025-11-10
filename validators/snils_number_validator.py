from pydantic import BaseModel, field_validator
import re
from typing import Optional


class SnilsNumberValidator(BaseModel):
    snils: Optional[str] = None

    @field_validator('snils')
    @classmethod
    def validate_snils(cls, v):
        if v is None or v == "":
            return None

        # Очищаем от всех нецифровых символов
        digits_only = re.sub(r'\D', '', v)
        print(digits_only)
        # Проверяем длину

        if len(digits_only) == 0:
            raise ValueError('СНИЛС должен содержать цифры')
        
        if len(digits_only) != 11:
            raise ValueError('СНИЛС должен содержать 11 цифр')

        # Проверяем контрольную сумму
        if not cls._check_snils_checksum(digits_only):
            raise ValueError('Неверная контрольная сумма СНИЛС')

        # Форматируем в стандартный вид: XXX-XXX-XXX YY
        # formatted_snils = f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:9]} {digits_only[9:]}"

        return digits_only

    @staticmethod
    def _check_snils_checksum(snils_digits: str) -> bool:
        """
        Проверка контрольной суммы СНИЛС.
        Алгоритм:
        1. Умножаем каждую цифру на позицию (с 9 до 1)
        2. Суммируем результаты
        3. Сравниваем контрольное число (последние 2 цифры) с вычисленной суммой
        """
        if len(snils_digits) != 11:
            return False

        # Преобразуем в список цифр
        digits = [int(d) for d in snils_digits]

        # Вычисляем контрольную сумму
        total = 0
        for i in range(9):
            total += digits[i] * (9 - i)

        # Определяем контрольное число
        checksum = digits[9] * 10 + digits[10]

        # Сравниваем
        if total < 100:
            return total == checksum
        elif total == 100 or total == 101:
            return checksum == 0
        else:
            remainder = total % 101
            if remainder == 100:
                return checksum == 0
            else:
                return remainder == checksum