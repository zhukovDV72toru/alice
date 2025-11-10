from celery_app.app import celery_app
from typing import Dict, Any
from services.patient_service import patient_service
from services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_find_patient(
    self,
    user_id: str,
    patient_data: Dict[str, Any]
) -> bool:
    """
    Операция поиска пациента
    """
    try:
        patient_id = patient_service.find_patient(patient_data)
        if patient_id:
            # TODO сохранить в редис, ограничение по времени 900 сек
            pass
        return True
    except Exception as exc:
        # Повторные попытки при ошибках
        raise self.retry(exc=exc)
    
    
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_get_mo(
    self,
    user_id: str,
    patient_data: Dict[str, Any],
    post_id: int
) -> bool:
    """
    Длительная операция поиска мед организации
    """
    try:
        medic_orgs = patient_service.get_mo(patient_data, post_id)
        print(medic_orgs)
        if len(medic_orgs) > 0:
            redis_service.hset(f"user:{user_id}:session", 'medic_orgs', medic_orgs, 900)
            pass
        return True
    except Exception as exc:
        # Повторные попытки при ошибках
        raise self.retry(exc=exc)
    
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_create_appointment(
    self,
    patient_data: Dict[str, Any],
    slot_id: str
) -> Dict[str, Any]:
    """Длительная операция создания записи на прием."""

    try:
        result, book_id = patient_service.appointment(patient_data, slot_id)
        return {
            'result': result,
            'book_id': book_id,
        }
    except Exception as exc:
        # Повторные попытки при ошибках
        raise self.retry(exc=exc)