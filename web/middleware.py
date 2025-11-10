import json
import logging
from datetime import datetime
from aiohttp import web
from typing import Callable, Awaitable, Dict, Any
from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("alice_skill.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@web.middleware
async def logging_middleware(
    request: web.Request, 
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    """Middleware для логирования входящих запросов и ответов"""
    start_time = datetime.now()

    # Логируем тело запроса (если есть)
    if request.body_exists and config.debug:
        try:
            body = await request.json()
            logger.info(f"Request body: {json.dumps(body, ensure_ascii=False, indent=2)}")
        except Exception as e:
            body_text = await request.text()
            # Ограничиваем длину лога для больших тел
            logged_body = body_text[:1000] + "..." if len(body_text) > 1000 else body_text
            logger.info(f"Request body (raw, first 1000 chars): {logged_body}")
            logger.debug(f"Failed to parse JSON: {e}")
    
    # Обрабатываем запрос и замеряем время выполнения
    try:
        response = await handler(request)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Логируем информацию об ответе
        logger.info(f"Response status: {response.status}, "
                   f"processed in {processing_time:.3f} seconds")        
        return response
        
    except Exception as e:
        # Логируем исключения
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Exception occurred after {processing_time:.3f} seconds: {e}", exc_info=True)
        raise

@web.middleware
async def error_handling_middleware(
    request: web.Request, 
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    """Middleware для обработки исключений и возврата корректных ответов Алисе"""
    try:
        return await handler(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        
        # Возвращаем ответ в формате, который ожидает Алиса
        error_response = {
            "response": {
                "text": "Извините, произошла внутренняя ошибка. Пожалуйста, попробуйте позже.",
                "tts": "Извините, произошла внутренняя ошибка. Пожалуйста, попробуйте позже.",
                "end_session": False
            },
            "version": "1.0"
        }
        
        return web.json_response(
            data=error_response,
            status=200  # Всегда возвращаем 200 для Алисы, даже при ошибках
        )

@web.middleware
async def validation_middleware(
    request: web.Request, 
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    """Middleware для валидации входящих запросов от Алисы"""
    # Проверяем, что запрос имеет правильный Content-Type
    if request.method == 'POST' and request.path == '/alice':
        content_type = request.headers.get('Content-Type', '')
        if not content_type.startswith('application/json'):
            logger.warning(f"Invalid Content-Type: {content_type}")
            return web.json_response(
                data={"error": "Invalid Content-Type"},
                status=415
            )
    
    return await handler(request)

@web.middleware
async def get_requests_middleware(
    request: web.Request, 
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    """Middleware для обработки всех GET-запросов"""
    if request.method == 'GET' and request.path == '/alice':
        return web.Response(
            text = 'Этот сервер используется для навыка Алисы'
        )
              
    return await handler(request)

def setup_middlewares(app: web.Application) -> None:
    """Добавляет все middleware в приложение"""
    #app.middlewares.append(address_middleware)
    app.middlewares.append(logging_middleware)
    app.middlewares.append(error_handling_middleware)
    app.middlewares.append(validation_middleware)
    app.middlewares.append(get_requests_middleware)