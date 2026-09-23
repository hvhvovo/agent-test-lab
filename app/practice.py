"""复盘由用户自评；不以关键词命中伪装语义评分。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class PracticeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    answer: str = Field(min_length=1, max_length=10000)
    covered_points: list[int] = Field(default_factory=list, max_length=10)
    confidence: Literal['需复习', '部分掌握', '能独立解释'] = '需复习'
    notes: str = Field(default='', max_length=3000)
