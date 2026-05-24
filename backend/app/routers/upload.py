from fastapi import APIRouter, UploadFile, File
from typing import List, Dict, Any, Optional
from ..ocr import parse_router

router = APIRouter(
    prefix="/upload",
    tags=["upload"],
)

@router.post("/")
async def upload_images(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    all_picks: List[Dict[str, Any]] = []
    detected_capper: Optional[str] = None
    all_raw_texts: List[str] = []
    failed_images: List[str] = []

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue

        contents = await file.read()
        filename = file.filename or "unknown"

        result = await parse_router.extract_picks(contents)
        raw_text = result.get("raw_text", "")
        all_raw_texts.append(raw_text)

        if result.get("engine") == "vision_failed":
            # Vision was triggered but returned nothing — flag this file so
            # the caller knows it needs manual attention.
            failed_images.append(filename)
            continue

        # Use the first capper name extracted (from vision or OCR)
        if detected_capper is None:
            detected_capper = result.get("capper_name")

        all_picks.extend(result["picks"])

    return {
        "picks": all_picks,
        "detected_capper": detected_capper,
        "raw_text": "\n---\n".join(all_raw_texts) if all_raw_texts else None,
        "failed_images": failed_images,
    }
