from aiohttp import web
from aliceio import Dispatcher, Skill
from aliceio.webhook.aiohttp_server import (
    OneSkillAiohttpRequestHandler,
    setup_application,
)
from config import config
from web.middleware import logging_middleware, error_handling_middleware, validation_middleware, get_requests_middleware #, address_middleware
from services.patient_service import patient_service
from clients.fer_client import FERClient
from handlers.patient_introduction import setup_patient_introduction_handlers
from handlers.schedule_selection import setup_schedule_handlers
from handlers.help import setup_help_handlers
from handlers.confirmation import setup_confirmations_handlers
from handlers.doctor_selection import setup_doctor_selection_handlers
from handlers.appointment import setup_appointment_handlers
from handlers.error import setup_error_handlers
from handlers.step_back import setup_step_back_handlers


def create_app() -> web.Application:
    # Инициализация зависимостей
       
    # Настройка диспетчера
    dp = Dispatcher(use_api_storage=True)
            
    # Регистрируем обработчики из других модулей
    setup_help_handlers(dp)
    setup_step_back_handlers(dp)
    setup_patient_introduction_handlers(dp)
    setup_doctor_selection_handlers(dp)
    setup_schedule_handlers(dp)
    setup_appointment_handlers(dp)
    setup_confirmations_handlers(dp)
    setup_error_handlers(dp)

    # Настройка навыка
    skill_id = config.skill_id.get_secret_value()
    skill = Skill(skill_id=skill_id)
    
    # Создание приложения
    app = web.Application(middlewares=[logging_middleware, validation_middleware, error_handling_middleware, get_requests_middleware])
    requests_handler = OneSkillAiohttpRequestHandler(dispatcher=dp, skill=skill)
    
    # Регистрация обработчиков
    requests_handler.register(app, path=config.webhook_path)
    setup_application(app, dp, skill=skill)
    
    return app

app = create_app()

def run_server():
    web.run_app(
        app, 
        host=config.web_server_host, 
        port=config.web_server_port
    )
