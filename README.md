# RAG testing

This repository provides a framework for evaluating and comparing different retrieval strategies for RAG systems, using the [LongDocURL](https://github.com/dengc2023/LongDocURL) benchmark

The primary goal is to analyze how different document parsing and retrieval methods impact the quality of LLM responses on documents.

## Tested Strategies

- Questioning without any retrieved data.

![PureLLM](evaluation/images/PureLLM.jpg)

- Questioning using cut-off paradigm from [LongDocURL](https://github.com/dengc2023/LongDocURL).

![PyMuPDFPartial](evaluation/images/PyMuPDFPartial.jpg)

- Questioning using [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/) based classic RAG algorithm with 500 chunk size and 100 overlap.

![PyMuPDFFull](evaluation/images/PyMuPDFFull.jpg)

- Questioning using [MinerU](https://github.com/opendatalab/mineru) based RAG algorithm.

![MinerU](evaluation/images/MinerU.jpg)

- Questioning using [PageR](Pager) based RAG algorithm.

![PageR](evaluation/images/PageR.jpg)

## Dependencies & Versions

- MinerU: v3.0.4.
- Tesseract OCR: v5.5.0.20241111 (System dependency).
- Python: 3.13.7.
- Full Python dependency list can be found in requirements.txt and mineru_requirements.txt.
- Embedding Model: [Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B).
- Reranker Model: [Qwen3-VL-Reranker-2B](https://huggingface.co/Qwen/Qwen3-VL-Reranker-2B).
- Model used for questioning is [Qwen3.5-9B-Q6_K.gguf](https://huggingface.co/lmstudio-community/Qwen3.5-9B-GGUF/tree/main) hosted in LM Studio.
