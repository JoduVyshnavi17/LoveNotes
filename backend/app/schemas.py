from pydantic import BaseModel, EmailStr, Field, ConfigDict
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str = Field(min_length=10, max_length=128)
    purpose: str = Field(min_length=2, max_length=80)
    education_level: str = Field(default="", max_length=80)
class LoginIn(BaseModel):
    email: EmailStr
    password: str
class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    purpose: str = "personal learning"
    education_level: str = ""
    model_config = ConfigDict(from_attributes=True)
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
class ContentIn(BaseModel):
    faithful_text: str = ""
    enhanced_text: str = ""
