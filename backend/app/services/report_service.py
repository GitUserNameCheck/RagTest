from io import BytesIO
import logging
import pymupdf
from typing import Any, List
from fastapi.concurrency import run_in_threadpool
from uuid import uuid4
from sqlalchemy.orm import Session
from torch import Tensor
from app.core.ml_models import ml_models
from types_boto3_s3.client import S3Client
from qdrant_client import AsyncQdrantClient
from app.db.schema import Document, Report
from app.core.s3 import AWS_BUCKET
from app.core.qdrant import QdrantClient, collection_name
from app.core.config import config
from qdrant_client.http import models
from app.models.report_models import ReportJson, PyMuPdfReportJson
from app.models.mineru_models import AuxiliaryBlock, MinerUReport
from app.utility.report_utility import generate_distinct_colors

def s3_upload_report(content: bytes, report_tag: str, s3_filename: str, document: Document, s3_client: S3Client, db: Session) -> Report:
    logging.info(f"Creating report for document {document.s3_filename}.{document.s3_mime_type} from s3")
    s3_client.upload_fileobj(Fileobj=BytesIO(content), Bucket=AWS_BUCKET, Key=f"reports/{s3_filename}.json")
    report = Report(document_id = document.id, s3_filename = s3_filename, tag=report_tag)
    db.add(report)
    db.commit()
    return report

def s3_upload_report_outline(content: bytes, report_name: str, document_type: str, s3_client: S3Client, db: Session) -> None:
    logging.info(f"Uploading report outline for report {report_name} to s3")
    s3_client.upload_fileobj(Fileobj=BytesIO(content), Bucket=AWS_BUCKET, Key=f"report_outlines/{report_name}.{document_type}")

async def delete_reports(document: Document, qdrant_client: AsyncQdrantClient, s3_client: S3Client, db: Session) -> None:
    await qdrant_delete_reports_points(document, qdrant_client)

    logging.info(f"Deleting reports for {document.id}")
    await run_in_threadpool(s3_delete_reports, document, s3_client, db)

def s3_delete_reports(document: Document, s3_client: S3Client, db: Session) -> Report:
    reports = db.query(Report).filter(Report.document_id == document.id).all()
    for report in reports:
        logging.info(f"Deleting report {report.s3_filename} from s3 for document {report.document_id}")
        s3_client.delete_object(Bucket=AWS_BUCKET, Key=f"reports/{report.s3_filename}.json")
        db.delete(report)
        db.commit()

async def qdrant_delete_reports_points(document: Document, qdrant_client: AsyncQdrantClient):
    filter_condition = models.Filter(
        must=[
            models.FieldCondition(
                key="document_id",
                match=models.MatchValue(
                    value=document.id
                )
            )
        ]
    )

    logging.info(f"Deleting vectors for reports of document {document.id}")
    await qdrant_client.delete(
        collection_name=collection_name,
        points_selector=filter_condition,
        wait=True
    )

def get_texts_and_labels(report: ReportJson) -> tuple[list[str], list[str]]:
    data = []
    labels = []
    seen = set()
    
    for page in report.pages:
        for region in page.regions:
            if region.label == "figure":
                current_data = {
                    "text": region.text,
                    "image": f"data:image/png;base64,{region.base64}"
                }
                seen_key = (current_data["text"], current_data["image"])
            else:
                current_data = region.text
                seen_key = region.text

            if seen_key not in seen:
                seen.add(seen_key)
                data.append(current_data)
                labels.append(region.label)

    return data, labels


def get_points(data: list[Any], labels: list[str], embeddings: Tensor, document_id: int, report_id: int) -> list[models.PointStruct]:
    points = []
    for element, label, embedding in zip(data, labels, embeddings):
        if isinstance(element, str) and len(element) == 0:
            continue
        points.append(
            models.PointStruct(
                id = uuid4(),
                vector = embedding[:512],
                payload = {
                    "document_id": document_id,
                    "report_id": report_id,
                    "label": label,
                    "data": element
                }
            )
        )
            
    return points

async def process_pager_report(report: ReportJson, document_id: int, report_id: int, qdrant_client: QdrantClient) -> None:


    data, labels = await run_in_threadpool(get_texts_and_labels, report)

    embeddings = await run_in_threadpool(ml_models["embedding_model"].encode, data)

    points = await run_in_threadpool(get_points, data, labels, embeddings, document_id, report_id)

    if len(points) > 0:
        await qdrant_client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True
        )

def chunk_document(report: PyMuPdfReportJson) -> List[str]:
    chunks = []
    
    full_text = " ".join([p.content for p in report.pages])
    
    full_text = full_text.replace("-\n", "").replace("\n", " ")

    if config.embedding_text_size <= 0:
        raise Exception("Embedding text size is less than 0")
    if config.embedding_text_overlap <= 0:
        raise Exception("Overlap text size is less than 0")
    if config.embedding_text_overlap >= config.embedding_text_size:
        raise Exception("Overlap is greater than text size")

    start = 0
    while start < len(full_text):
        end = start + config.embedding_text_size
        chunk = full_text[start:end]
        chunks.append(chunk)
        
        # Сдвигаемся на размер чанка минус перекрытие
        start += (config.embedding_text_size - config.embedding_text_overlap)      
            
    return chunks

async def process_pymupdf_full_report(report: PyMuPdfReportJson, document_id: int, report_id: int, qdrant_client: QdrantClient) -> None:

    texts = await run_in_threadpool(chunk_document, report)

    embeddings = await run_in_threadpool(ml_models["embedding_model"].encode, texts)

    points = await run_in_threadpool(get_points, texts, [None] * len(texts), embeddings, document_id, report_id)

    await qdrant_client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True
    )

def mineru_get_texts_and_labels(report: MinerUReport):
    blocks = report.content_list
    texts = []
    labels = []

    for block in blocks:
        def join_existing(*parts):
            valid_parts = []
            for p in parts:
                if isinstance(p, list):
                    joined_list = "\n".join(filter(None, p))
                    if joined_list: valid_parts.append(joined_list)
                elif p:
                    valid_parts.append(str(p))
            return "\n".join(valid_parts)

        content = ""
        
        if block.type in ["text", "seal", "equation"] or isinstance(block, AuxiliaryBlock):
            content = block.text
            
        elif block.type == "image":
            content = join_existing(block.image_caption, block.image_footnote)
            
        elif block.type == "table":
            content = join_existing(block.table_caption, block.table_body, block.table_footnote)
            
        elif block.type == "chart":
            content = join_existing(block.chart_caption, block.content, block.chart_footnote)
            
        elif block.type == "code":
            content = join_existing(block.code_caption, block.code_body, block.code_footnote)
            
        elif block.type == "list":
            content = "\n".join(filter(None, block.list_items))

        if content:
            texts.append(content)
            labels.append(block.type)

    return texts, labels



async def process_mineru_report(report: MinerUReport, document_id: int, report_id: int, qdrant_client: QdrantClient) -> None:

    texts, labels = await run_in_threadpool(mineru_get_texts_and_labels, report)

    # result = "".join([f"\n\n{labels[i]}\nSTART\n{el}\nEND\n\n" for i, el in enumerate(texts)])
    # print(result)

    # print(len(texts), len(labels))

    embeddings = await run_in_threadpool(ml_models["embedding_model"].encode, texts)

    points = await run_in_threadpool(get_points, texts, labels, embeddings, document_id, report_id)

    await qdrant_client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True
    )


BORDER_WIDTH = 1
FILL_OPACITY = 0.15
FONT_SIZE = 9

def outline_pager_report(report: ReportJson, report_name: str, document_obj: id, document_type) -> bytes:

    unique_labels = sorted({
        region.label
        for page in report.pages
        for region in page.regions
    })

    generated_colors = generate_distinct_colors(len(unique_labels))

    label_colors = {
        label: generated_colors[i]
        for i, label in enumerate(unique_labels)
    }

    document = pymupdf.open(stream=document_obj, filetype=document_type)

    for page in report.pages:
        page_number = page.number

        if page_number >= len(document):
            logging.info(f"Skipping page {page_number}: page not found in PDF, report {report_name}")
            continue

        document_page = document[page_number]

        for region in page.regions:
            segment = region.segment

            x = segment.x_top_left
            y = segment.y_top_left
            w = segment.width
            h = segment.height

            label = region.label
            color = label_colors[label]

            rect = pymupdf.Rect(x, y, x + w, y + h)

            document_page.draw_rect(
                rect,
                color=color,
                fill=color,
                fill_opacity=FILL_OPACITY,
                width=BORDER_WIDTH
            )

            text_width = pymupdf.get_text_length(label, fontsize=FONT_SIZE)
            text_height = FONT_SIZE
            padding = 3

            rect_x0 = x
            rect_y0 = y - text_height - (padding * 2)
            rect_x1 = rect_x0 + text_width + (padding * 2)
            rect_y1 = y

            rect = pymupdf.Rect(rect_x0, rect_y0, rect_x1, rect_y1)

            document_page.draw_rect(
                rect,
                color=color,
                fill=color,
                fill_opacity=1,
                width=1,
            )

            text_x = rect_x0 + padding
            text_y = rect_y1 - padding - 1

            document_page.insert_text(
                (text_x, text_y),
                label,
                fontsize=FONT_SIZE,
                color=(0, 0, 0),
            )

    updated_document_obj = document.tobytes(incremental=False)
    document.close()

    return updated_document_obj