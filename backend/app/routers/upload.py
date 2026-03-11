from fastapi import APIRouter, UploadFile, File
from typing import List, Dict, Any, Optional
from ..ocr import pipeline, parser

router = APIRouter(
    prefix="/upload",
    tags=["upload"],
)

@router.post("/")
async def upload_images(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    all_picks: List[Dict[str, Any]] = []
    detected_capper: Optional[str] = None

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue

        contents = await file.read()

        raw_text = pipeline.extract_text(contents)

        # Try to extract the capper name from the first image that yields one
        if detected_capper is None:
            detected_capper = parser.extract_capper_name(raw_text)

        picks = parser.parse_picks(raw_text)
        all_picks.extend(picks)

    return {
        "picks": all_picks,
        "detected_capper": detected_capper,
    }
