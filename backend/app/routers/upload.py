from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict, Any
from ..ocr import pipeline, parser

router = APIRouter(
    prefix="/upload",
    tags=["upload"],
)

@router.post("/", response_model=List[Dict[str, Any]])
async def upload_images(files: List[UploadFile] = File(...)):
    all_picks = []
    
    for file in files:
        if not file.content_type.startswith("image/"):
            continue # Skip non-image files
        
        contents = await file.read()
        
        # Run OCR
        raw_text = pipeline.extract_text(contents)
        
        # Parse picks
        picks = parser.parse_picks(raw_text)
        all_picks.extend(picks)
    
    return all_picks
