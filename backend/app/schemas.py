from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)

    @field_validator("session_id", "question")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        """拒绝只包含空白字符的字段。"""
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value
