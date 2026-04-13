import json
from typing import Annotated, List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator

class BaseBlock(BaseModel):
    type: str
    bbox: List[int]
    page_idx: int

class TextBlock(BaseBlock):
    type: Literal["text"]
    text: str
    text_level: Optional[int] = None

class AuxiliaryBlock(BaseBlock):
    type: Literal["header", "footer", "page_number", "aside_text", "page_footnote"]
    text: str

class ImageBlock(BaseBlock):
    type: Literal["image"]
    img_path: str
    image_caption: List[str]
    image_footnote: List[str]

class TableBlock(BaseBlock):
    type: Literal["table"]
    img_path: str
    table_caption: List[str]
    table_footnote: List[str]
    table_body: Optional[str] = None  # HTML

class ChartBlock(BaseBlock):
    type: Literal["chart"]
    img_path: str
    content: str
    chart_caption: List[str]
    chart_footnote: List[str]

class EquationBlock(BaseBlock):
    type: Literal["equation"]
    img_path: str
    text: Optional[str] = None
    text_format: Optional[str] = None

class CodeBlock(BaseBlock):
    type: Literal["code"]
    sub_type: str
    code_caption: List[str]
    code_footnote: List[str]
    code_body: str

class ListBlock(BaseBlock):
    type: Literal["list"]
    sub_type: str
    list_items: List[str]

class SealBlock(BaseBlock):
    type: Literal["seal"]
    img_path: str
    text: str

Block = Annotated[
    Union[
        TextBlock,
        AuxiliaryBlock,
        ImageBlock,
        TableBlock,
        ChartBlock,
        EquationBlock,
        CodeBlock,
        ListBlock,
        SealBlock
    ],
    Field(discriminator="type")
]


class MinerUReport(BaseModel):
    content_list: List[Block]

    @field_validator("content_list", mode="before")
    @classmethod
    def parse_json_string(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v