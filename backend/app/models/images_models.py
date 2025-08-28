from pydantic import BaseModel, Field
from typing import Union, Optional, List, Literal
from enum import Enum   
from pydantic import BaseModel

class DataPoint(BaseModel):
    label: Union[str, float, int] = Field(..., description="X-axis label or category")
    value: Optional[Union[float, int]] = Field(None, description="Y-axis value or proportion")


class ChartSeries(BaseModel):
    name: Optional[str] = Field(None, description="Legend or series name")
    data: List[DataPoint]


class ChartContent(BaseModel):
    chart_type: Literal[
        "bar", "line", "pie", "scatter", "box", "area", "histogram",
        "heatmap", "bubble", "radar", "gantt", "waterfall", "funnel", "treemap"
    ]
    title: Optional[str] = None
    series: List[ChartSeries]
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    notes: Optional[str] = None

# class ChartDataPoint(BaseModel):
#     label: str
#     value: Union[int, float, str]




class TableRow(BaseModel):
    columns: List[str]  # raw row as list of columns


class DiagramEntity(BaseModel):
    id: str
    label: str
    type: str
    connected_to: List[str]  # list of entity ids


class ImageData(BaseModel):
    chart_data: Optional[List[ChartContent]] = Field(
        default=None,
        description=(
            "If the image is a chart, extract its data as a list of charts.\n"
            "Format: {chart_type: 'bar', title: ..., series: [{name: ..., data: [{label: ..., value: ...}]}]}"
        )
    )
    table_data: Optional[List[dict]] = Field(
        default=None,
        description="If the image is a table, extract rows as a list of dictionaries."
    )

class ImageType(str, Enum):
    CHART = "chart"
    DIAGRAM = "diagram"
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"

class ImageAnalysisResult(BaseModel):
    image_summary:str = Field(description="A short human-readable summary of what the image is showing. Include all the information in the image.")
    image_type: ImageType
    # image_relevance: RelevanceScore
    image_data: ImageData = Field(description=("Images data "))
    
    
