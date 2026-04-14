import json

QUESTION_OBJECTS_FILE = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/FilteredQuestions.jsonl"
DOCUMENT_OBJECTS_FILE = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_full/ProcessedPyMuPDFFull.jsonl"
OUTPUT_FILE = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_full/MergedProcessedPyMuPDFFull.jsonl"


def load_jsonl(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items

questions = load_jsonl(QUESTION_OBJECTS_FILE)
documents = load_jsonl(DOCUMENT_OBJECTS_FILE)


with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
    for question in questions:
        doc_no = question.get("doc_no")
        for document in documents:
            pdf_name: str = document.get("name")
            pdf_base = pdf_name.split(".")[0]

            if doc_no != pdf_base:
                continue

            record = {
                "id": document.get("id"),
                "pymupdf_full_process": document.get("pymupdf_full_process"),
                "task_tag": question.get("task_tag"),
                "subTask": question.get("subTask"),
                "doc_no": question.get("doc_no"),
                "path": document.get("path"),
                "total_pages": question.get("total_pages"),
                "start_end_idx": question.get("start_end_idx"),
                "question_id": question.get("question_id"),
                "question_type": question.get("question_type"),
                "question": question.get("question"),
                "answer_format": question.get("answer_format"),
                "answer": question.get("answer"),
                "detailed_evidences": question.get("detailed_evidences"),
                "evidence_pages": question.get("evidence_pages"),
                "evidence_sources": question.get("evidence_sources"),
            }

            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"Done! Output written to {OUTPUT_FILE}")