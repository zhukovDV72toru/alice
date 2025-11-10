from fuzzywuzzy import process, fuzz
import csv
import re
from typing import List, Dict, Optional, Union, Any
import os
from pathlib import Path


class ProfessionSearcher:
    def __init__(self, csv_filename: str = 'spec_list.csv'):
        """
        Инициализация поисковика профессий

        Args:
            csv_filename: Путь к CSV файлу с профессиями (по умолчанию 'spec_list.csv')
        """
        self.csv_filename = self._resolve_csv_path(csv_filename)
        self.professions: List[Dict[str, str]] = self._load_professions()

    def _resolve_csv_path(self, csv_filename: str) -> str:
        """Разрешает путь к CSV файлу относительно корня проекта"""
        # Если указан абсолютный путь, используем его
        if os.path.isabs(csv_filename):
            return csv_filename

        # Пытаемся найти файл относительно корня проекта
        project_root = Path(__file__).parent.parent  # Поднимаемся на уровень выше services
        csv_path = project_root / csv_filename

        if csv_path.exists():
            return str(csv_path)

        # Если файл не найден в корне, возвращаем оригинальный путь
        return csv_filename

    def _load_professions(self) -> List[Dict[str, str]]:
        """Загрузка профессий из CSV файла"""
        professions = []

        try:
            with open(self.csv_filename, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file, delimiter=',')
                for row in reader:
                    professions.append({
                        'show_in_help': row.get('Отображать при команде помощь', False),
                        'code': row.get('Код', ''),
                        'name': row.get('Наименование', ''),
                        'id': row.get('Уникальный идентификатор', ''),
                    })
        except FileNotFoundError:
            raise FileNotFoundError(
                f"CSV файл не найден: {self.csv_filename}. "
                f"Убедитесь, что файл находится в корне проекта."
            )
        except Exception as e:
            raise Exception(f"Ошибка при чтении CSV файла: {e}")

        return professions

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Нормализация текста для улучшения поиска"""
        text = text.lower().strip()
        text = text.replace('-', ' ')
        text = re.sub(r'[^\w\s]', '', text)  # Удаляем пунктуацию
        text = re.sub(r'\s+', ' ', text)  # Удаляем лишние пробелы
        return text

    def _find_exact_match(self, user_input: str) -> Optional[Dict[str, str]]:
        """Поиск точного совпадения"""
        normalized_input = self._normalize_text(user_input)
        for profession in self.professions:
            if normalized_input in self._normalize_text(profession['name']):
                return profession
        return None

    def _find_fuzzy_matches(self, user_input: str, threshold: int = 50) -> List[Dict[str, Any]]:
        """Нечеткий поиск совпадений"""
        normalized_input = self._normalize_text(user_input)
        profession_names = [p['name'] for p in self.professions]
        normalized_names = [self._normalize_text(name) for name in profession_names]

        matches = process.extract(normalized_input, normalized_names,
                                  scorer=fuzz.token_sort_ratio,
                                  limit=5)

        results: List[Dict[str, Any]] = []
        for match in matches:
            matched_normalized, score = match
            if score >= threshold:
                # Находим индекс совпадения в оригинальном списке
                index = normalized_names.index(matched_normalized)
                results.append({
                    'profession': self.professions[index],
                    'score': score,
                    'original_name': profession_names[index]
                })

        return results

    def _find_by_keywords(self, user_input: str) -> Optional[Dict[str, str]]:
        """Поиск по ключевым словам"""
        keywords = user_input.split()
        for profession in self.professions:
            profession_lower = self._normalize_text(profession['name'])
            if all(self._normalize_text(keyword) in profession_lower for keyword in keywords):
                return profession
        return None

    def search(self, user_input: str, threshold: int = 50) -> Union[Dict[str, str], List[Dict[str, Any]], None]:
        """
        Умный поиск профессии по входной строке

        Args:
            user_input: Входная строка от пользователя
            threshold: Порог совпадения для нечеткого поиска (0-100)

        Returns:
            Dict: если найдено одно точное совпадение
            List[Dict]: если найдено несколько нечетких совпадений
            None: если ничего не найдено
        """
        # 1. Точное совпадение
        # exact_match = self._find_exact_match(user_input)
        # if exact_match:
        #     return exact_match

        # 2. Нечеткий поиск
        fuzzy_matches = self._find_fuzzy_matches(user_input, threshold)
        if fuzzy_matches:
            # Если нашли одно хорошее совпадение, возвращаем его
            if len(fuzzy_matches) == 1 or fuzzy_matches[0]['score'] >= 80:
                return fuzzy_matches[0]['profession']
            # Иначе возвращаем список всех хороших совпадений
            return fuzzy_matches

        # 3. Поиск по ключевым словам
        keyword_match = self._find_by_keywords(user_input)
        if keyword_match:
            return keyword_match

        return None

    def get_all_professions(self) -> List[Dict[str, str]]:
        """Получить все профессии"""
        return self.professions.copy()  # Возвращаем копию для безопасности

    def get_profession_by_code(self, code: str) -> Optional[Dict[str, str]]:
        """Найти профессию по коду"""
        for profession in self.professions:
            if profession['code'] == code:
                return profession
        return None

    def get_profession_by_name(self, name: str) -> Optional[Dict[str, str]]:
        """Найти профессию по точному названию"""
        for profession in self.professions:
            if profession['name'] == name:
                return profession
        return None