from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class GroupBase(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

class GroupDetail(GroupBase):
    student_count: Optional[int] = 0
    members: Optional[List[dict]] = []

class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class MaterialBase(BaseModel):
    id: int
    title: str
    content: str
    material_type: str
    author_name: str
    is_public: bool
    created_at: datetime
    updated_at: datetime
    groups: Optional[List[GroupBase]] = []

class MaterialCreate(BaseModel):
    title: str
    content: str
    material_type: str
    is_public: Optional[bool] = False
    group_ids: Optional[List[int]] = []

class MaterialUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    material_type: Optional[str] = None
    is_public: Optional[bool] = None
    group_ids: Optional[List[int]] = None 