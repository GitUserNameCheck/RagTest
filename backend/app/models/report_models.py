from typing import List
from pydantic import BaseModel


class Annotations(BaseModel):
    is_italic: bool
    metadata: str
    x_top_left: int
    font_size: int
    start: int
    url: str
    is_bold: bool
    font_name: str
    is_normal: bool
    y_top_left: int
    width: int
    end: int
    text: str
    height: int


class Block(BaseModel):
    x_top_left: int
    metadata: str
    spacing: int
    y_top_left: int
    indent: int
    width: int
    start: int
    annotations: List[Annotations]
    end: int
    text: str
    order: int
    height: int

class Region(BaseModel):
    x_top_left: int
    y_top_left: int
    width: int
    height: int
    text: str
    label: str

class Image(BaseModel):
    x_top_left: int
    y_top_left: int
    original_name: str
    width: int
    page_num: int
    tmp_file_path: str
    uuid: str
    height: int

class CellBlock(BaseModel):
    x_top_left: int
    y_top_left: int
    width: int
    start: int
    end: int
    height: int

class RowItem(BaseModel):
    cell_blocks: List[CellBlock]
    text: str

class CellPropertyItem(BaseModel):
    row_span: int
    invisible: int
    col_span: int

class Table(BaseModel):
    x_top_left: int
    y_top_left: int
    width: int
    rows: List[List[RowItem]]
    height: int
    order: int
    cell_properties: List[List[CellPropertyItem]]

class Page(BaseModel):
    number: int
    tables: List[Table]
    images: List[Image]
    blocks: List[Block]
    width: float
    height: float
    regions: List[Region]

class ReportJson(BaseModel):
    pages: List[Page]


class PyMuPdfPage(BaseModel):
    page_number: int
    content: str

class PyMuPdfReportJson(BaseModel):
    document_name: str
    total_pages: int
    pages: List[PyMuPdfPage]

