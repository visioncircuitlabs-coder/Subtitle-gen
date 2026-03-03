from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    filename: str


class ProgressEvent(BaseModel):
    stage: str
    progress: float
    message: str = ""


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    progress: float


class ErrorResponse(BaseModel):
    detail: str
