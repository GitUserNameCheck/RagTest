import json
from openai import OpenAI
import os
from transformers import AutoModelForCausalLM, AutoTokenizer

# INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_partial/PyMuPDFPartialAnswers.jsonl"
# OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_partial/PyMuPDFPartialExtractedAnswers.jsonl"
# INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_full/PyMuPDFFullAnswers.jsonl"
# OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pymupdf_full/PyMuPDFFullExtractedAnswers.jsonl"
# INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/mineru/MineruAnswers.jsonl"
# OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/mineru/MineruExtractedAnswers.jsonl"
# INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pager/PagerAnswers.jsonl"
# OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pager/PagerExtractedAnswers.jsonl"
INPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pure_llm/PureLLMAnswers.jsonl"
OUTPUT_JSONL = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/pure_llm/PureLLMExtractedAnswers.jsonl"
OPENAI_API_KEY = ""
OPENAI_URL = "http://localhost:12434/v1"
OPENAI_MODEL_NAME = "docker.io/ai/qwen2.5:latest"
ANSWER_EXTRACTION_PROMPT = "C:/Users/howto/Downloads/SemanticSearch/RagTestProject/testing/AnswerExtractionPrompt.md"

SYSTEM_PROMPT = (
    "You are an expert in document question answering. Answer the question strictly based on the given document. \n"
)


def load_jsonl(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main():

    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_URL,
        max_retries=1,
    )

    with open(ANSWER_EXTRACTION_PROMPT) as f:
        extraction_prompt = f.read()

    rows = load_jsonl(INPUT_JSONL)

    existing_ids = set()
    if os.path.exists(OUTPUT_JSONL):
        for row in load_jsonl(OUTPUT_JSONL):
            existing_ids.add(row.get("question_id"))

    for row in rows:
        question_id = row.get("question_id")
        if question_id in existing_ids:
            print(f"Skipping existing question {question_id}")
            continue

        question = row.get("question")
        predicted_answer = row.get("predicted_answer")

        messages = [
            {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
            {"role": "user", "content": SYSTEM_PROMPT + extraction_prompt + "\nQuestion: " + question + "\nAnalysis: " + predicted_answer}
        ]

        print("Extracting answer for question " + question_id)

        response = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=messages,
            temperature=0
        )

        result = response.choices[0].message.content

        try:
            import re
            concise_answer = re.findall(r"<concise_answer>(.*?)</concise_answer>", result, re.DOTALL)[0]
            answer_format = re.findall(r"<answer_format>(.*?)</answer_format>", result, re.DOTALL)[0]
        except:
            concise_answer = "Fail to extract"
            answer_format = "None"

        row.setdefault("predicted_concise_answer", concise_answer)
        row.setdefault("predicted_concise_answer_format", answer_format)

        append_jsonl(OUTPUT_JSONL, row)


if __name__ == "__main__":
    main()


