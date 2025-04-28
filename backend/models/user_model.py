from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Optional
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        # You can customize the schema here
        json_schema = handler(core_schema)
        json_schema.update(type="string")
        return json_schema



class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    city: str

    class Config:
        validate_by_name = True  
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        from_attributes = True


class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UserResponse(UserBase):
    id: str
    created_at: datetime

    class Config:
        orm_mode = True


class LastJob(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None


class LifeStage(BaseModel):
    pregnancy_status: Optional[str] = None
    needs_flexible_work: bool = False
    situation: Optional[str] = None


class JobPreferences(BaseModel):
    type: Optional[str] = None
    roles: List[str] = []
    short_term_goal: Optional[str] = None
    long_term_goal: Optional[str] = None


class Location(BaseModel):
    city: str
    relocation: bool = False
    work_mode: Optional[str] = None


class Community(BaseModel):
    wants_mentorship: bool = False
    mentorship_type: Optional[str] = None
    join_events: bool = False


class ProfileCreate(BaseModel):
    user_id: str
    education: Optional[str] = None
    skills: List[str] = []
    current_status: Optional[str] = None
    experience_years: Optional[int] = None
    last_job: Optional[LastJob] = None
    life_stage: Optional[LifeStage] = None
    job_preferences: Optional[JobPreferences] = None
    location: Optional[Location] = None
    community: Optional[Community] = None
    communication_preference: Optional[str] = None
    consent: bool = False


class ProfileInDB(ProfileCreate):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ProfileResponse(ProfileCreate):
    id: str
    created_at: datetime

    class Config:
        orm_mode = True