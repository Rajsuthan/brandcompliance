from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FeedbackBase(BaseModel):
    user_id: str
    content: str


class FeedbackCreate(FeedbackBase):
    pass


class Feedback(FeedbackBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
