from typing import List, Optional, Any
from pydantic import BaseModel


class Segment(BaseModel):
    x_top_left: int
    y_top_left: int
    height: int
    width: int

class Region(BaseModel):
    segment: Segment
    rows: Optional[Any] = None
    text: str
    label: str
    base64: Optional[str] = None

class Page(BaseModel):
    regions: List[Region]
    number: int
    width: float
    height: float

class ReportJson(BaseModel):
    pages: List[Page]


class PyMuPdfPage(BaseModel):
    page_number: int
    content: str

class PyMuPdfReportJson(BaseModel):
    document_name: str
    total_pages: int
    pages: List[PyMuPdfPage]

