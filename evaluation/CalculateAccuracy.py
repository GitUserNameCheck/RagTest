import json
from collections import defaultdict

def calculate_jsonl_metrics(file_path):
    total_score = 0
    total_count = 0
    
    # Словари для метрик
    source_metrics = defaultdict(lambda: {"sum": 0, "count": 0})
    task_metrics = defaultdict(lambda: {"sum": 0, "count": 0})

    # Перевод терминов для вывода
    trans = {
        "Layout": "Разметка", 
        "Text": "Текст",
        "Understanding": "Понимание", 
        "Locating": "Обнаружение"
    }

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            record = json.loads(line)
            
            score = record.get('score_v3', 0)
            total_score += score
            total_count += 1
            
            # 1. Метрики по источникам (Evidence Sources)
            sources = record.get('evidence_sources', [])
            translated_sources = [trans.get(s, s) for s in sources]
            source_key = " + ".join(sorted(translated_sources)) if translated_sources else "Нет данных"
            
            source_metrics[source_key]["sum"] += score
            source_metrics[source_key]["count"] += 1
            
            # 2. Метрики по типам задач (Task Tag)
            raw_tag = record.get('task_tag', 'Unknown')
            task_key = trans.get(raw_tag, raw_tag)
            
            task_metrics[task_key]["sum"] += score
            task_metrics[task_key]["count"] += 1

    # Вывод результатов
    print(f"--- Общие метрики ---")
    print(f"Всего записей: {total_count}")
    print(f"Общая точность: {total_score / total_count:.4f}\n")

    print(f"--- Точность по источникам (Evidence Source) ---")
    for source, data in source_metrics.items():
        accuracy = data["sum"] / data["count"]
        print(f"{source}: {accuracy:.4f} (Кол-во: {data['count']})")

    print(f"\n--- Точность по типам задач (Task Tag) ---")
    for task, data in task_metrics.items():
        accuracy = data["sum"] / data["count"]
        print(f"{task}: {accuracy:.4f} (Кол-во: {data['count']})")

# Пути к файлам
# PATH = "C:/Users/howto/Downloads/test/ScoredMineru.jsonl"
# PATH = "C:/Users/howto/Downloads/test/ScoredPyMuPDFFull.jsonl"
# PATH = "C:/Users/howto/Downloads/test/ScoredPyMuPDFPartial.jsonl"

# PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/mineru/ScoredMineru.jsonl"
# PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pure_llm/ScoredPureLLM.jsonl"
# PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_full/ScoredPyMuPDFFull.jsonl"
PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_partial/ScoredPyMuPDFPartial.jsonl"

calculate_jsonl_metrics(PATH)
