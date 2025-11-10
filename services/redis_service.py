import json
import logging
from typing import Any, Optional, Dict, List, Union
from datetime import timedelta
import redis
from redis.exceptions import RedisError

from config import config

logger = logging.getLogger(__name__)


class RedisService:
    """Сервис для работы с Redis."""
    
    def __init__(self):
        self.redis_url = config.redis_url
        self._client = None
    
    @property
    def client(self) -> redis.Redis:
        """Ленивая инициализация Redis клиента."""
        if self._client is None:
            try:
                self._client = redis.Redis.from_url(
                    self.redis_url,
                    decode_responses=True,  # Автоматически декодировать ответы в строки
                    socket_timeout=5,       # Таймаут подключения
                    socket_connect_timeout=5,  # Таймаут соединения
                    retry_on_timeout=True   # Повторять попытки при таймауте
                )
                # Проверяем подключение
                self._client.ping()
            except RedisError as e:
                logger.error(f"Ошибка подключения к Redis: {e}")
                raise
        return self._client
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Сохраняет значение по ключу.
        
        Args:
            key: Ключ
            value: Значение (будет сериализовано в JSON)
            expire: Время жизни в секундах
            
        Returns:
            bool: Успешность операции
        """
        try:
            if not isinstance(value, (str, int, float)):
                value = json.dumps(value)
            
            if expire:
                return self.client.setex(key, timedelta(seconds=expire), value)
            else:
                return self.client.set(key, value)
        except RedisError as e:
            logger.error(f"Ошибка записи в Redis: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получает значение по ключу.
        
        Args:
            key: Ключ
            default: Значение по умолчанию, если ключ не найден
            
        Returns:
            Any: Значение или default
        """
        try:
            value = self.client.get(key)
            if value is None:
                return default
            
            # Пытаемся десериализовать JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except RedisError as e:
            logger.error(f"Ошибка чтения из Redis: {e}")
            return default
    
    def delete(self, *keys) -> int:
        """
        Удаляет один или несколько ключей.
        
        Args:
            keys: Ключи для удаления
            
        Returns:
            int: Количество удаленных ключей
        """
        try:
            return self.client.delete(*keys)
        except RedisError as e:
            logger.error(f"Ошибка удаления из Redis: {e}")
            return 0
        
    def delete_by_pattern(self, pattern: str) -> int:
        """
        Удаляет все ключи, соответствующие заданному шаблону.
        
        Args:
            pattern: Шаблон для поиска ключей (например, "user:123:*")
            
        Returns:
            int: Количество удаленных ключей
        """
        try:
            # Находим все ключи, соответствующие шаблону
            keys = self.client.keys(pattern)
            
            if not keys:
                return 0
                
            # Удаляем все найденные ключи
            return self.client.delete(*keys)
        except RedisError as e:
            logger.error(f"Ошибка удаления ключей по шаблону {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """
        Проверяет существование ключа.
        
        Args:
            key: Ключ для проверки
            
        Returns:
            bool: True если ключ существует
        """
        try:
            return self.client.exists(key) == 1
        except RedisError as e:
            logger.error(f"Ошибка проверки ключа в Redis: {e}")
            return False
    
    def expire(self, key: str, time: int) -> bool:
        """
        Устанавливает время жизни ключа в секундах.
        
        Args:
            key: Ключ
            time: Время жизни в секундах
            
        Returns:
            bool: Успешность операции
        """
        try:
            return self.client.expire(key, time)
        except RedisError as e:
            logger.error(f"Ошибка установки TTL в Redis: {e}")
            return False
    
    def hset(self, name: str, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Устанавливает значение поля в хеше.
        
        Args:
            name: Имя хеша
            key: Ключ поля
            value: Значение поля
            expire: Время жизни в секундах
            
        Returns:
            bool: Успешность операции
        """
        try:
            if not isinstance(value, (str, int, float)):
                value = json.dumps(value)
            hset_result = self.client.hset(name, key, value)
            if expire and hset_result:
                self.client.expire(name, expire)
            return hset_result
        except RedisError as e:
            logger.error(f"Ошибка записи в хеш Redis: {e}")
            return False
    
    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """
        Получает значение поля из хеша.
        
        Args:
            name: Имя хеша
            key: Ключ поля
            default: Значение по умолчанию
            
        Returns:
            Any: Значение или default
        """
        try:
            value = self.client.hget(name, key)
            if value is None:
                return default
            
            # Пытаемся десериализовать JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except RedisError as e:
            logger.error(f"Ошибка чтения из хеша Redis: {e}")
            return default
    
    def hgetall(self, name: str) -> Dict[str, Any]:
        """
        Получает все поля и значения хеша.
        
        Args:
            name: Имя хеша
            
        Returns:
            Dict[str, Any]: Словарь с полями и значениями
        """
        try:
            result = self.client.hgetall(name)
            decoded_result = {}
            for key, value in result.items():
                try:
                    decoded_result[key] = json.loads(value)
                except json.JSONDecodeError:
                    decoded_result[key] = value
            return decoded_result
        except RedisError as e:
            logger.error(f"Ошибка чтения хеша из Redis: {e}")
            return {}
    
    def sadd(self, name: str, *values) -> int:
        """
        Добавляет элементы в множество.
        
        Args:
            name: Имя множества
            values: Значения для добавления
            
        Returns:
            int: Количество добавленных элементов
        """
        try:
            # Сериализуем нестроковые значения
            serialized_values = [
                json.dumps(value) if not isinstance(value, (str, int, float)) else value
                for value in values
            ]
            return self.client.sadd(name, *serialized_values)
        except RedisError as e:
            logger.error(f"Ошибка добавления в множество Redis: {e}")
            return 0
    
    def smembers(self, name: str) -> List[Any]:
        """
        Получает все элементы множества.
        
        Args:
            name: Имя множества
            
        Returns:
            List[Any]: Список элементов
        """
        try:
            members = self.client.smembers(name)
            result = []
            for member in members:
                try:
                    result.append(json.loads(member))
                except json.JSONDecodeError:
                    result.append(member)
            return result
        except RedisError as e:
            logger.error(f"Ошибка чтения множества из Redis: {e}")
            return []
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Увеличивает значение на указанное количество.
        
        Args:
            key: Ключ
            amount: Значение для увеличения
            
        Returns:
            Optional[int]: Новое значение или None при ошибке
        """
        try:
            return self.client.incrby(key, amount)
        except RedisError as e:
            logger.error(f"Ошибка увеличения значения в Redis: {e}")
            return None
    
    def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Уменьшает значение на указанное количество.
        
        Args:
            key: Ключ
            amount: Значение для уменьшения
            
        Returns:
            Optional[int]: Новое значение или None при ошибке
        """
        try:
            return self.client.decrby(key, amount)
        except RedisError as e:
            logger.error(f"Ошибка уменьшения значения в Redis: {e}")
            return None
    
    def keys(self, pattern: str = "*") -> List[str]:
        """
        Поиск ключей по шаблону.
        
        Args:
            pattern: Шаблон поиска
            
        Returns:
            List[str]: Список ключей
        """
        try:
            return self.client.keys(pattern)
        except RedisError as e:
            logger.error(f"Ошибка поиска ключей в Redis: {e}")
            return []
    
    def close(self):
        """Закрывает соединение с Redis."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Соединение с Redis закрыто")


# Создаем глобальный экземпляр сервиса
redis_service = RedisService()