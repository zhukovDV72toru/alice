from pydantic import BaseModel, field_validator
import re
from typing import Optional


class PhoneNumberValidator(BaseModel):
    phone: str
    
    @field_validator('phone')
    def validate_phone_number(cls, v):
        if v is None:
            return v
            
        # Удаляем все нецифровые символы, кроме плюса в начале
        cleaned_phone = re.sub(r'(?!^\+)\D', '', v)
        
        # Проверяем различные форматы номеров
        patterns = [
            r'^\+7\d{10}$',      # +79261234567
            r'^8\d{10}$',        # 89261234567
            r'^7\d{10}$',        # 79261234567 (без +)
            r'^9\d{9}$',        # 9261234567 (без +7, 7, 8)
        ]
        
        if not any(re.match(pattern, cleaned_phone) for pattern in patterns):
            raise ValueError('Неверный формат номера телефона. Ожидается российский номер в форматах: +79261234567, 89261234567 или 79261234567')
        
        # Нормализуем номер к формату +7XXXXXXXXXX
        if cleaned_phone.startswith('8'):
            normalized_phone = '+7' + cleaned_phone[1:]
        elif cleaned_phone.startswith('7') and not cleaned_phone.startswith('+7'):
            normalized_phone = '+7' + cleaned_phone[1:]
        elif cleaned_phone.startswith('9') and len(cleaned_phone) == 10:
            normalized_phone = '+7' + cleaned_phone
        else:
            normalized_phone = cleaned_phone
           
        formatted_phone = f"+7({normalized_phone[2:5]}){normalized_phone[5:]}"
        return formatted_phone
