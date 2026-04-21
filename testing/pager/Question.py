import json
import os
import httpx

SYSTEM_SEARCH_DOCUMENTS_URL = "http://localhost:5001/api/document/report_points_based_search"
QUESTION_JSONL_PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pager/MergedProcessedPager.jsonl"
OUTPUT_JSONL_PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pager/PagerAnswers.jsonl"

SYSTEM_PROMPT = (
    "You are an expert in document question answering. Answer the question strictly based on the given document. \n Following is our question: \n"
)

def load_jsonl(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main():
    questions = load_jsonl(QUESTION_JSONL_PATH)

    existing_ids = set()
    if os.path.exists(OUTPUT_JSONL_PATH):
        for row in load_jsonl(OUTPUT_JSONL_PATH):
            existing_ids.add(row.get("question_id"))

    client = httpx.Client(
        timeout=None,
    )

    for question in questions:
        question_id = question.get("question_id")
        if question_id in existing_ids:
            print(f"Skipping existing question {question_id}")
            continue

        print(f"→ Processing QID: {question_id}")

        try:
            response = client.get(
                SYSTEM_SEARCH_DOCUMENTS_URL,
                params={
                    "prompt": SYSTEM_PROMPT,
                    "search_text": question.get("question"),
                    "report_id": question.get("pager_process")
                }
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error for QID {question_id}: {e}")
            # continue

        data = response.json()
        predicted_answer = data.get("message", "None")

        out = {
            "task_tag": question.get("task_tag"),
            "subTask": question.get("subTask"),
            "doc_no": question.get("doc_no"),
            "id": question.get("id"),
            "pager_process": question.get("pager_process"),
            "path": question.get("path"),
            "total_pages": question.get("total_pages"),
            "start_end_idx": question.get("start_end_idx"),
            "question_id": question_id,
            "question_type": question.get("question_type"),
            "question": question.get("question"),
            "answer_format": question.get("answer_format"),
            "answer": question.get("answer"),
            "detailed_evidences": question.get("detailed_evidences"),
            "evidence_pages": question.get("evidence_pages"),
            "evidence_sources": question.get("evidence_sources"),
            "predicted_answer": predicted_answer
        }

        append_jsonl(OUTPUT_JSONL_PATH, out)

    client.close()

if __name__ == "__main__":
    main()
