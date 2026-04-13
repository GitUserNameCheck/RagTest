import logging
import os
from openai import OpenAI
from fastapi import APIRouter, HTTPException, status, UploadFile
from fastapi.concurrency import run_in_threadpool
from uuid import uuid4

from app.core.config import config
from app.core.ml_models import ml_models
from app.core.s3 import S3Client
from app.core.qdrant import QdrantClient
from app.core.openai import OpenAIClient
from app.services.document_service import s3_get_documents, s3_upload_document, s3_delete_document
from app.services.document_service import report_based_search as service_report_based_search
from app.services.document_service import report_points_based_search as service_report_points_based_search
from app.services.document_service import pager_process_document as service_pager_process_document
from app.services.document_service import pymupdf_full_process_document as service_pymupdf_full_process_document 
from app.services.document_service import pymupdf_partial_process_document as service_pymupdf_partial_process_document 
from app.services.report_service import delete_reports
from app.db.schema import DbSession, Document, Report
from app.models.document_models import DocumentStatus

router = APIRouter(
    prefix="/document"
)

KB = 1024
MB = 1024 * KB

SUPPORTED_FILE_TYPES = {
    "application/pdf": "pdf"
}


@router.post("/upload")
def upload_document(s3_client: S3Client, db: DbSession, file: UploadFile | None = None):

    if not file:
        logging.info(f"No provided file")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No file was provided",
        )
    
    if not 0 < file.size <= 250 * MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported max file size is 250 mb"
        )
    
    content = file.file.read()
    identifier = ml_models["magika"].identify_bytes(content)
    mime_type = identifier.output.mime_type
    filename = os.path.splitext(file.filename)[0]

    if mime_type not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {mime_type}. Supported types are {SUPPORTED_FILE_TYPES}."
        )
    
    document_uuid = uuid4()

    document_id = s3_upload_document(content, str(document_uuid), SUPPORTED_FILE_TYPES[mime_type], filename, s3_client, db)

    return {"message": "file uploaded successfuly", "id": document_id}


@router.post("/delete")
async def delete_document(id: int, qdrant_client: QdrantClient, s3_client: S3Client, db: DbSession):
    document = await run_in_threadpool(lambda: db.query(Document).filter(Document.id == id).first())
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document is being processed"
        )
    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is being processed"
        )

    await s3_delete_document(document, qdrant_client, s3_client, db)

    return {"message": "file successfuly deleted"}

@router.post("/delete_document_reports")
async def delete_document_reports(id: int, qdrant_client: QdrantClient, s3_client: S3Client, db: DbSession):
    document = await run_in_threadpool(lambda: db.query(Document).filter(Document.id == id).first())
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document is being processed"
        )
    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is being processed"
        )

    await delete_reports(document, qdrant_client, s3_client, db)
    
    document.status = DocumentStatus.UPLOADED.value
    await run_in_threadpool(db.commit)

    return {"message": "document report successfuly deleted"}

@router.get("/get")
def get_documents(s3_client: S3Client, db: DbSession, page: int = 1, page_size: int = 20):

    result = s3_get_documents(page, page_size, s3_client, db)

    return result

@router.post("/pager_process")
async def pager_process_document(id: int,  qdrant_client: QdrantClient, s3_client: S3Client,  db: DbSession):
    document = await run_in_threadpool(lambda: db.query(Document).filter(Document.id == id).first())
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document is being processed"
        )
    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already being processed"
        )

    report_id = await service_pager_process_document(document, qdrant_client, s3_client, db)

    return {"message": "document successfuly processed", "id": report_id}


@router.post("/pymupdf_full_process")
async def pymupdf_full_process_document(id: int,  qdrant_client: QdrantClient, s3_client: S3Client,  db: DbSession):
    document = await run_in_threadpool(lambda: db.query(Document).filter(Document.id == id).first())
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document is being processed"
        )
    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already being processed"
        )

    report_id = await service_pymupdf_full_process_document(document, qdrant_client, s3_client, db)

    return {"message": "document successfuly processed", "id": report_id}


@router.post("/pymupdf_partial_process")
async def pymupdf_partial_process_document(id: int, start: int, end: int,  qdrant_client: QdrantClient, s3_client: S3Client,  db: DbSession):
    document = await run_in_threadpool(lambda: db.query(Document).filter(Document.id == id).first())
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document is being processed"
        )
    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already being processed"
        )

    report_id = await service_pymupdf_partial_process_document(document, start, end, qdrant_client, s3_client, db)

    return {"message": "document successfuly processed", "id": report_id}


# [(label, text), (text)]
#https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
@router.get("/report_points_based_search")
async def report_points_based_search(prompt: str, search_text: str, report_id: int, qdrant_client: QdrantClient, open_ai_client: OpenAIClient, label: str | None = None):

    result = await service_report_points_based_search(search_text, report_id, label, qdrant_client)

    documents_fragments = ""
    for scored_point in result.points:
        documents_fragments = documents_fragments + scored_point.payload["text"] + "\n"

    messages = [
        {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
        {"role": "user", "content": prompt + "\n" + search_text + "\n" + documents_fragments}
    ]

    print(prompt + "\n" + search_text + "\n" + documents_fragments)

    response = await open_ai_client.chat.completions.create(
        model=config.open_ai_model_name,
        messages=messages,
        temperature=0
    )

    result = response.choices[0].message.content

    return {"message": result}

@router.get("/report_based_search")
async def report_based_search(prompt: str, search_text: str, report_id: int, s3_client: S3Client, open_ai_client: OpenAIClient, db: DbSession):
    report = await run_in_threadpool(lambda: db.query(Report).filter(Report.id == report_id).first())
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report does not exist"
        )
    
    result = await service_report_based_search(report, s3_client)

    messages = [
        {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
        {"role": "user", "content": prompt + "\n" + search_text + "\n" + result}
    ]

    print(prompt + "\n" + search_text + "\n" + result)

    response = await open_ai_client.chat.completions.create(
        model=config.open_ai_model_name,
        messages=messages,
        temperature=0
    )

    result = response.choices[0].message.content

    return {"message": result}


@router.get("/pure_llm_search")
async def pure_llm_search(prompt: str, search_text: str, open_ai_client: OpenAIClient,):

    messages = [
        {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
        {"role": "user", "content": prompt + "\n" + search_text}
    ]

    print(prompt + "\n" + search_text)

    response = await open_ai_client.chat.completions.create(
        model=config.open_ai_model_name,
        messages=messages,
        temperature=0
    )

    result = response.choices[0].message.content

    return {"message": result}