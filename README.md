# RAG testing

This repository provides a framework for evaluating and comparing different retrieval strategies for RAG systems, using the [LongDocURL](https://github.com/dengc2023/LongDocURL) benchmark

The primary goal is to analyze how different document parsing and retrieval methods impact the quality of LLM responses on documents.

## Tested Strategies

- Questioning without any retrieved data.
- Questioning using cut-off paradigm from LongDocURL.
- Questioning using [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/) based RAG algorithm.
- Questioning using [MinerU](https://github.com/opendatalab/mineru) based RAG algorithm.

## Dependencies & Versions

- MinerU: v3.0.4.
- Tesseract OCR: v5.5.0.20241111 (System dependency).
- Python: 3.13.7.
- Full Python environment details can be found in requirements.txt.
- Embeddings Model: [distiluse-base-multilingual-cased-v1](https://huggingface.co/sentence-transformers/distiluse-base-multilingual-cased-v1).
