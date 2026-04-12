import json
import logging
import re
import pymupdf
from pymupdf import Page
from io import BytesIO
from uuid import uuid4
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from types_boto3_s3.client import S3Client
from qdrant_client import AsyncQdrantClient
import httpx
from qdrant_client import models

from app.core.ml_models import ml_models
from app.db.schema import Document, Report
from app.core.s3 import AWS_BUCKET
from app.core.config import config
from app.core.qdrant import collection_name
from app.models.document_models import DocumentStatus
from app.services.report_service import delete_reports, s3_upload_report
from app.services.report_service import process_pager_report, process_pymupdf_full_report
from app.models.report_models import ReportJson, PyMuPdfReportJson, PyMuPdfPage

PRESIGNED_URLS_EXPIRATION_TIME_SECONDS = 3600 # 1 hour

def s3_upload_document(content: bytes, s3_filename: str, s3_mime_type: str, filename: str, s3_client: S3Client, db: Session) -> int:
    logging.info(f"Uploading file {filename}.{s3_mime_type} to s3 {s3_filename}")
    s3_client.upload_fileobj(Fileobj=BytesIO(content), Bucket=AWS_BUCKET, Key=f"documents/{s3_filename}.{s3_mime_type}")
    document = Document(name=filename, status=DocumentStatus.UPLOADED.value, s3_filename=s3_filename, s3_mime_type=s3_mime_type)
    db.add(document)
    db.commit()
    return document.id


async def s3_delete_document(document: Document, qdrant_client: AsyncQdrantClient, s3_client: S3Client, db: Session)  -> None:
    logging.info(f"Starting deleting process for document {document.id}")

    await delete_reports(document, qdrant_client, s3_client, db)

    logging.info(f"Deleting document {document.id} from s3")
    await run_in_threadpool(s3_client.delete_object, Bucket=AWS_BUCKET, Key=f"documents/{document.s3_filename}.{document.s3_mime_type}")
    logging.info(f"Deleting document {document.id} from db")
    await run_in_threadpool(db.delete, document)
    await run_in_threadpool(db.commit)

def s3_get_documents(page: int, page_size: int, s3_client: S3Client, db: Session) -> list[dict[str, str]]:
    logging.info(f"Presigning documents urls")
    query = db.query(Document)

    total_items = query.count()

    documents = (
        query.offset((page-1)*page_size)
        .limit(page_size)
        .all()
    )

    result = []
    for document in documents:
        url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": AWS_BUCKET, 
                "Key": f"documents/{document.s3_filename}.{document.s3_mime_type}",
                "ResponseContentType": "application/pdf",
                "ResponseContentDisposition": "inline"
            },
            ExpiresIn=PRESIGNED_URLS_EXPIRATION_TIME_SECONDS,
        )
        result.append({"id": document.id,"key": f"{document.name}.{document.s3_mime_type}", "status": document.status, "url": url, "reports": document.reports})
        
    return {"page": page, "page_size": page_size, "total_items": total_items, "documents": result}

async def pager_process_document(document: Document, qdrant_client: AsyncQdrantClient, s3_client: S3Client, db: Session):
    logging.info(f"Processing document {document.s3_filename}.{document.s3_mime_type} from s3")
    document.status = DocumentStatus.PROCESSING.value
    await run_in_threadpool(db.commit)
    try:
        files = {
            "file": (
                f"{document.s3_filename}.{document.s3_mime_type}",
                await run_in_threadpool(s3_client.get_object(Bucket=AWS_BUCKET, Key=f"documents/{document.s3_filename}.{document.s3_mime_type}")["Body"].read),
                f"application/{document.s3_mime_type}"
            )
        }

        data = {
            "process": '{"glam_rows": true}'
        }

        logging.info(f"Sending documents {document.s3_filename}.{document.s3_mime_type} to pager")
        
        async with httpx.AsyncClient(timeout=500.0) as client:
            response = await client.post(config.pager_url + "/", data=data, files=files)
            response.raise_for_status()

        report_uuid = uuid4()
        
        report = await run_in_threadpool(s3_upload_report, response.content, "pager", str(report_uuid), document, s3_client, db)

        report_obj = ReportJson.model_validate(response.json())

        # report is not gonna be processed again if something fails, 
        # but it is gonna be created and saved to s3
        logging.info(f"Processing report {report.s3_filename}.json")
        await process_pager_report(report_obj, document.id, report.id, qdrant_client)

        document.status = DocumentStatus.PROCESSED.value
        await run_in_threadpool(db.commit)

        return report.id

    except Exception as e:
        await run_in_threadpool(db.rollback)
        logging.exception(f"Error while processing document {document.s3_filename}.{document.s3_mime_type} from s3 \n {e}")
        document.status = DocumentStatus.PROCESSING_FAILED.value
        await run_in_threadpool(db.commit)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document processing failed"
        )
    

def get_page_text(page: Page, document: Document):
    text = page.get_text(sort=True)
    if not text:
        logging.info(f"Document {document.id}, page {page.number + 1} is an image")
        tp = page.get_textpage_ocr(language="eng")
        text = page.get_text(textpage=tp, sort=True)

    text = re.sub(' +', ' ', text)
    lines = [line for line in text.splitlines() if line.strip()]
    cleaned_text = "\n".join(lines)

    return cleaned_text

async def pymupdf_full_process_document(document: Document, qdrant_client: AsyncQdrantClient, s3_client: S3Client, db: Session):
    logging.info(f"Processing document {document.s3_filename}.{document.s3_mime_type} from s3")
    document.status = DocumentStatus.PROCESSING.value
    await run_in_threadpool(db.commit)
    try:

        file = await run_in_threadpool(s3_client.get_object, Bucket=AWS_BUCKET, Key=f"documents/{document.s3_filename}.{document.s3_mime_type}")

        file_content = await run_in_threadpool(file["Body"].read)

        pymupdf_doc = pymupdf.open(stream=file_content, filetype=document.s3_mime_type)


        pages_data  = []
        for  page in pymupdf_doc:
            page_text = await run_in_threadpool(get_page_text, page, document)
            pages_data.append(PyMuPdfPage(page_number=page.number + 1, content=page_text))

        pymupdf_doc.close()

        report_data = PyMuPdfReportJson(
            document_name=document.s3_filename,
            total_pages=len(pages_data),
            pages=pages_data
        )

        json_bytes = report_data.model_dump_json(indent=2).encode("utf-8")

        report_uuid = uuid4()
        
        report = await run_in_threadpool(s3_upload_report, json_bytes, "pymupdf_full", str(report_uuid), document, s3_client, db)

        logging.info(f"Processing report {report.s3_filename}.json")
        await process_pymupdf_full_report(report_data, document.id, report.id, qdrant_client)

        document.status = DocumentStatus.PROCESSED.value
        await run_in_threadpool(db.commit)

        return report.id

    except Exception as e:
        await run_in_threadpool(db.rollback)
        logging.exception(f"Error while processing document {document.s3_filename}.{document.s3_mime_type} from s3 \n {e}")
        document.status = DocumentStatus.PROCESSING_FAILED.value
        await run_in_threadpool(db.commit)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document processing failed"
        )
    

def get_pages_start_end(document: Document, start: int, end: int, total_pages: int, num_of_images_input: int = 30):
    # All page ids mentioned are based on the order in the raw document.
    # context_start_end: page start/end id of context in qa generation
    # num_of_images_input: the number of input images, 30 images in cut-off paradigm
    # total_pages: total pages in the raw document
    # img_start, img_end: input page start/end id
    raw_start_page, raw_end_page = start, end
    raw_pages_len = raw_end_page - raw_start_page
    img_start = max(0, raw_start_page - (num_of_images_input - raw_pages_len)//2)
    img_end = img_start + num_of_images_input
    if img_end >= total_pages:
        img_end = total_pages
        img_start = max(0, img_end - num_of_images_input)
    logging.info(f"Document {document.id}: start  {start}, end {end}, page number {total_pages}")
    logging.info(f"result is [{img_start}, {img_end}]")
    return img_start, img_end

async def pymupdf_partial_process_document(document: Document, start: int, end: int, qdrant_client: AsyncQdrantClient, s3_client: S3Client, db: Session):
    logging.info(f"Processing document {document.s3_filename}.{document.s3_mime_type} from s3")
    document.status = DocumentStatus.PROCESSING.value
    await run_in_threadpool(db.commit)
    try:

        file = await run_in_threadpool(s3_client.get_object, Bucket=AWS_BUCKET, Key=f"documents/{document.s3_filename}.{document.s3_mime_type}")

        file_content = await run_in_threadpool(file["Body"].read)

        pymupdf_doc = pymupdf.open(stream=file_content, filetype=document.s3_mime_type)

        part_start, part_end = get_pages_start_end(document, start, end, pymupdf_doc.page_count)

        pages_data  = []
        for page in pymupdf_doc.pages(start=part_start, stop=part_end):
            page_text = await run_in_threadpool(get_page_text, page, document)
            pages_data.append(PyMuPdfPage(page_number=page.number + 1, content=page_text))

        report_data = PyMuPdfReportJson(
            document_name=document.s3_filename,
            total_pages=pymupdf_doc.page_count,
            pages=pages_data
        )

        pymupdf_doc.close()

        json_bytes = report_data.model_dump_json(indent=2).encode("utf-8")

        report_uuid = uuid4()
        
        report = await run_in_threadpool(s3_upload_report, json_bytes, "pymupdf_partial", str(report_uuid), document, s3_client, db)

        document.status = DocumentStatus.PROCESSED.value
        await run_in_threadpool(db.commit)

        return report.id

    except Exception as e:
        await run_in_threadpool(db.rollback)
        logging.exception(f"Error while processing document {document.s3_filename}.{document.s3_mime_type} from s3 \n {e}")
        document.status = DocumentStatus.PROCESSING_FAILED.value
        await run_in_threadpool(db.commit)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document processing failed"
        )

async def report_points_based_search(text: str, report_id: int, label: str | None, qdrant_client: AsyncQdrantClient) -> models.QueryResponse:
    logging.info(f"Searching documents with string {text}")

    text = text.replace("-\n", "").replace("\n", " ").lower()
    
    embedding = await run_in_threadpool(ml_models["embedding_model"].encode, text)

    conditions = []
    

    conditions.append(
        models.FieldCondition(
            key="report_id",
            match=models.MatchValue(
                value=report_id,
            ),
        )
    )

    if label is not None:
        conditions.append(
            models.FieldCondition(
                key="label",
                match=models.MatchValue(
                    value=label,
                ),
            )
        )

    filter_condition = models.Filter(
        must=conditions
    )

    result = await qdrant_client.query_points(
        collection_name=collection_name,
        query_filter=filter_condition,
        query=embedding,
        limit=10,
    )

    return result


async def report_based_search(report: Report, s3_client: S3Client) -> str:
    logging.info(f"Assembling text for report {report.id}")

    # text = text.replace("-\n", "").replace("\n", " ").lower()
    file = await run_in_threadpool(s3_client.get_object, Bucket=AWS_BUCKET, Key=f"reports/{report.s3_filename}.json")

    file_content = await run_in_threadpool(file["Body"].read)

    report_obj = PyMuPdfReportJson.model_validate_json(file_content)

    full_text = "\n".join([p.content for p in report_obj.pages])

    return full_text

