import json
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# Leave empty {} if you want English labels
trans = {
    "Layout": "Разметка",
    "Text": "Текст",
    "Figure": "Изображение",
    "Table": "Таблица",
    "Others": "Другое",
    "Understanding": "Понимание",
    "Locating": "Обнаружение",
    "Reasoning": "Рассуждение"
}

def make_combined_plot(task_tag_counts, evidence_counts):
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    fig.subplots_adjust(wspace=0.3)
    # ==================================================
    # Left: Task Tag Donut Chart
    # ==================================================
    ax = axes[0]

    total = task_tag_counts.sum()

    labels = [
        f"{name}\n({count})"
        for name, count in zip(task_tag_counts.index, task_tag_counts.values)
    ]

    wedges, texts, autotexts = ax.pie(
        task_tag_counts.values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.72,
        labeldistance=1.15,
        radius=0.8,
        wedgeprops=dict(width=0.42),
        textprops=dict(fontsize=12)
    )

    for t in autotexts:
        t.set_fontsize(15)
        t.set_fontweight("bold")
        t.set_color("white")

    ax.text(
        0,
        0,
        f"Всего\n{total}",
        ha="center",
        va="center",
        fontsize=18,
        fontweight="bold"
    )

    ax.set_title("Категория вопроса", fontsize=20)

    ax.set_box_aspect(0.8)

    # ==================================================
    # Right: Evidence Source Bar Chart
    # ==================================================
    ax = axes[1]

    labels = [tr(x) for x in evidence_counts.index]


    bars = ax.bar(labels, evidence_counts.values, width=0.5)

    ax.set_xticklabels(labels, fontsize=12)

    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{int(height)}",
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold"
        )

    ax.set_title("Элементы с ответом", fontsize=20)
    ax.set_ylabel("Количество", fontsize=15)

    ax.set_box_aspect(0.8)


    fig.savefig("C:/Users/howto/Downloads/SemanticSearch/RagTestProject/evaluation/Dataset.png")
    plt.tight_layout()
    plt.show()

def tr(value):
    return trans.get(value, value)


def make_pie_chart(series, title):
    total = series.sum()

    fig, ax = plt.subplots(figsize=(8, 8))

    labels = [
        f"{name}\n({count})"
        for name, count in zip(series.index, series.values)
    ]

    wedges, texts, autotexts = ax.pie(
        series.values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.72,
        labeldistance=1.08,
        wedgeprops=dict(width=0.42),
        textprops=dict(fontsize=12)
    )

    for t in autotexts:
        t.set_fontsize(11)
        t.set_fontweight("bold")
        t.set_color("white")

    ax.text(
        0, 0,
        f"Всего\n{total}",
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold"
    )

    ax.set_title(title, fontsize=18, pad=25)
    plt.tight_layout()
    plt.show()


def make_bar_chart(series, title):
    labels = [tr(x) for x in series.index]

    fig, ax = plt.subplots(figsize=(8, 6))

    bars = ax.bar(labels, series.values)

    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            str(int(height)),
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold"
        )

    ax.set_title(title, fontsize=16)
    ax.set_ylabel("Количество")

    plt.tight_layout()
    plt.show()


def main():
    jsonl_path = (
        "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/evaluation/FilteredQuestions.jsonl"
    )

    records = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    df = pd.DataFrame(records)

    print(f"Loaded {len(df)} records\n")

    # --------------------------------------------------
    # Task tags
    # --------------------------------------------------
    task_tag_counts = (
        df["task_tag"]
        .fillna("Unknown")
        .map(tr)
        .value_counts()
    )

    print("Task Tag Counts:")
    print(task_tag_counts)
    print()

    # --------------------------------------------------
    # Evidence source counts
    # Count every occurrence independently.
    # Example:
    # ["Text", "Table"] -> +1 Text, +1 Table
    # --------------------------------------------------
    evidence_types = [
        "Table",
        "Others",
        "Text",
        "Layout",
        "Figure"
    ]

    source_counter = Counter()

    for item in df["evidence_sources"].dropna():
        if not isinstance(item, list):
            item = [item]

        for src in item:
            source_counter[str(src).strip()] += 1

    evidence_counts = pd.Series(
        {
            src: source_counter.get(src, 0)
            for src in evidence_types
        }
    )

    print("Evidence Source Counts:")
    print(evidence_counts)
    print()

    # --------------------------------------------------
    # Visualizations
    # --------------------------------------------------

    make_combined_plot(
        task_tag_counts,
        evidence_counts
    )

    # make_pie_chart(
    #     task_tag_counts,
    #     "Task Tag Distribution"
    # )

    # make_bar_chart(
    #     evidence_counts,
    #     "Evidence Source Distribution"
    # )


if __name__ == "__main__":
    main()