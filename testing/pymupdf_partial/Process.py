import json
import httpx

INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/Process.jsonl"   # output from previous script
OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_partial/ProcessedPyMuPDFPartial.jsonl"
PROCESS_URL = "http://localhost:5001/api/document"
PROCESS_TYPE = "pymupdf_partial_process"

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
                doc_start_end = record.get("start_end_idx")
                start, end = doc_start_end[0], doc_start_end[1]

                print(f"Processing document id={doc_id} ({doc_name})")


                response = client.post(
                    f"{PROCESS_URL}/{PROCESS_TYPE}",
                    params={"id": doc_id, "start": start, "end": end}
                )

                if response.is_success:
                    data = response.json()
                    print(f"Processed id={doc_id}, report_id = {data["id"]}")
                    record[PROCESS_TYPE] = data["id"]
                else:
                    record[PROCESS_TYPE] = None
                    print(
                        PROCESS_TYPE,
                        f"Failed to process id={doc_id} "
                        f"({response.status_code}): {response.text}"
                    )

                with open(OUTPUT_JSONL, "a", encoding="utf-8") as f_out:
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")

    finally:
        client.close()


if __name__ == "__main__":
    main()