import json
import os
import httpx

JSONL_PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/FilteredQuestions.jsonl"
NEW_PDF_BASE_PATH = "C:/Users/howto/Downloads/SemanticSearch/LongDocUrlDataset"  # everything before 'ccpdf_zip' is replaced with this
UPLOAD_URL = "http://localhost:5001/api/document/upload"
OUTPUT_JSONL_PATH = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/UploadedDocuments.jsonl"

def rewrite_pdf_path(original_path: str, new_base: str) -> str:
    marker = "ccpdf_zip"
    if marker not in original_path:
        raise ValueError(f"'ccpdf_zip' not found in path: {original_path}")

    suffix = original_path.split(marker, 1)[1]
    
    sub_parts = suffix.split("/")

    filename = os.path.basename(original_path)
    sub_folder = filename[:4]

    return new_base + "/" + marker + "/" + sub_parts[1] + "/" + sub_folder + "/" + sub_parts[2]

def main():

    data = []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_num}") from e


    uploaded_docs = {}

    client = httpx.Client(
        timeout=None,
    )

    try:
        for item in data:
            original_pdf_path = item.get("pdf_path")
            if not original_pdf_path:
                continue

            try:
                resolved_pdf_path = rewrite_pdf_path(
                    original_pdf_path, NEW_PDF_BASE_PATH
                )
            except ValueError as e:
                print(f"Skipping entry: {e}")
                continue

            if resolved_pdf_path in uploaded_docs:
                continue

            if not os.path.exists(resolved_pdf_path):
                print(f"File not found: {resolved_pdf_path}")
                continue

            print(f"Uploading: {resolved_pdf_path}")

            with open(resolved_pdf_path, "rb") as f:
                files = {"file": (os.path.basename(resolved_pdf_path), f, "application/pdf")}
                response = client.post(UPLOAD_URL, files=files)

            if not response.is_success:
                print(f"Upload failed {response.status_code}: {response.text}")
                continue

            resp_json = response.json()
            if "id" not in resp_json:
                print(f"Unexpected response format: {resp_json}")
                continue

            uploaded_docs[resolved_pdf_path] = resp_json["id"]
            print(f"Uploaded with id={resp_json['id']}")

    finally:
        client.close()


    with open(OUTPUT_JSONL_PATH, "w", encoding="utf-8") as f:
        for path, doc_id in uploaded_docs.items():
            record = {
                "path": path,
                "id": doc_id,
                "name": os.path.basename(path),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"JSONL written to: {OUTPUT_JSONL_PATH}")
    print(f"Total unique documents uploaded: {len(uploaded_docs)}")



if __name__ == "__main__":
    main()