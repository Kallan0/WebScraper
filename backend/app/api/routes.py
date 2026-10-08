from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool
from app.config import Settings, get_settings
from app.errors import PipelineError
from app.schemas.summarize import SummarizeRequest, SummarizeResponse, SummaryData
from app.services.scraper import fetch_page
from app.services.extractor import extract_content
from app.services.cleaner import clean_text
from app.services.classifier import classify_content
from app.services.summarizer import summarize_text

router = APIRouter(prefix='/api')


@router.post('/summarize', response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest, settings: Settings = Depends(get_settings)):
    scraped = await fetch_page(request.url, settings)
    page = await run_in_threadpool(extract_content, scraped.html)
    text = clean_text(page.text, settings.max_scraped_characters)
    classification = classify_content(page, text)
    if not classification.suitable:
        raise PipelineError(422, classification.reason)
    content = text[:settings.max_summary_characters].rstrip()
    summary = await summarize_text(content, settings, content_type=classification.content_type)
    return SummarizeResponse(data=SummaryData(
        url=scraped.url, title=page.title, content_type=classification.content_type,
        characters_processed=len(content), summary=summary,
        truncated=len(page.text) > settings.max_scraped_characters or len(text) > len(content),
    ))
