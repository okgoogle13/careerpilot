# ==============================================================================
# main.py - Refactored Backend
#
# This file contains the primary FastAPI application for the API-first
# architecture and the background Cloud Functions.
# ==============================================================================

# --- 1. IMPORTS ---
import asyncio
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict

# Firebase Functions for background tasks
from firebase_functions import storage_fn, scheduler_fn

# Refactored services
from services.firebase_service import firebase_service
from services.vector_db_service import vector_db_service
from services.ai_service import ai_service
from services.gcp_service import gcp_service
from auth import get_current_user

# Environment variable loading for local development
from dotenv import load_dotenv

# --- 2. INITIALIZATION ---
load_dotenv()

# --- 3. FASTAPI APPLICATION ---
app = FastAPI()

class GenerationRequest(BaseModel):
    job_description: str

class GenerationResponse(BaseModel):
    cover_letter_text: str
    resume_text: str

@app.post("/generate", response_model=GenerationResponse)
async def generate_application_documents(
    request: GenerationRequest,
    user: dict = Depends(get_current_user)
):
    """
    API endpoint to generate application documents (cover letter and resume summary).
    """
    try:
        print(f"Starting RAG workflow for user: {user.get('uid')}")

        # 1. Retrieve relevant documents from the vector database
        retrieved_docs = vector_db_service.retrieve(request.job_description, k=3)
        context_docs_text = "\n\n---\n\n".join([doc['text'] for doc in retrieved_docs])

        # 2. Generate content with the AI service
        generated_content = ai_service.generate_document_content(
            job_description=request.job_description,
            context_docs_text=context_docs_text
        )

        return GenerationResponse(**generated_content)

    except Exception as e:
        print(f"Error in /generate endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# --- 4. BACKGROUND CLOUD FUNCTIONS ---

@storage_fn.on_object_finalized()
def process_and_embed_document(event: storage_fn.CloudEvent) -> None:
    """
    Triggered on file upload. Extracts text, embeds it, and stores it.
    This function now uses the refactored services.
    """
    bucket_name = event.data["bucket"]
    file_path = event.data["name"]
    content_type = event.data["contentType"]

    if not file_path.startswith("user_uploads/"):
        print(f"Skipping file in non-processed directory: {file_path}")
        return

    try:
        user_id = firebase_service.get_user_id_from_path(file_path)

        file_bytes = firebase_service.download_file_from_storage(bucket_name, file_path)
        raw_text = firebase_service.extract_text_from_file(file_bytes, content_type)

        firestore_id = firebase_service.store_document_metadata(user_id, file_path, raw_text)

        vector_db_service.index([{"content": raw_text, "metadata": {"id": firestore_id}}])

    except Exception as e:
        print(f"Error processing document {file_path}: {e}")

@scheduler_fn.on_schedule(schedule="0 */1 * * *")
def jobScout_scheduled(event: scheduler_fn.ScheduledEvent) -> None:
    """
    Scheduled trigger for the job scout flow.
    This function now uses the refactored GCPService.
    """
    print(f"Job scout triggered by schedule: {event.schedule_time}")
    try:
        gcp_service.run_job_scout()
    except Exception as e:
        print(f"Critical error in job scout scheduler: {str(e)}")
