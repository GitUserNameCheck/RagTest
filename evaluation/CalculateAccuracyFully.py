import json
from collections import defaultdict


jsonl_file_path = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_full/ScoredPyMuPDFFull.jsonl"

data_store = defaultdict(lambda: defaultdict(lambda: {"score": 0.0, "count": 0}))

task_totals = defaultdict(lambda: {"score": 0.0, "count": 0})

total_dataset_score = 0.0
total_dataset_questions = 0

with open(jsonl_file_path, "r", encoding="utf-8") as file:
    for line_num, line in enumerate(file, 1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)

            task_tag = data.get("task_tag")  or "Unknown Task"
            task_tag = str(task_tag).strip().upper()

            score = float(data.get("score_v3", 0.0))

            total_dataset_score += score
            total_dataset_questions += 1

            task_totals[task_tag]["score"] += score
            task_totals[task_tag]["count"] += 1

            raw_subtask = data.get("subTask")
            if isinstance(raw_subtask, list):
                subtasks = raw_subtask
            elif isinstance(raw_subtask, str) and raw_subtask.strip():
                subtasks = [raw_subtask]
            else:
                subtasks = []

            if not subtasks:
                subtasks = ["Unknown Subtask"]

            for subtask in subtasks:
                subtask_name = str(subtask).strip()
                data_store[task_tag][subtask_name]["score"] += score
                data_store[task_tag][subtask_name]["count"] += 1

        except json.JSONDecodeError:
            print(f"Пропущена некорректная строка JSON: {line_num}")
        except Exception as e:
            print(f"Ошибка обработки строки {line_num}: {e}")

if not data_store:
    print("Данные не загружены. Проверьте путь к файлу.")

for task, subtasks_dict in sorted(data_store.items()):
    print(f"\n================ ГЛАВНАЯ КАТЕГОРИЯ: {task} ================")
    print(f"{'Подкатегория':<35} | {'Точность (%)':<15} | {'Всего вопросов':<15}")
    print("-" * 72)

    # Вывод подкатегорий
    for subtask, metrics in sorted(subtasks_dict.items()):
        sub_score = metrics["score"]
        sub_questions = metrics["count"]
        sub_accuracy = (sub_score / sub_questions) * 100 if sub_questions > 0 else 0.0
        print(f"{subtask:<35} | {sub_accuracy:.2f}% | {sub_questions:<15}")
    
    # Расчет чистой точности всей главной категории без дубликатов строк
    clean_task_score = task_totals[task]["score"]
    clean_task_questions = task_totals[task]["count"]
    task_accuracy = (clean_task_score / clean_task_questions) * 100 if clean_task_questions > 0 else 0.0
    
    print("-" * 72)
    print(f"{'ОБЩАЯ ТОЧНОСТЬ ПО КАТЕГОРИИ':<35} | {task_accuracy:.2f}% | {clean_task_questions:<15}")

# Итог по всему датасету
print("\n================ ИТОГ ПО ВСЕМУ ДАТАСЕТУ ================")
dataset_accuracy = (total_dataset_score / total_dataset_questions) * 100 if total_dataset_questions > 0 else 0.0
print(f"Общая точность датасета: {dataset_accuracy:.2f}%")
print(f"Всего уникальных вопросов в датасете: {total_dataset_questions}")