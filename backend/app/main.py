import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import router
from app.config import get_settings
from app.errors import PipelineError

app = FastAPI(title='AI Web Scraper', version='0.1.0')
app.add_middleware(
    CORSMiddleware, allow_origins=[get_settings().frontend_url],
    allow_methods=['GET', 'POST'], allow_headers=['Content-Type'],
)
app.include_router(router)


@app.get('/api/health')
async def health():
    return {'status': 'ok'}


@app.exception_handler(PipelineError)
async def pipeline_error(request: Request, exc: PipelineError):
    return JSONResponse(status_code=exc.status_code, content={'success': False, 'error': exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={
        'success': False, 'error': 'Send a JSON object containing a valid url string.',
    })


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logging.getLogger(__name__).exception('Unexpected pipeline error')
    return JSONResponse(status_code=500, content={
        'success': False, 'error': 'An unexpected error occurred. Please try again.',
    })
