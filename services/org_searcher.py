from fuzzywuzzy import process, fuzz
import re
from typing import List, Dict, Optional, Union, Any
import os
from pathlib import Path
from services.mo_alias_service import mo_alias_service
from collections import defaultdict


class OrgSearcher:
    def __init__(self, medic_orgs):
        self.medic_orgs = medic_orgs

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Нормализация текста для улучшения поиска"""
        text = text.lower().strip()
        text = text.replace('-', ' ')
        text = re.sub(r'[^\w\s]', '', text)  # Удаляем пунктуацию
        text = re.sub(r'\s+', ' ', text)  # Удаляем лишние пробелы
        return text

    def _find_fuzzy_matches(self, user_input: str, threshold: int = 50) -> List[Dict[str, Any]]:
        """Нечеткий поиск совпадений"""
        normalized_input = self._normalize_text(user_input)
        org_names = [p['name'] for p in self.medic_orgs]
        org_address = [p['address'] for p in self.medic_orgs]

        short_names = []
        short_names_indices = []
        for i, org in enumerate(self.medic_orgs):
            oid = org.get('oid')
            if oid:
                alias_object = mo_alias_service.get_mo_info_by_oid(oid)
                if alias_object:
                    short_text = alias_object.get('short_name_text')
                    if short_text:
                        short_names.append(short_text)
                        short_names_indices.append(i)

        normalized_names = [self._normalize_text(name) for name in org_names]
        normalized_address = [self._normalize_text(address) for address in org_address]
        normalized_short_names = [self._normalize_text(name) for name in short_names]

        # Используем defaultdict для группировки результатов по организации
        results_dict = defaultdict(lambda: {'score': 0, 'original_names': set()})

        # Поиск по коротким именам
        if normalized_short_names:
            short_matches = process.extract(normalized_input, normalized_short_names,
                                            scorer=fuzz.token_sort_ratio,
                                            limit=3)
            for match in short_matches:
                matched_normalized, score = match
                if score >= threshold:
                    # Находим индекс совпадения в списке коротких имен
                    index_in_short = normalized_short_names.index(matched_normalized)
                    # Получаем индекс оригинальной организации
                    org_index = short_names_indices[index_in_short]
                    org = self.medic_orgs[org_index]

                    # Используем кортеж ключевых полей как идентификатор организации
                    org_key = (org.get('oid'), org.get('name'), org.get('address'))
                    results_dict[org_key]['score'] = max(results_dict[org_key]['score'], score)
                    results_dict[org_key]['original_names'].add(short_names[index_in_short])

        # Поиск по полным именам
        matches = process.extract(normalized_input, normalized_names,
                                  scorer=fuzz.token_sort_ratio,
                                  limit=3)

        for match in matches:
            matched_normalized, score = match
            if score >= threshold:
                index = normalized_names.index(matched_normalized)
                org = self.medic_orgs[index]

                org_key = (org.get('oid'), org.get('name'), org.get('address'))
                results_dict[org_key]['score'] = max(results_dict[org_key]['score'], score)
                results_dict[org_key]['original_names'].add(org_names[index])

        # Поиск по адресам
        matches = process.extract(normalized_input, normalized_address,
                                  scorer=fuzz.token_sort_ratio,
                                  limit=3)

        for match in matches:
            matched_normalized, score = match
            if score >= threshold:
                index = normalized_address.index(matched_normalized)
                org = self.medic_orgs[index]

                org_key = (org.get('oid'), org.get('name'), org.get('address'))
                results_dict[org_key]['score'] = max(results_dict[org_key]['score'], score)
                results_dict[org_key]['original_names'].add(org_address[index])

        # Преобразуем defaultdict в список результатов
        results: List[Dict[str, Any]] = []
        for org_key, data in results_dict.items():
            # Находим оригинальную организацию по ключу
            org = next((o for o in self.medic_orgs
                        if (o.get('oid'), o.get('name'), o.get('address')) == org_key), None)
            if org:
                results.append({
                    'org': org,
                    'score': data['score'],
                    'original_names': list(data['original_names'])
                })

        # Сортируем результаты по score в убывающем порядке
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

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

        # 2. Нечеткий поиск
        fuzzy_matches = self._find_fuzzy_matches(user_input, threshold)
        print(f"fuzzy_matches:")
        if fuzzy_matches:
            # Если нашли одно хорошее совпадение, возвращаем его
            print(fuzzy_matches)
            if len(fuzzy_matches) == 1 or fuzzy_matches[0]['score'] >= 50:
                return fuzzy_matches[0]['org']
            # Иначе возвращаем список всех хороших совпадений
            return fuzzy_matches

        return None