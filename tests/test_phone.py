from validators.phone_number_validator import PhoneNumberValidator
from pydantic import ValidationError

try:
    raw_phone = "+7 (926) 123-45-67"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")
    
try:
    raw_phone = "+7 926 123-45-67"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")
    
    
try:
    raw_phone = "+7 926 123 45 67"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")
    
try:
    raw_phone = "+79261234567"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")
    
try:
    raw_phone = "79261234567"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")
    
try:
    raw_phone = "89261234567"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")
    
try:
    raw_phone = "8 926 1234567"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")    
    
try:
    raw_phone = "8 926 123 45 67"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")  
      
try:
    raw_phone = "8(926)1234567"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")
      
try:
    raw_phone = "8(926)123 45 67"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")   
       
try:
    raw_phone = "8 (926)123 45 67"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")  
             
try:
    raw_phone = "999 123 45 67"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(f"{raw_phone} - ошибка: {e}")      
     
try:
    raw_phone = "+7(919)9340710"
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(e.errors()[0]['msg'])     
    
try:
    raw_phone = None
    phone = PhoneNumberValidator(phone=raw_phone)
    print(f"{raw_phone} - валидный номер: {phone.phone}")
except ValueError as e:
    print(e.errors()[0]['msg'])