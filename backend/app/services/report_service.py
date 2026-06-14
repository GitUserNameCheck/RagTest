import asyncio
import gc
from io import BytesIO
import json
import logging
from pathlib import Path
import random
import pymupdf
from typing import Any, Union
from PIL.Image import Image as PILImage
from fastapi.concurrency import run_in_threadpool
from markdownify import markdownify as md
from uuid import uuid4
from sqlalchemy.orm import Session
from torch import Tensor
import torch
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
from app.utility.report_utility import generate_distinct_colors, get_aspect_ratio_from_base64

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
        if report.tag in ["mineru", "pager"]:
            s3_client.delete_object(Bucket=AWS_BUCKET, Key=f"report_outlines/{report.s3_filename}.{document.s3_mime_type}")
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

def pager_get_data(report: ReportJson):
    data = []
    embedding_data = []
    labels = []
    seen = set()
    
    for page in report.pages:
        for region in page.regions:
            content = []
            if region.label == "figure":
                image_base64 = f"data:image/png;base64,{region.base64}"
                if get_aspect_ratio_from_base64(image_base64) >= 200:
                    continue
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_base64
                    },
                })
                if region.text:
                    content.append({"type": "text", "text": region.text})
            else:
                content.append({"type": "text", "text": region.text})
        
            seen_key = json.dumps(content, sort_keys=True)

            if seen_key not in seen:
                seen.add(seen_key)
                data.append(content)
                embedding_data.append({
                    "role": "user",
                    "content": content
                })
                labels.append(region.label)

    return data, embedding_data, labels


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

    data, embedding_data, labels = await run_in_threadpool(pager_get_data, report)

    with torch.inference_mode():
        embeddings = await run_in_threadpool(ml_models["embedding_model"].encode, embedding_data, batch_size=1)

    points = await run_in_threadpool(get_points, data, labels, embeddings, document_id, report_id)

    if len(points) > 0:
        await qdrant_client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True
        )

    del embeddings
    gc.collect()
    torch.cuda.empty_cache()

def pymupdf_get_data(report: PyMuPdfReportJson):
    data, embedding_data = [], []
    
    full_text = " ".join([p.text for p in report.pages])
    
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
        content = [
            {"type": "text", "text": chunk}
        ]
        data.append(content)
        embedding_data.append({
            "role": "user",
            "content": content
        })
        
        start += (config.embedding_text_size - config.embedding_text_overlap)      

    seen = set()
    for page in report.pages:
        for image in page.images:
            seen_key = image
            if seen_key not in seen:
                seen.add(seen_key)
                content = [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image
                        },
                    }
                ]
                data.append(content)
                embedding_data.append({
                    "role": "user",
                    "content": content
                })

    return data, embedding_data

async def process_pymupdf_full_report(report: PyMuPdfReportJson, document_id: int, report_id: int, qdrant_client: QdrantClient) -> None:

    data, embedding_data = await run_in_threadpool(pymupdf_get_data, report)

    with torch.inference_mode():
        embeddings = await run_in_threadpool(ml_models["embedding_model"].encode, embedding_data, batch_size=1)

    # embeddings = []

    # for element in embedding_data:
    #     embeddings.append(ml_models["embedding_model"].encode(element))

    points = await run_in_threadpool(get_points, data, [None] * len(data), embeddings, document_id, report_id)

    if len(points) > 0:
        await qdrant_client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True
        )

    del embeddings
    gc.collect()
    torch.cuda.empty_cache()

def mineru_get_data(report: MinerUReport):
    blocks = report.content_list
    images = report.images
    data = []
    embedding_data = []
    labels = []

    seen = set()
    for block in blocks:
        def convert(list):
            content_list = []
            for item in list:
                content_list.append({"type": "text", "text": item})
            return content_list
        def append_image(path, images, content):
            name = Path(path).name
            base64 = images[name]
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": base64
                },
            })


        content = []
        
        if block.type == "text" or isinstance(block, AuxiliaryBlock):
            if block.text:
                content.append({"type": "text", "text": block.text})   

        elif block.type == "image":
            if block.image_caption:
                image_caption = convert(block.image_caption)
                content.extend(image_caption)

            if block.img_path:
                append_image(block.img_path, images, content)
            
            if block.image_footnote:
                image_footnote = convert(block.image_footnote)
                content.extend(image_footnote)
            
        elif block.type == "table":
            if block.table_caption:
                table_caption = convert(block.table_caption)
                content.extend(table_caption)
            
            if block.img_path:
                append_image(block.img_path, images, content)

            if block.table_body:
                md_body = md(block.table_body)
                content.append({"type": "text", "text": md_body})

            if block.table_footnote:
                table_footnote = convert(block.table_footnote)
                content.extend(table_footnote)


        elif block.type == "chart":
            if block.chart_caption:
                chart_caption = convert(block.chart_caption)
                content.extend(chart_caption)
            
            if block.img_path:
                append_image(block.img_path, images, content)

            if block.content:
                content.append({"type": "text", "text": block.content})   

            if block.chart_footnote:
                chart_footnote = convert(block.chart_footnote)
                content.extend(chart_footnote)

        elif block.type == "equation":
            if block.img_path:
                append_image(block.img_path, images, content)

            if block.text:
                content.append({"type": "text", "text": block.text})   


        elif block.type == "code":
            if block.code_caption:
                code_caption = convert(block.code_caption)
                content.extend(code_caption)
            
            if block.code_body:
                content.append({"type": "text", "text": block.code_body})   

            if block.code_footnote:
                code_footnote = convert(block.code_footnote)
                content.extend(code_footnote)


        elif block.type == "list":
            if block.list_items:
                list_items = convert(block.list_items)
                content.extend(list_items)

        elif block.type == "seal":
            if block.img_path:
                append_image(block.img_path, images, content)

            if block.text:
                content.append({"type": "text", "text": block.text})   

        if content:
            seen_key = json.dumps(content, sort_keys=True)

            if seen_key not in seen:
                seen.add(seen_key)
                data.append(content)
                embedding_data.append(
                    {
                        "role": "user",
                        "content": content
                    }
                )
                labels.append(block.type)

    return data, embedding_data, labels



async def process_mineru_report(report: MinerUReport, document_id: int, report_id: int, qdrant_client: QdrantClient) -> None:

    data, embedding_data, labels = await run_in_threadpool(mineru_get_data, report)

    with torch.inference_mode():
        embeddings = await run_in_threadpool(ml_models["embedding_model"].encode, embedding_data, batch_size=1)

    points = await run_in_threadpool(get_points, data, labels, embeddings, document_id, report_id)

    await qdrant_client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True
    )

    del embeddings
    gc.collect()
    torch.cuda.empty_cache()


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

        shape = document_page.new_shape()

        for region in page.regions:
            segment = region.segment

            x = segment.x_top_left
            y = segment.y_top_left
            w = segment.width
            h = segment.height

            label = region.label
            color = label_colors[label]

            rect = pymupdf.Rect(x, y, x + w, y + h)

            shape.draw_rect(rect)

            shape.finish(
                color=color,
                fill=color,
                fill_opacity=0.15,
                width=1,
            )

            text_width = pymupdf.get_text_length(label, fontsize=FONT_SIZE)
            text_height = FONT_SIZE
            padding = 3

            rect_x0 = x
            rect_y0 = y - text_height - (padding * 2)
            rect_x1 = rect_x0 + text_width + (padding * 2)
            rect_y1 = y

            rect = pymupdf.Rect(rect_x0, rect_y0, rect_x1, rect_y1)

            shape.draw_rect(rect)

            shape.finish(
                color=color,
                fill=color,
                fill_opacity=1.0,
                width=1,
            )

            text_x = rect_x0 + padding
            text_y = rect_y1 - padding - 1

            shape.insert_text(
                (text_x, text_y),
                label,
                fontsize=FONT_SIZE,
                color=(0, 0, 0),
            )

        shape.commit(overlay=True)

    updated_document_obj = document.tobytes(incremental=False)
    document.close()

    return updated_document_obj

def outline_mineru_report(report: MinerUReport, report_name: str, document_obj: id, document_type) -> bytes:

    pages_data = json.loads(report.model_output)

    unique_labels = sorted({
        item.get("label", "unknown")
        for page in pages_data
        for item in page.get("layout_dets", [])
    })

    generated_colors = generate_distinct_colors(len(unique_labels))

    label_colors = {
        label: generated_colors[i]
        for i, label in enumerate(unique_labels)
    }

    document = pymupdf.open(stream=document_obj, filetype=document_type)

    for page_data in pages_data:

        page_info = page_data["page_info"]

        page_number = page_info["page_no"]

        if page_number >= len(document):
            logging.info(f"Skipping page {page_number}: page not found in PDF, report {report_name}")
            continue

        page = document[page_number]

        source_width = page_info["width"]
        source_height = page_info["height"]

        pdf_width = page.rect.width
        pdf_height = page.rect.height

        scale_x = pdf_width / source_width
        scale_y = pdf_height / source_height

        shape = page.new_shape()

        for item in page_data.get("layout_dets", []):

            label = item.get("label")

            if label == "ocr_text":
                continue

            bbox = item.get("bbox")

            if not bbox or len(bbox) != 4:
                continue

            x0, y0, x1, y1 = bbox

            x0 *= scale_x
            x1 *= scale_x
            y0 *= scale_y
            y1 *= scale_y

            rect = pymupdf.Rect(x0, y0, x1, y1)

            shape.draw_rect(rect)

            color = label_colors[label]

            shape.finish(
                color=color,
                fill=color,
                fill_opacity=0.15,
                width=1,
            )

            text_width = pymupdf.get_text_length(label, fontsize=FONT_SIZE)
            text_height = FONT_SIZE
            padding = 3

            rect_x0 = x0
            rect_y0 = y0 - text_height - (padding * 2)
            rect_x1 = rect_x0 + text_width + (padding * 2)
            rect_y1 = y0

            rect = pymupdf.Rect(rect_x0, rect_y0, rect_x1, rect_y1)

            shape.draw_rect(rect)

            shape.finish(
                color=color,
                fill=color,
                fill_opacity=1,
                width=1,
            )

            text_x = rect_x0 + padding
            text_y = rect_y1 - padding - 1

            shape.insert_text(
                (text_x, text_y),
                label,
                fontsize=FONT_SIZE,
                color=(0, 0, 0),
            )

        shape.commit(overlay=True)

    updated_document_obj = document.tobytes(incremental=False)
    document.close()

    return updated_document_obj