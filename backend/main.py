# ==============================================================================
# main.py - Refactored Backend
#
# This file contains the primary FastAPI application for the API-first
# architecture and the background Cloud Functions.
# =================================================_

# --- 1. IMPORTS ---
import asyncio
import json
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, List, AsyncGenerator
from fastapi.responses import StreamingResponse

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

class FeedbackRequest(BaseModel):
    feedback: str
    job_description: str
    generated_text: str

class DocumentResponse(BaseModel):
    id: str
    original_storage_path: str
    created_at: str

async def generate_and_stream(
    job_description: str,
    user: dict
) -> AsyncGenerator[str, None]:
    """Generator function for the streaming response."""
    try:
        yield "event: message\ndata: Starting RAG workflow...\n\n"

        # 1. Retrieve relevant documents
        retrieved_docs = vector_db_service.retrieve(job_description, k=3)
        context_docs_text = "\n\n---\n\n".join([doc['text'] for doc in retrieved_docs])
        yield "event: message\ndata: Retrieved relevant documents.\n\n"

        # 2. Generate content stream
        content_generator = ai_service.generate_document_content_stream(
            job_description=job_description,
            context_docs_text=context_docs_text
        )

        cover_letter_text = ""
        resume_text = ""
        async for chunk in content_generator:
            yield f"event: partial_result\ndata: {json.dumps(chunk)}\n\n"
            if chunk.get("cover_letter_chunk"):
                cover_letter_text += chunk["cover_letter_chunk"]
            if chunk.get("resume_chunk"):
                resume_text += chunk["resume_chunk"]

        yield "event: message\ndata: Content generation complete.\n\n"

        # 3. Create Google Doc with the full generated content
        doc_title = f"Application for {job_description[:50]}"
        document_url = gcp_service.create_google_doc(
            title=doc_title,
            cover_letter=cover_letter_text,
            resume_summary=resume_text
        )
        yield "event: message\ndata: Created Google Doc.\n\n"

        # 4. Send final result
        final_data = {
            "cover_letter_text": cover_letter_text,
            "resume_text": resume_text,
            "document_url": document_url
        }
        yield f"event: final_result\ndata: {json.dumps(final_data)}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {str(e)}\n\n"

@app.post("/generate-stream")
async def generate_application_documents_stream(
    request: GenerationRequest,
    user: dict = Depends(get_current_user)
):
    """
    API endpoint to generate application documents and stream the response.
    """
    return StreamingResponse(generate_and_stream(request.job_description, user), media_type="text/event-stream")

@app.post("/feedback")
async def receive_.feedback(
    request: FeedbackRequest,
    user: dict = Depends(get_current_user)
):
    """
    API endpoint to receive and store user feedback.
    """
    try:
        firebase_service.store_feedback(
            feedback=request.feedback,
            job_description=request.job_description,
            generated_text=request.generated_text
        )
        return {"message": "Feedback received successfully"}
    except Exception as e:
        print(f"Error in /feedback endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/documents", response_model=List[DocumentResponse])
async def get_user_documents(user: dict = Depends(get_current_user)):
    """
    API endpoint to retrieve a list of user's uploaded documents.
    """
    try:
        user_id = user.get("uid")
        documents = firebase_service.get_user_documents(user_id)
        return documents
    except Exception as e:
        print(f"Error in /documents endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/documents/{document_id}")
async def delete_user_document(document_id: str, user: dict = Depends(get_current_user)):
    """
    API endpoint to delete a user's document.
    """
    try:
        user_id = user.get("uid")
        firebase_service.delete_document(user_id, document_id)
        return {"message": "Document deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        print(f"Error in /documents/{document_id} endpoint: {e}")
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

        # BUG FIX: Corrected variable name from fire_store_id to firestore_id
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
