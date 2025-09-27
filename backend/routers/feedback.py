from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.logging_service import update_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])

class FeedbackRequest(BaseModel):
    log_id: int
    feedback: int   # 1 = 👍 helpful, 0 = 👎 not helpful

@router.post("/")
async def give_feedback(request: FeedbackRequest):
    try:
        update_feedback(request.log_id, request.feedback)
        return {"status": "success", "log_id": request.log_id, "feedback": request.feedback}
    except Exception as e:
        return {"status": "error", "message": str(e)}
