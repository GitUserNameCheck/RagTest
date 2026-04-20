import json
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt

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
        f"Total\n{total}",
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold"
    )

    ax.set_title(title, fontsize=18, pad=25)
    plt.tight_layout()
    plt.show()

def make_two_pie_charts(series1, title1, series2, title2):
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    charts = [
        (axes[0], series1, title1),
        (axes[1], series2, title2)
    ]

    for ax, series, title in charts:
        total = series.sum()

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
            labeldistance=1.2,
            radius=0.75,
            wedgeprops=dict(width=0.4),
            textprops=dict(fontsize=12)
        )

        for t in autotexts:
            t.set_fontsize(12)
            t.set_fontweight("bold")
            t.set_color("white")

        ax.text(
            0, 0,
            f"Total\n{total}",
            ha="center",
            va="center",
            fontsize=16,
            fontweight="bold"
        )

        ax.set_title(title, fontsize=14, pad=18)

    plt.tight_layout()
    plt.show()


# -----------------------------------
# Normalize evidence_sources into categories:
#   - Text only
#   - Layout only
#   - Text + Layout
#   - Other
# -----------------------------------
def classify_sources(src):
    if not isinstance(src, list):
        src = [src]

    vals = {str(x).strip().lower() for x in src}

    has_text = "text" in vals
    has_layout = "layout" in vals

    # if has_text and has_layout:
    #     return "Разметка + Текст"
    # elif has_text:
    #     return "Текст"
    # elif has_layout:
    #     return "Разметка"
    # else:
    #     return "Other"
    
    if has_text and has_layout:
        return "Layout + Text"
    elif has_text:
        return "Text"
    elif has_layout:
        return "Lauyout"
    else:
        return "Other"


def main():
    
    jsonl_path = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/evaluation/FilteredQuestions.jsonl"

    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():  # skip empty lines
                records.append(json.loads(line))

    df = pd.DataFrame(records)

    # print(df.head())
    # print(df.columns)
    # print(df.shape)



    task_tag_counts = df["task_tag"].value_counts(dropna=False)

    print("Task Tag Counts:")
    print(task_tag_counts)
    print()



    all_sources = []

    for item in df["evidence_sources"].dropna():
        if isinstance(item, list):
            all_sources.extend(item)
        else:
            all_sources.append(item)

    evidence_source_counts = pd.Series(Counter(all_sources)).sort_values(ascending=False)

    print("Evidence Sources Counts:")
    print(evidence_source_counts)

    # Apply classification
    df["evidence_category"] = df["evidence_sources"].apply(classify_sources)

    # Count categories
    category_counts = df["evidence_category"].value_counts()

    task_tag_counts = df["task_tag"].value_counts(dropna=False)


    # make_pie_chart(task_tag_counts, "Task Tag Distribution")

    # make_pie_chart(category_counts, "Evidence Source Categories")

    # task_tag_counts = task_tag_counts.rename({
    #     "Understanding": "Понимание",
    #     "Locating": "Обнаружение"
    # })


    make_two_pie_charts(task_tag_counts, "Task Tag Distribution", category_counts, "Evidence Source Categories")


if __name__ == "__main__":
    main()


