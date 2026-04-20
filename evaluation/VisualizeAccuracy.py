import json
import matplotlib.pyplot as plt
from collections import defaultdict

def plot_combined_metrics(file_path):
    # Словари для накопления данных
    source_metrics = defaultdict(lambda: {"sum": 0, "count": 0})
    task_metrics = defaultdict(lambda: {"sum": 0, "count": 0})
    total_score = 0
    total_count = 0

    # Переводчики
    trans = {
        "Layout": "Layout", "Text": "Text",
        "Understanding": "Understanding", "Locating": "Locating"
    }

    # 1. Чтение файла и сбор статистики
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            record = json.loads(line)
            
            score = record.get('score_v3', 0)
            total_score += score
            total_count += 1
            
            # Обработка источников (Sources)
            sources = record.get('evidence_sources', [])
            translated_sources = [trans.get(s, s) for s in sources]
            s_key = " + ".join(sorted(translated_sources)) if translated_sources else "Нет данных"
            source_metrics[s_key]["sum"] += score
            source_metrics[s_key]["count"] += 1
            
            # Обработка задач (Task Tag)
            raw_tag = record.get('task_tag', 'Unknown')
            t_key = trans.get(raw_tag, raw_tag)
            task_metrics[t_key]["sum"] += score
            task_metrics[t_key]["count"] += 1

    overall_accuracy = (total_score / total_count) * 100

    # 2. Создание полотна с двумя графиками
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    def draw_donut(ax, metrics, title):
        labels, counts, accuracies = [], [], []
        for key, data in metrics.items():
            labels.append(f"{key}\n({data['count']})")
            counts.append(data["count"])
            accuracies.append((data["sum"] / data["count"]) * 100)
        
        wedges, texts, autotexts = ax.pie(
            counts, labels=labels, 
            autopct=lambda pct: f"{accuracies[counts.index(min(counts, key=lambda x: abs(x/sum(counts)*100 - pct)))]:.2f}%",
            startangle=140, pctdistance=0.72,
            wedgeprops=dict(width=0.45, edgecolor='w'),
            textprops=dict(fontsize=12)
        )

        for t in autotexts:
            t.set_fontsize(11)
            t.set_fontweight("bold")
            t.set_color("white")
        
        # Общая информация в центре каждого круга
        ax.text(0, 0, f"Total: {total_count}\nAcc: {overall_accuracy:.2f}%", 
                ha='center', va='center', fontsize=18, fontweight='bold')
        ax.set_title(title, fontsize=14)

    # Рисуем оба графика
    draw_donut(ax1, source_metrics, "Точность по источникам (Sources)")
    draw_donut(ax2, task_metrics, "Точность по типам задач (Task Tags)")

    plt.tight_layout()
    plt.show()

# PATH = "C:/Users/howto/Downloads/miner/ScoredMineru.jsonl"
# PATH = "C:/Users/howto/Downloads/test/ScoredPyMuPDFFull.jsonl"
# PATH = "C:/Users/howto/Downloads/test/ScoredPyMuPDFPartial.jsonl"

# PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/mineru/ScoredMineru.jsonl"
# PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pure_llm/ScoredPureLLM.jsonl"
# PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_full/ScoredPyMuPDFFull.jsonl"
PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_partial/ScoredPyMuPDFPartial.jsonl"

# Замените на имя вашего файла
plot_combined_metrics(PATH)
