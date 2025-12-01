from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict, Any
from ..ocr import pipeline, parser

router = APIRouter(
    prefix="/upload",
    tags=["upload"],
)

@router.post("/", response_model=List[Dict[str, Any]])
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    contents = await file.read()
    
    # Run OCR
    raw_text = pipeline.extract_text(contents)
    
    # Parse picks
    picks = parser.parse_picks(raw_text)
    
    return picks
