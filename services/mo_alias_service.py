import pandas as pd
import logging
from typing import Dict, Any, Optional
import os
import sys

logger = logging.getLogger(__name__)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

sys.path.insert(0, project_root)
from services.redis_service import redis_service


class MoAliasService:
    def __init__(self, excel_file_path: str = None):
        # Определяем путь к файлу относительно расположения этого скрипта
        if excel_file_path is None:
            self.excel_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "mo_alias.xlsx"
            )
        else:
            self.excel_file_path = excel_file_path

        self.redis_key = "mo_alias"

    def load_mo_alias_from_excel(self) -> Dict[str, Dict[str, str]]:
        """
        Чтение mo_alias.xlsx и преобразование в словарь.

        Returns:
            Dict[str, Dict[str, str]]: Словарь с OID в качестве ключа
        """
        try:
            # Проверяем существование файла
            if not os.path.exists(self.excel_file_path):
                logger.error(f"Файл {self.excel_file_path} не найден")
                return {}

            # Читаем Excel файл
            df = pd.read_excel(self.excel_file_path)

            # Проверяем наличие необходимых колонок
            required_columns = [
                'OID',
                'Короткое наименование (текст)',
                'Короткое наименование (ttl)'
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Отсутствуют необходимые колонки: {missing_columns}")

            # Преобразуем в словарь
            mo_alias = {}
            for _, row in df.iterrows():
                oid = str(row['OID']).strip()  # Приводим к строке и убираем пробелы

                short_text = row['Короткое наименование (текст)']
                short_ttl = row['Короткое наименование (ttl)']

                short_text = None if pd.isna(short_text) else str(short_text)
                short_ttl = None if pd.isna(short_ttl) else str(short_ttl)

                mo_alias[oid] = {
                    'short_name_text': short_text,
                    'short_name_ttl': short_ttl
                }

            # Сохраняем в Redis
            redis_service.set(self.redis_key, mo_alias)
            logger.info(f"Успешно загружено {len(mo_alias)} записей из {self.excel_file_path}")

            return mo_alias

        except FileNotFoundError:
            logger.error(f"Файл {self.excel_file_path} не найден")
            raise
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {self.excel_file_path}: {e}")
            raise

    def get_mo_alias(self) -> Dict[str, Dict[str, str]]:
        """
        Получение mo_alias из Redis или из Excel файла.

        Returns:
            Dict[str, Dict[str, str]]: Словарь с данными mo_alias
        """
        try:
            # Пытаемся получить из Redis
            mo_alias = redis_service.get(self.redis_key)

            if mo_alias is not None:
                return mo_alias

            # Если в Redis нет данных, загружаем из Excel
            logger.info("Данные в Redis не найдены, загружаем из Excel файла")
            return self.load_mo_alias_from_excel()

        except Exception as e:
            logger.error(f"Ошибка при получении mo_alias: {e}")
            return {}

    def get_mo_info_by_oid(self, oid: str) -> Optional[Dict[str, str]]:
        """
        Получение информации по конкретному OID.

        Args:
            oid: OID медицинской организации

        Returns:
            Optional[Dict[str, str]]: Информация о МО или None если не найдена
        """
        mo_alias = self.get_mo_alias()
        return mo_alias.get(str(oid).strip())

    def refresh_cache(self) -> Dict[str, Dict[str, str]]:
        """
        Принудительное обновление кэша из Excel файла.

        Returns:
            Dict[str, Dict[str, str]]: Обновленные данные
        """
        logger.info("Принудительное обновление кэша mo_alias")
        return self.load_mo_alias_from_excel()


# Создаем глобальный экземпляр для удобства использования
mo_alias_service = MoAliasService()

if __name__ == "__main__":
    """
    Запуск при деплое для предзагрузки данных в Redis
    """
    import sys
    import argparse

    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


    def main():
        parser = argparse.ArgumentParser(description='Загрузка mo_alias в Redis')
        parser.add_argument(
            '--file',
            type=str,
            default="mo_alias.xlsx",
            help='Путь к Excel файлу с mo_alias'
        )

        args = parser.parse_args()

        try:
            # Создаем сервис с указанным путем к файлу
            service = MoAliasService(args.file)
            result = service.refresh_cache()
            print(f"Успешно обработано {len(result)} записей")
            sys.exit(0)

        except Exception as e:
            logger.error(f"Ошибка при выполнении: {e}")
            sys.exit(1)

    main()
