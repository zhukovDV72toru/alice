from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

import requests


ER_NS = "http://www.rt-eu.ru/med/er/v2_0"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
WSU_NS = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"

NSMAP = {
    "soap": SOAP_NS,
    "er": ER_NS,
    "wsu": WSU_NS,
}


class PatientServiceError(Exception):
    """Базовое исключение для ошибок сервиса пациентов."""

def _build_envelope_xml(
    session_id: str,
    first_name: str,
    last_name: str,
    middle_name: Optional[str],
    birth_date_iso: str,
    sex: str,
    pass_referral: bool,
) -> str:
    """
    Формирует строку SOAP XML запроса GetPatientInfoRequest.
    """
    middle_name_xml = (
        f"\n                <Middle_Name>{xml_escape(middle_name)}</Middle_Name>"
        if middle_name
        else ""
    )

    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}">
  <soapenv:Header/>
  <soapenv:Body xmlns:wsu="{WSU_NS}" wsu:Id="id-{xml_escape(session_id)}">
    <GetPatientInfoRequest xmlns="{ER_NS}">
      <Session_ID>{xml_escape(session_id)}</Session_ID>
      <Patient_Data>
        <First_Name>{xml_escape(first_name)}</First_Name>
        <Last_Name>{xml_escape(last_name)}</Last_Name>{middle_name_xml}
        <Birth_Date>{xml_escape(birth_date_iso)}</Birth_Date>
        <Sex>{xml_escape(sex)}</Sex>
      </Patient_Data>
      <Pass_referral>{"1" if pass_referral else "0"}</Pass_referral>
    </GetPatientInfoRequest>
  </soapenv:Body>
</soapenv:Envelope>"""
    return envelope


def _parse_response(xml_text: str) -> Tuple[Optional[str], List[str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise PatientServiceError(f"Некорректный XML ответа: {e}") from e

    # Попытка найти через namespace
    patient_id_elem = root.find(".//er:GetPatientInfoResponse/er:Patient_Id", NSMAP)
    if patient_id_elem is None:
        # fallback: поиск по локальному имени, если namespace отличается
        for el in root.iter():
            if el.tag.endswith("Patient_Id"):
                patient_id_elem = el
                break

    patient_id = patient_id_elem.text.strip() if (patient_id_elem is not None and patient_id_elem.text) else None

    codes: List[str] = []
    # Собираем все No_Attachment_Code
    for el in root.findall(".//er:GetPatientInfoResponse/er:No_Attachment_Code", NSMAP):
        if el.text:
            codes.append(el.text.strip())
    if not codes:
        # fallback по локальному имени
        for el in root.iter():
            if el.tag.endswith("No_Attachment_Code") and el.text:
                codes.append(el.text.strip())

    return patient_id, codes


def get_patient_info(
    endpoint_url: str,
    *,
    first_name: str,
    last_name: str,
    middle_name: Optional[str],
    birth_date: str,
    sex: str,
    session_id: Optional[str] = None,
    pass_referral: bool = False,
    soap_action: Optional[str] = None,
    timeout: float = 15.0,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Отправляет SOAP-запрос GetPatientInfoRequest и возвращает результат.

    Параметры:
        endpoint_url: URL SOAP сервиса.
        first_name, last_name, middle_name: ФИО пациента (отчество можно None).
        birth_date: Дата рождения — 'ДД.ММ.ГГГГ' или 'YYYY-MM-DD'.
        sex: Пол — 'M'/'F' (поддерживаются эквиваленты: М/Ж, male/female).
        session_id: Необязательный Session_ID; если не указан — будет сгенерирован UUID v4.
        pass_referral: Значение тега <Pass_referral> (по умолчанию 0).
        soap_action: Заголовок SOAPAction (если требуется бекендом).
        timeout: Таймаут запроса в секундах.
        extra_headers: Доп. заголовки HTTP.

    Возвращает:
        dict:
          {
            "success": bool,                  # True, если найден Patient_Id
            "patient_id": Optional[str],
            "session_id": str,
            "no_attachment_codes": List[str], # все коды из ответа (если были)
            "status_code": int,
            "raw_response": str               # исходный XML ответа (для логов/отладки)
          }

    Исключения:
        ValueError — при некорректных входных данных.
        PatientServiceError — при проблемах парсинга или сетевых ошибках.
    """
    if not endpoint_url:
        raise ValueError("endpoint_url обязателен.")

    sid = session_id or str(uuid.uuid4())

    # Формируем XML
    envelope_xml = _build_envelope_xml(
        session_id=sid,
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        birth_date_iso=birth_date,
        sex=sex,
        pass_referral=pass_referral,
    )

    # Заголовки
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
    }
    if soap_action:
        headers["SOAPAction"] = soap_action
    if extra_headers:
        headers.update(extra_headers)

    # HTTP-запрос
    try:
        resp = requests.post(
            endpoint_url,
            data=envelope_xml.encode("utf-8"),
            headers=headers,
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise PatientServiceError(f"Ошибка сети при обращении к сервису: {e}") from e

    # Парсим ответ
    patient_id = None
    codes: List[str] = []
    try:
        patient_id, codes = _parse_response(resp.text)
    except PatientServiceError:
        # пробрасываем дальше
        raise
    except Exception as e:
        raise PatientServiceError(f"Не удалось обработать ответ: {e}") from e

    return {
        # "success": bool(patient_id),
        "patient_id": patient_id,
        "session_id": sid
        # "no_attachment_codes": codes,
        # "status_code": resp.status_code,
        # "raw_response": resp.text
    }