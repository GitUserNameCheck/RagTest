# RAG testing

This repository provides a framework for evaluating and comparing different retrieval strategies for RAG systems, using the [LongDocURL](https://github.com/dengc2023/LongDocURL) benchmark

The primary goal is to analyze how different document parsing methods impact the quality of LLM responses on documents.

## Tested Strategies

- Questioning using [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/) based classic RAG algorithm with 500 chunk size and 100 overlap.

- Questioning using [MinerU](https://github.com/opendatalab/mineru) based RAG algorithm.

- Questioning using [PageR](Pager) based RAG algorithm.

## Results

### Overall Results

| Category           | MinerU |  Pager |    PyMuPDF | Number of Questions |
| :----------------- | :----: | :----: | :--------: | :-----------------: |
| Understanding      | 51.40% | 50.60% | **57.41%** |                1243 |
| Reasoning          | 46.51% | 39.59% | **48.92%** |                 387 |
| Locating           | 25.24% | 24.95% | **29.44%** |                 695 |
| **All Categories** | 42.76% | 41.10% | **47.64%** |                2325 |

### Results for Understanding Subcategories

| Subcategory             | MinerU |      Pager |    PyMuPDF | Number of Questions |
| :---------------------- | :----: | :--------: | :--------: | :-----------------: |
| MP_Figure_Understanding | 50.24% | **54.97%** |     54.51% |                 174 |
| MP_Layout_Understanding | 47.50% |     44.22% | **52.32%** |                 172 |
| MP_Table_Understanding  | 44.44% |     45.67% | **51.87%** |                 115 |
| MP_Text_Understanding   | 54.07% |     54.94% | **59.95%** |                 443 |
| SP_Figure_Understanding | 60.44% |     49.55% | **62.69%** |                  94 |
| SP_Layout_Understanding | 41.87% |     45.59% | **56.57%** |                  91 |
| SP_Table_Understanding  | 53.54% |     47.85% | **59.44%** |                 263 |
| SP_Text_Understanding   | 51.25% |     52.21% | **57.03%** |                 259 |

### Results for Reasoning Subcategories

| Subcategory         |     MinerU |      Pager |    PyMuPDF | Number of Questions |
| :------------------ | :--------: | :--------: | :--------: | :-----------------: |
| MP_Figure_Reasoning |     43.29% |     37.35% | **44.41%** |                  85 |
| MP_Layout_Reasoning |     27.50% |     37.50% | **42.50%** |                  40 |
| MP_Table_Reasoning  | **35.67%** |     28.66% |     35.38% |                  69 |
| MP_Text_Reasoning   |     48.46% |     43.24% | **52.81%** |                 115 |
| SP_Figure_Reasoning |     50.00% |     46.43% | **53.57%** |                  28 |
| SP_Layout_Reasoning |     58.30% | **73.11%** |     58.33% |                  12 |
| SP_Table_Reasoning  |     55.99% |     40.82% | **56.12%** |                  98 |
| SP_Text_Reasoning   | **51.41%** |     43.82% |     45.00% |                  40 |

### Results for Locating Subcategories

| Subcategory           |     MinerU |  Pager |    PyMuPDF | Number of Questions |
| :-------------------- | :--------: | :----: | :--------: | :-----------------: |
| Cross_Table_Locating  | **23.00%** | 16.00% |     16.87% |                 126 |
| Cross_Title_Locating  |     36.35% | 34.75% | **36.40%** |                 201 |
| Figure_Table_Locating |      9.65% | 17.17% | **17.34%** |                 231 |
| Para_Title_Locating   |     37.30% | 31.93% | **51.21%** |                 137 |


## Dependencies & Versions

- MinerU: v3.0.4.
- Tesseract OCR: v5.5.0.20241111 (System dependency).
- Python: 3.13.7.
- Full Python dependency list can be found in requirements.txt and mineru_requirements.txt.
- Embedding Model: [Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B).
- Reranker Model: [Qwen3-VL-Reranker-2B](https://huggingface.co/Qwen/Qwen3-VL-Reranker-2B).
- Model used for questioning is [Qwen3.5-9B-Q6_K.gguf](https://huggingface.co/lmstudio-community/Qwen3.5-9B-GGUF/tree/main) hosted in LM Studio.
