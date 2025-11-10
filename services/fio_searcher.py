from fuzzywuzzy import process, fuzz
import re
from typing import List, Dict, Optional, Union, Any
import os
from pathlib import Path


class FioSearcher:
    def __init__(self, fio_list):
        self.fio_list = fio_list


    @staticmethod
    def _normalize_text(text: str) -> str:
        """Нормализация текста для улучшения поиска"""
        text = text.lower().strip()
        text = text.replace('-', ' ')
        text = re.sub(r'[^\w\s]', '', text)  # Удаляем пунктуацию
        text = re.sub(r'\s+', ' ', text)  # Удаляем лишние пробелы
        return text

    def _find_exact_matches(self, user_input: str) -> List[str]:
        """Поиск точного совпадения"""
        normalized_input = self._normalize_text(user_input)
        matches = []

        for fio in self.fio_list:
            normalized_fio = self._normalize_text(fio)
            # Проверяем, содержится ли введенный текст в ФИО
            if normalized_input in normalized_fio:
                matches.append(fio)

        return matches

    def _find_fuzzy_matches(self, user_input: str, threshold: int = 50) -> List[Dict[str, Any]]:
        """Нечеткий поиск совпадений"""
        normalized_input = self._normalize_text(user_input)
        normalized_list = [self._normalize_text(name) for name in self.fio_list]


        results: List[Dict[str, Any]] = []

        matches = process.extract(normalized_input, normalized_list,
                                  scorer=fuzz.token_sort_ratio,
                                  limit=3)
        print(matches)
        for match in matches:
            matched_normalized, score = match
            if score >= threshold:
                # Находим индекс совпадения в оригинальном списке
                index = normalized_list.index(matched_normalized)
                results.append({
                    'fio': self.fio_list[index],
                    'score': score
                })

        return results

    def search(self, user_input: str, threshold: int = 50) -> Union[str, None]:
        """
        Умный поиск фио по входной строке

        Args:
            user_input: Входная строка от пользователя
            threshold: Порог совпадения для нечеткого поиска (0-100)

        Returns:
            str: если найдено одно точное совпадение
            None: если ничего не найдено или найдено более одного варианта
        """
        exact_matches = self._find_exact_matches(user_input)
        if exact_matches:
            # Если найдено одно точное совпадение - возвращаем его
            if len(exact_matches) == 1:
                return exact_matches[0]
            # Если найдено несколько точных совпадений - возвращаем None
            else:
                return None

        # 2. Нечеткий поиск
        fuzzy_matches = self._find_fuzzy_matches(user_input, threshold)
        print(fuzzy_matches)
        if fuzzy_matches:
            # Если нашли одно хорошее совпадение, возвращаем его
            if len(fuzzy_matches) == 1 or fuzzy_matches[0]['score'] >= 80:
                return fuzzy_matches[0]['fio']
            # Иначе возвращаем None
            return None
        return None