from fastapi import APIRouter

router = APIRouter()


@router.post("/generate-image")
def generate_image(prompt: dict) -> dict:
    return {"status": "queued", "prompt": prompt}


@router.post("/generate-voice")
def generate_voice(payload: dict) -> dict:
    return {"status": "queued", "payload": payload}
