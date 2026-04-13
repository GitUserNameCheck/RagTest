import json
import httpx
import os

INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/UploadedDocuments.jsonl"
OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/DocumentsHalfProcessingInfo.jsonl"
PROCESS_URL = "http://localhost:5001/api/document"
PROCESS_TYPES = ["pager_process", "pymupdf_full_process", "mineru_process_document"]

def get_processed_ids():
    """Собирает ID уже обработанных документов из файла вывода."""
    processed = set()
    if os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        if "id" in record:
                            processed.add(record["id"])
                    except json.JSONDecodeError:
                        continue
    return processed

def main():
    processed_ids = get_processed_ids()
    print(f"Найдено уже обработанных записей: {len(processed_ids)}")

    client = httpx.Client(timeout=None)

    try:
        with open(INPUT_JSONL, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Пропуск строки {line_no}: ошибка JSON ({e})")
                    continue

                doc_id = record.get("id")
                
                # КЛЮЧЕВОЙ МОМЕНТ: Проверяем, был ли этот ID обработан ранее
                if doc_id in processed_ids:
                    print(f"Пропуск id={doc_id} (уже в файле вывода)")
                    continue

                doc_name = record.get("name")
                print(f"Обработка документа id={doc_id} ({doc_name})")

                for endpoint in PROCESS_TYPES:
                    try:
                        response = client.post(
                            f"{PROCESS_URL}/{endpoint}",
                            params={"id": doc_id}
                        )

                        if response.is_success:
                            data = response.json()
                            print(f"Успех id={doc_id}, {endpoint} report_id = {data['id']}")
                            record[endpoint] = data["id"]
                        else:
                            record[endpoint] = None
                            print(f"Ошибка {endpoint} для id={doc_id}: {response.status_code}")
                    except Exception as e:
                        record[endpoint] = None
                        print(f"Исключение при запросе {endpoint} для id={doc_id}: {e}")

                # Записываем результат сразу после обработки каждого документа
                with open(OUTPUT_JSONL, "a", encoding="utf-8") as f_out:
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")

    finally:
        client.close()

if __name__ == "__main__":
    main()