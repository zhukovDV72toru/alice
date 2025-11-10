import sys
import os
import redis
import time

# Добавляем корневую директорию проекта в Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from services.redis_service import redis_service


def test_redis_simple():
    try:
        redis_service.set("test_key_name", "Иван Иванов")
        redis_service.set("test_key_age_expire", 30, expire=36)

        time.sleep(0.1)

        name = redis_service.get("test_key_name")
        age = redis_service.get("test_key_age_expire")

        if name == "Иван Иванов" and age == 30:
            print('test_redis_simple: success')
        else:
            print('test_redis_simple: fail')

    except Exception as e:
        print(f"Ошибка Redis test_redis_simple: {e}")
        return False


def test_redis_hset():
    try:
        redis_service.hset("test_key_hset", 'person', {'name': "Иван Иванов", 'age': 44})
        redis_service.hset("test_key_hset", 'work', 'hard')

        time.sleep(0.1)

        object = redis_service.hgetall("test_key_hset")
        if object and object['person']['name'] == "Иван Иванов" and  object['person']['age'] == 44:
            print('test_redis_hset: success')
        else:
            print('test_redis_hset: fail')
    except Exception as e:
        print(f"Ошибка Redis test_redis_hset: {e}")
        return False

def test_redis_hget():
    try:
        person = redis_service.hget("test_key_hset", 'person')
        time.sleep(0.1)

        if person and person['name'] == "Иван Иванов" and  person['age'] == 44:
            print('test_redis_hget: success')
        else:
            print('test_redis_hget: fail')
    except Exception as e:
        print(f"Ошибка Redis test_redis_hget: {e}")
        return False

def test_redis_delete():
    try:
        redis_service.delete("test_key_name")
        redis_service.delete("test_key_age_expire")
        redis_service.delete("test_key_hset")

        time.sleep(0.1)

        name = redis_service.get("test_key_name")
        age = redis_service.get("test_key_age_expire")
        object = redis_service.get("test_key_hset")

        if name == None and age == None and object == None:
            print('test_redis_delete: success')
        else:
            print('test_redis_delete: fail')

    except Exception as e:
        print(f"Ошибка Redis test_redis_delete: {e}")
        return False

if __name__ == "__main__":
    test_redis_simple()
    test_redis_hset()
    test_redis_hget()
    test_redis_delete()
