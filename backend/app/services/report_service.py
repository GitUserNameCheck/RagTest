from io import BytesIO
import logging
from typing import List
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

def s3_upload_report(content: bytes, report_tag: str, s3_filename: str, document: Document, s3_client: S3Client, db: Session) -> Report:
    logging.info(f"Creating report for document {document.s3_filename}.{document.s3_mime_type} from s3")
    s3_client.upload_fileobj(Fileobj=BytesIO(content), Bucket=AWS_BUCKET, Key=f"reports/{s3_filename}.json")
    report = Report(document_id = document.id, s3_filename = s3_filename, tag=report_tag)
    db.add(report)
    db.commit()
    return report


async def delete_reports(document: Document, qdrant_client: AsyncQdrantClient, s3_client: S3Client, db: Session):
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
    texts = []
    labels = []
    
    for page in report.pages:
        for region in page.regions:
            texts.append(region.text.replace("-\n", "").replace("\n", " ").lower())
            labels.append(region.label)

    return texts, labels


def get_points(texts: list[str], labels: list[str], embeddings: Tensor, document_id: int, report_id: int) -> list[models.PointStruct]:
    points = []
    for text, label, embedding in zip(texts, labels, embeddings):
        if len(text) > 0:
            points.append(
                models.PointStruct(
                    id = uuid4(),
                    vector = embedding,
                    payload = {
                        "document_id": document_id,
                        "report_id": report_id,
                        "label": label,
                        "text": text
                    }
                )
            )
            
    return points

async def process_pager_report(report: ReportJson, document_id: int, report_id: int, qdrant_client: QdrantClient) -> None:


    texts, labels = await run_in_threadpool(get_texts_and_labels, report)

    embeddings = await run_in_threadpool(ml_models["embedding_model"].encode, texts)

    points = await run_in_threadpool(get_points, texts, labels, embeddings, document_id, report_id)

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