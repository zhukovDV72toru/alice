from typing import Dict, Any
from clients.fer_client import fer_client
from lxml import etree
from typing import List, TypedDict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from utils.slots_parser import prepare_slots
import logging
import time
import os
import sys


class MedicalOrganization(TypedDict):
    id: str
    oid: str
    name: str
    address: str
    phone: Optional[str] 


def normalize_name(name):
    return name.lower().strip() if name else ""


class PatientService:
    def __init__(self):
        self.namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://www.rt-eu.ru/med/er/v2_0'
        }

        in_container = os.environ.get('CONTAINERIZED') or os.path.exists('/.dockerenv')

        self.logger = logging.getLogger('patient_service')
        if not self.logger.handlers:
            if in_container:
                # В контейнере пишем в stdout
                print("LOGS IN in_container")
                file_handler = logging.StreamHandler(sys.stdout)
            else:
                # Локально пишем в файл
                print("LOGS IN FILE")
                file_handler = logging.StreamHandler(sys.stdout)
                #file_handler = logging.FileHandler('patient_service.log', encoding='utf-8')


            # Создаем форматтер
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            # Устанавливаем уровень логирования
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

            # Опционально: запретить передачу сообщений родительским логгерам
            self.logger.propagate = False

    def find_patient_by_phone(self, patient_data: Dict[str, Any]) -> Optional[str]:
        session_id = patient_data.get('fer_session_id')
        phone = patient_data.get('phone')

        start_time = time.time()
        try:
            response = fer_client.send('IdentifyPatientByPhoneRequest', {'session_id': session_id, 'phone': phone})

            execution_time = time.time() - start_time
            request_data = {'session_id': session_id, 'phone': phone}

            print(f"find_patient_by_phone executed in {execution_time:.3f} seconds")
            print(f"SOAP Request: {request_data}")
            print(f"SOAP Response: {response}")

            root = etree.fromstring(response)
            patient_id = root.xpath(
                '//ns:IdentifyPatientByPhoneResponse/ns:Patient_Data/ns:Patient_Id/text()',
                namespaces=self.namespaces
            )

            if patient_id and len(patient_id) > 0:
                patient_id = patient_id[0]
                print(f"Patient_Id: {patient_id}")
                xml_last_name = root.xpath(
                    '//ns:IdentifyPatientByPhoneResponse/ns:Patient_Data/ns:Last_Name/text()',
                    namespaces=self.namespaces
                )
                
                xml_middle_name = root.xpath(
                    '//ns:IdentifyPatientByPhoneResponse/ns:Patient_Data/ns:Middle_Name/text()',
                    namespaces=self.namespaces
                )    
                        
                xml_first_name = root.xpath(
                    '//ns:IdentifyPatientByPhoneResponse/ns:Patient_Data/ns:First_Name/text()',
                    namespaces=self.namespaces
                )    
                
                first_name = patient_data.get('first_name')
                last_name = patient_data.get('last_name')
                middle_name = patient_data.get('middle_name')
                    
                xml_last_name = xml_last_name[0] if xml_last_name else None
                xml_middle_name = xml_middle_name[0] if xml_middle_name else None
                xml_first_name = xml_first_name[0] if xml_first_name else None
                
                if (normalize_name(xml_last_name) != normalize_name(last_name) or 
                    normalize_name(xml_first_name) != normalize_name(first_name) or 
                    normalize_name(xml_middle_name) != normalize_name(middle_name)):
                    
                    print("Данные пациента не совпадают")
                    print(f"{normalize_name(xml_last_name)} - {normalize_name(last_name)}")
                    print(f"{normalize_name(xml_first_name)} - {normalize_name(first_name)}")
                    print(f"{normalize_name(xml_middle_name)} - {normalize_name(middle_name)}")
                    
                    
                    if normalize_name(xml_last_name) == normalize_name(last_name):
                        print('last_name ok')
                    if normalize_name(xml_first_name) == normalize_name(first_name):
                        print('first_name ok')
                    if normalize_name(xml_middle_name) == normalize_name(middle_name):
                        print('middle_name ok')   
                    else: 
                        xml_middle_name_bytes = xml_middle_name.encode(encoding='UTF-8', errors='strict')
                        print(xml_middle_name_bytes)  
                        middle_name_bytes = middle_name.encode(encoding='UTF-8', errors='strict')
                        print(middle_name_bytes)                
                    
                    return None
                
                return patient_id
            
            return None
        except Exception as e:
            print(f"Ошибка FER: {e}")
            return None
        
    def find_patient_by_fio(
        self, 
        patient_data: Dict[str, Any]
    ) -> Optional[str]:
        session_id = patient_data.get('fer_session_id')
        first_name = patient_data.get('first_name')
        last_name = patient_data.get('last_name')
        middle_name = patient_data.get('middle_name')
        birth_date = patient_data.get('birth_date')
        gender = patient_data.get('gender')

        start_time = time.time()
        try:
            response = fer_client.send('GetPatientInfoRequest', {
                'session_id': session_id, 
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'birth_date': birth_date,
                'gender': gender,
            })

            execution_time = time.time() - start_time
            print(f"find_patient_by_fio executed in {execution_time:.3f} seconds")
            request_data = {
                'session_id': session_id,
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'birth_date': birth_date,
                'gender': gender,
            }
            print(f"SOAP Request: {request_data}")
            print(f"SOAP Response: {response}")

            root = etree.fromstring(response)
            patient_id = root.xpath(
                '//ns:GetPatientInfoResponse/ns:Patient_Id/text()',
                namespaces=self.namespaces
            )
            
            if patient_id and len(patient_id) > 0:
                return patient_id[0]
            
            return None
        except Exception as e:
            print(f"Ошибка FER: {e}")
            return None

    def find_patient_by_snils(
        self,
        patient_data: Dict[str, Any]
    ) -> Optional[str]:
        session_id = patient_data.get('fer_session_id')
        first_name = patient_data.get('first_name')
        last_name = patient_data.get('last_name')
        middle_name = patient_data.get('middle_name')
        birth_date = patient_data.get('birth_date')
        gender = patient_data.get('gender')
        snils = patient_data.get('snils')

        start_time = time.time()
        try:
            response = fer_client.send('GetPatientInfoBySnilsRequest', {
                'session_id': session_id,
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'birth_date': birth_date,
                'gender': gender,
                'snils': snils,
            })

            execution_time = time.time() - start_time
            print(f"find_patient_by_snils executed in {execution_time:.3f} seconds")
            request_data = {
                'session_id': session_id,
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'birth_date': birth_date,
                'gender': gender,
                'snils': snils,
            }
            print(f"SOAP Request: {request_data}")
            print(f"SOAP Response: {response}")

            root = etree.fromstring(response)
            patient_id = root.xpath(
                '//ns:GetPatientInfoResponse/ns:Patient_Id/text()',
                namespaces=self.namespaces
            )

            if patient_id and len(patient_id) > 0:
                return patient_id[0]

            return None
        except Exception as e:
            print(f"Ошибка FER: {e}")
            return None
        
    def find_patient(
        self, 
        patient_data: Dict[str, Any]
    ) -> Optional[str]:
        try:
            if 'snils' in patient_data:
                patient_id = self.find_patient_by_snils(patient_data)
            else:
                patient_id = self.find_patient_by_fio(patient_data)

            if patient_id is None and 'phone' in patient_data:
                patient_id = self.find_patient_by_phone(patient_data)

            return patient_id
        except Exception as e:
            print(f"Ошибка FER: {e}")
            return None

    def get_mo(
        self, 
        patient_data: Dict[str, Any],
        post_id: int
    ) -> List[MedicalOrganization]:
        session_id = patient_data.get('fer_session_id')

        start_time = time.time()
        try:
            response = fer_client.send('GetMOInfoExtendedRequest', {
                'session_id': session_id, 
                'post_id': post_id,
            })

            execution_time = time.time() - start_time
            print(f"get_mo executed in {execution_time:.3f} seconds")
            print(f"SOAP Response: {response}")

            root = etree.fromstring(response)
            mo_elements = root.xpath(
                '//ns:GetMOInfoExtendedResponse/ns:MO_List/ns:MO',
                namespaces=self.namespaces
            )
            
            organizations: List[MedicalOrganization] = []
    
            for mo_element in mo_elements:
                mo_id = mo_element.xpath('ns:MO_Id/text()', namespaces=self.namespaces)
                mo_oid = mo_element.xpath('ns:MO_OID/text()', namespaces=self.namespaces)
                mo_name = mo_element.xpath('ns:MO_Name/text()', namespaces=self.namespaces)
                mo_address = mo_element.xpath('ns:MO_Address/text()', namespaces=self.namespaces)
                mo_phone = mo_element.xpath('ns:MO_Phone/text()', namespaces=self.namespaces)
                
                # Создаем словарь с данными организации
                organization: MedicalOrganization = {
                    'id': mo_id[0] if mo_id else '',
                    'oid': mo_oid[0] if mo_oid else '',
                    'name': mo_name[0] if mo_name else '',
                    'address': mo_address[0] if mo_address else '',
                    'phone': mo_phone[0] if mo_phone else None
                }
                
                organizations.append(organization)
            
            return organizations
        except Exception as e:
            print(f"Ошибка FER: {e}")
            return []

    def get_medics(
            self,
            patient_data: Dict[str, Any],
            oid: str,
            post_id: int
    ) -> Dict:
        session_id = patient_data.get('fer_session_id')
        current_date = datetime.now().date()
        end_date = current_date + timedelta(days=14)
        date_start = current_date.strftime('%Y-%m-%d')
        date_end = end_date.strftime('%Y-%m-%d')

        start_time = time.time()
        try:
            response = fer_client.send('GetMOResourceInfoRequest', {
                'session_id': session_id,
                'post_id': post_id,
                'oid': oid,
                'date_start': date_start,
                'date_end': date_end,
            })

            execution_time = time.time() - start_time
            print(f"get_medics executed in {execution_time:.3f} seconds")
            print(f"SOAP Response: {response}")

            root = etree.fromstring(response)
            resource_elements = root.xpath(
                '//ns:GetMOResourceInfoResponse/ns:MO_Resource_List/ns:MO_Available/ns:Resource_Available/ns:Resource',
                namespaces=self.namespaces
            )

            medics = defaultdict(dict)
            for resource in resource_elements:
                specialist_last_name = resource.xpath('ns:Specialist/ns:Last_Name/text()', namespaces=self.namespaces)
                specialist_first_name = resource.xpath('ns:Specialist/ns:First_Name/text()', namespaces=self.namespaces)
                specialist_middle_name = resource.xpath('ns:Specialist/ns:Middle_Name/text()', namespaces=self.namespaces)
                specialist_snils = resource.xpath('ns:Specialist/ns:SNILS/text()', namespaces=self.namespaces)
                no_schedule_reason = resource.xpath('ns:No_Schedule_Reason/ns:No_Schedule_Reason_Сode/text()', namespaces=self.namespaces)
                available_dates = resource.xpath('ns:Available_Dates/ns:Available_Date/text()', namespaces=self.namespaces)

                specialist_last_name = specialist_last_name[0] if specialist_last_name else ''
                specialist_first_name = specialist_first_name[0] if specialist_first_name else ''
                specialist_middle_name = specialist_middle_name[0] if specialist_middle_name else ''
                specialist_snils = specialist_snils[0] if specialist_snils else None

                specialist = f"{specialist_last_name} {specialist_first_name} {specialist_middle_name}"

                print(f"\n\n{specialist} available_dates: {available_dates}\n\n")
                print(f"\n\n{specialist} no_schedule_reason: {no_schedule_reason}\n\n")
                if len(no_schedule_reason) > 0:
                    continue

                if len(available_dates) == 0:
                    continue

                medics[specialist] = specialist_snils

            return medics
        except Exception as e:
            print(f"Ошибка FER: {e}")
            return {}

    def get_slots(
            self,
            patient_data: Dict[str, Any],
            specialist_snils: str,
            post_id: int,
            expected_date: Optional[datetime] = None,
            timedelta_days: Optional[int] = 14
    ) -> Dict:

        session_id = patient_data.get('fer_session_id')

        if expected_date is None:
            expected_date = datetime.now()

        current_date = datetime.now().date()
        time_start = "06:00:00"
        time_end = "23:59:59"
        date_start = current_date

        if expected_date.date() == current_date:
            time_start = current_date + timedelta(hours=1)
            time_start = time_start.strftime('%H:%M:%S')
        elif expected_date.date() > current_date:
            date_start = expected_date.date()

        date_end = date_start + timedelta(days=timedelta_days)

        start_time = time.time()
        try:
            response = fer_client.send('GetScheduleInfoRequest', {
                'session_id': session_id,
                'post_id': post_id,
                'specialist_snils': specialist_snils,
                'date_start': date_start.strftime('%Y-%m-%d'),
                'date_end': date_end.strftime('%Y-%m-%d'),
                'time_start': time_start,
                'time_end': time_end,
            })

            execution_time = time.time() - start_time
            print(f"get_slots executed in {execution_time:.3f} seconds")
            print(f"SOAP Response: {response}")

            root = etree.fromstring(response)
            slots_elements = root.xpath(
                '//ns:GetScheduleInfoResponse/ns:Schedule/ns:Slots',
                namespaces=self.namespaces
            )
            slots = prepare_slots(slots_elements, self.namespaces)

            if len(slots) == 0 and timedelta_days < 14 * 2:
                print("Запрашиваем повторно")
                return self.get_slots(
                    patient_data,
                    specialist_snils,
                    post_id,
                    expected_date,
                    timedelta_days + 7
            )
            return slots
        except Exception as e:
            print(f"Ошибка FER: {e}")
            return {}

    def appointment(
                self,
                patient_data: Dict[str, Any],
                slot_id: str
        ):
        session_id = patient_data.get('fer_session_id')
        start_time = time.time()
        try:
            response = fer_client.send('CreateAppointmentRequest', {
                'session_id': session_id,
                'slot_id': slot_id
            })

            execution_time = time.time() - start_time
            print(f"appointment executed in {execution_time:.3f} seconds")
            print(f"SOAP Response: {response}")

            root = etree.fromstring(response)
            status = root.xpath(
                '//ns:CreateAppointmentResponse/ns:Status/ns:Status_Code/text()',
                namespaces=self.namespaces
            )

            book_id = root.xpath(
                '//ns:CreateAppointmentResponse/ns:Book_Id_Mis/text()',
                namespaces=self.namespaces
            )

            status = status[0] if status else None
            book_id = book_id[0] if book_id else None


            return status, book_id
        except Exception as e:
            print(f"Ошибка FER: {e}")
            return None, None


patient_service = PatientService()