from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class BrandGuidelineBase(BaseModel):
    """Base model for brand guideline files"""

    filename: str
    user_id: str
    brand_name: str
    total_pages: Optional[int] = None
    description: Optional[str] = None


class BrandGuidelineCreate(BrandGuidelineBase):
    """Model for creating a brand guideline record"""

    pass


class BrandGuideline(BrandGuidelineBase):
    """Model for a brand guideline with ID"""

    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BrandGuidelinePageBase(BaseModel):
    """Base model for brand guideline pages"""

    guideline_id: str
    page_number: int
    width: int
    height: int
    format: str


class BrandGuidelinePageCreate(BrandGuidelinePageBase):
    """Model for creating a brand guideline page record"""

    base64: str


class BrandGuidelinePage(BrandGuidelinePageBase):
    """Model for a brand guideline page with ID"""

    id: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    processing_results: Optional[Dict[str, Any]] = None
    compliance_score: Optional[float] = None

    class Config:
        from_attributes = True


class BrandGuidelinePageWithBase64(BrandGuidelinePage):
    """Model for a brand guideline page with base64 data"""

    base64: str


class BrandGuidelineUploadResponse(BaseModel):
    """Response model for brand guideline upload"""

    guideline: BrandGuideline
    pages_processed: int
    message: str
