import json
import httpx

INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/UploadedDocuments.jsonl"   # output from previous script
OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/DocumentsHalfProcessingInfo.jsonl"
PROCESS_URL = "http://localhost:5001/api/document"
PROCESS_TYPES = ["pager_process", "pymupdf_full_process", "mineru_process_document"]

def main():
    client = httpx.Client(
        timeout=None,
    )

    try:
        with open(INPUT_JSONL, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Skipping line {line_no}: invalid JSON ({e})")
                    continue

                doc_id = record.get("id")
                doc_name = record.get("name")

                print(f"Processing document id={doc_id} ({doc_name})")

                for endpoint in PROCESS_TYPES:
                    response = client.post(
                        f"{PROCESS_URL}/{endpoint}",
                        params={"id": doc_id}
                    )

                    if response.is_success:
                        data = response.json()
                        print(f"Processed id={doc_id}, report_id = {data["id"]}")
                        record[endpoint] = data["id"]
                    else:
                        record[endpoint] = None
                        print(
                            endpoint,
                            f"Failed to process id={doc_id} "
                            f"({response.status_code}): {response.text}"
                        )

                with open(OUTPUT_JSONL, "a", encoding="utf-8") as f_out:
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")

    finally:
        client.close()


if __name__ == "__main__":
    main()