from __future__ import annotations

import os
import requests
import logging
from typing import Dict, Any
from config import config
import base64


logger = logging.getLogger(__name__)


class FERClientError(Exception):
    """Базовое исключение для ошибок FER клиента."""


class FERClient:
    """Клиент для работы с FER SOAP API."""
    
    def __init__(self):     
        """
        Инициализирует клиент FER.
        """
        self.endpoint_url = config.fer_url
        self.default_timeout = config.fer_timeout
        fer_login = config.fer_login.get_secret_value()
        fer_password = config.fer_password.get_secret_value()
        self.token = 'Basic ' + base64.b64encode(f"{fer_login}:{fer_password}".encode()).decode('utf-8')
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(self.base_dir, 'templates')
        
        logger.info(f"FERClient initialized with endpoint: {self.endpoint_url}")

    def load_xml_template(
        self,
        action: str,
        data: Dict[str, str]
    ) -> str:
        """
        Формирует строку SOAP XML запроса.
        """
        filename = f"{action}.xml"
        template_path = os.path.join(self.templates_dir, filename)
        
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                xml_template = file.read()
            return xml_template.format(**data)
        except FileNotFoundError:
            logger.error(f"XML template not found: {template_path}")
            raise FERClientError(f"XML template not found: {template_path}")        
        except KeyError as e:
            missing_key = str(e)
            logger.error(f"Missing required data key in XML template: {missing_key}")
            raise FERClientError(
               f"Missing required data key in XML template: {missing_key}"
            )
        except Exception as e:
            logger.error(f"Error loading XML template: {str(e)}")
            raise FERClientError(f"Error loading XML template: {str(e)}")
        
    def send(
        self,
        action: str,
        data: Dict[str, str]
    ) -> str:
        xml_body = self.load_xml_template(action, data)
                
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'Authorization': self.token,
            'SOAPAction': action
        }
        response = requests.post(self.endpoint_url.get_secret_value(), data=xml_body, headers=headers)
        if response.status_code != 200:
            logger.error(f"FER API request failed with status code {response.status_code}")
            raise FERClientError(f"FER API request failed with status code {response.status_code}")
        
        return response.text
        
        
# Создаем глобальный экземпляр сервиса
fer_client = FERClient()