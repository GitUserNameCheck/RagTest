import json
from pathlib import Path


TASK_TAXONOMY = {
    "Understanding": {
        "Single-Page": [
            "SP_Text_Understanding",
            "SP_Layout_Understanding",
            "SP_Figure_Understanding",
            "SP_Table_Understanding",
        ],
        "Multi-Page": [
            "MP_Text_Understanding",
            "MP_Layout_Understanding",
            "MP_Figure_Understanding",
            "MP_Table_Understanding",
        ],
    },
    "Locating": {
        "Cross-Element": [
            "Figure_Table_Locating",
            "Para_Title_Locating",
            "Cross_Table_Locating",
            "Cross_Title_Locating",
        ]
    },
    "Reasoning": {
        "Single-Page": [
            "SP_Text_Reasoning",
            "SP_Layout_Reasoning",
            "SP_Figure_Reasoning",
            "SP_Table_Reasoning",
        ],
        "Multi-Page": [
            "MP_Text_Reasoning",
            "MP_Layout_Reasoning",
            "MP_Figure_Reasoning",
            "MP_Table_Reasoning",
        ],
    },
}

SELECTED_TASK_TAGS = {
    "Understanding",
    "Locating",
    # "Reasoning",
}

SELECTED_SUBTASKS = {
    # "SP_Layout_Understanding",
    # "MP_Text_Understanding",
}

SELECTED_EVIDENCE_SOURCES = {
    "Layout",
    "Text",
    # "Figure",
    # "Table",
}


def should_include(item):
    task_tag = item.get("task_tag")
    if SELECTED_TASK_TAGS and not (task_tag in SELECTED_TASK_TAGS):
        return False

    sub_tasks = set(item.get("subTask", []))
    if SELECTED_SUBTASKS and not sub_tasks.issubset(SELECTED_SUBTASKS):
        return False

    evidence_sources = set(item.get("evidence_sources", []))
    if SELECTED_EVIDENCE_SOURCES and not evidence_sources.issubset(SELECTED_EVIDENCE_SOURCES):
        return False

    return True


def filter_json(
    input_jsonl_path : str,
    output_jsonl_path: str,
):
    input_jsonl_path  = Path(input_jsonl_path)
    output_jsonl_path = Path(output_jsonl_path)

    data = []
    with open(input_jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_num}") from e

    filtered_data = [item for item in data if should_include(item)]

    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for item in filtered_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Input items: {len(data)}")
    print(f"Output items: {len(filtered_data)}")
    print(f"Saved to: {output_jsonl_path}")



if __name__ == "__main__":
    filter_json(
        input_jsonl_path="C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/LongDocURL_public_with_subtask_category.jsonl",
        output_jsonl_path="C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/FilteredQuestions.jsonl",
    )