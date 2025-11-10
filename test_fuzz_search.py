from services.profession_searcher import ProfessionSearcher
import sys

if len(sys.argv) < 2:
    print("Не задана должность врача")
    exit(1)


# Использование с файлом по умолчанию (spec_list.csv в корне проекта)
searcher = ProfessionSearcher()  # Автоматически ищет spec_list.csv в корне

# Поиск профессии
input = sys.argv[1]

result = searcher.search(input)
print(result)