# ==============================================================================
# main.py
#
# This is the complete backend for the Personal AI Career Co-Pilot. It contains
# all the Python Cloud Functions and AI logic for the application.
#
# ==============================================================================

# --- 1. IMPORTS ---
# Core Python libraries
import os
import json
import asyncio
import io
from typing import Dict, Any
import datetime
from urllib.parse import urlparse
# Firebase and Google Cloud libraries
from firebase_admin import initialize_app, firestore, storage
from firebase_functions import https_fn, scheduler_fn, storage_fn
from google.cloud import secretmanager
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import genkit
from genkit.models import gemini
from genkit.retrievers import pinecone
import genkit.embedders

# Document Parsing & Web Scraping libraries
from pypdf import PdfReader
import docx
import requests
from bs4 import BeautifulSoup

# Environment variable loading for local development
from dotenv import load_dotenv

# ==============================================================================
# 2. INITIALIZATION
# ==============================================================================
# This section runs once when the function server starts up.

# Load environment variables from a .env file (for local testing)
load_dotenv()

# Initialize Firebase Admin SDK
initialize_app()
# Initialize Genkit Framework
genkit.init(log_level="INFO")

# Initialize Firestore client
db = firestore.client()
# Initialize Pinecone client
pinecone.init(api_key=os.getenv("PINECONE_API_KEY"))

# Define the AI models and tools we will use throughout the application
embedder_model = gemini.text_embedding_004
generator_model = gemini.gemini_1_5_pro
pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "career-pilot-index")
main_retriever = pinecone.PineconeRetriever(index_name=pinecone_index_name)


# ==============================================================================
# 3. HELPER FUNCTIONS
# ==============================================================================

def _extract_text_from_file(file_bytes: bytes, content_type: str) -> str:
    """Extracts raw text from PDF or DOCX file bytes."""
    if content_type == "application/pdf":
        pdf_reader = PdfReader(io.BytesIO(file_bytes))
        return "".join(page.extract_text() for page in pdf_reader.pages)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs)
    else:
        raise ValueError(f"Unsupported file type for text extraction: {content_type}")

def get_oauth_credentials() -> Credentials:
    """
    Fetches stored OAuth credentials from Google Secret Manager.
    
    NOTE: This assumes the secret contains the full JSON structure
    downloaded from the Google Cloud Console after completing the OAuth flow.
    """
    """Fetches stored OAuth credentials from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GCLOUD_PROJECT")
    secret_name = "job-scout-token" # This name must match the secret you create
    
    if not project_id:
        raise ValueError("GCLOUD_PROJECT environment variable is not set.")

    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    try:
        response = client.access_secret_version(request={"name": name})
        creds_json = response.payload.data.decode("UTF-8")
        return Credentials.from_authorized_user_info(json.loads(creds_json))
    except Exception as e:
        print(f"FATAL: Could not access the secret '{secret_name}' in Secret Manager. "
              f"Ensure the secret exists and the Cloud Function's service account has the "
              f"'Secret Manager Secret Accessor' role. Error: {e}")
        raise

def _get_user_id_from_path(file_path: str) -> str:
    """
    Extracts the user ID from the file path.
    Assumes file paths are in the format: user_uploads/{user_id}/{filename}
    """
    parts = file_path.split('/')
    if len(parts) > 1 and parts[0] == "user_uploads":
        return parts[1]
    raise ValueError(f"Could not extract user ID from file path: {file_path}. Expected format: user_uploads/{{user_id}}/{{filename}}")

def _parse_firestore_doc_id_from_uri(uri: str) -> str:
    """
    Parses the Firestore document ID from a Firestore URI string.
    Example URI: projects/{project_id}/databases/(default)/documents/user_documents/{doc_id}
    """
    return uri.split('/')[-1]

# ==============================================================================
# 4. CLOUD FUNCTION: Document Ingestion & Embedding Pipeline
# ==============================================================================
@storage_fn.on_object_finalized()
def process_and_embed_document(event: storage_fn.CloudEvent) -> None:
    """
    Triggered on file upload to Firebase Storage. Extracts text, embeds it,
    and stores it in Firestore and Pinecone.
    """
    bucket_name = event.data["bucket"]
    file_path = event.data["name"]
    content_type = event.data["contentType"]
    
    # Process files only in a specific directory to avoid infinite loops or errors
    if not file_path.startswith("user_uploads/"):
        print(f"Skipping file in non-processed directory: {file_path}")
        # Delete the file if it's in an unexpected location to prevent clutter
        bucket = storage.bucket(bucket_name)
        blob = bucket.blob(file_path)
        blob.delete()
        return

    user_id = _get_user_id_from_path(file_path)
    try:
        # Download file content from Storage
        bucket = storage.bucket(bucket_name)
        blob = bucket.blob(file_path)
        file_bytes = blob.download_as_bytes()
        
        # Extract text from the file
        raw_text = _extract_text_from_file(file_bytes, content_type)

        # 2. Generate a vector embedding for the text
        embedding = genkit.embed(embedder=embedder_model, content=raw_text)
        
        # 3. Store the raw text and metadata in Firestore
        # Store in a subcollection specific to the user
        doc_ref = db.collection("users").document(user_id).collection("user_documents").document()
        doc_ref.set({
            "original_storage_path": file_path,
            "raw_text": raw_text,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        firestore_id = doc_ref.id
        print(f"Document stored in Firestore with ID: {firestore_id}")

        # 4. Store the embedding in Pinecone, linking it with the Firestore ID
        # Genkit expects chunks to be in the format {"content": ..., "metadata": {"id": ...}}
        # Or simply {"content": ...} if id comes from the content itself.
        # Here, we'll use the Firestore ID as the vector ID.
        # Genkit's Pinecone indexer handles the vector creation from content.
        # We need to format the document correctly for Genkit's indexer.
        # The PineconeRetriever expects Chunk objects, which can be created from text.
        # For simple text indexing, we can just pass the text and let Genkit handle it.
        main_retriever.index([{"content": raw_text, "metadata": {"id": firestore_id}}])
        print(f"Embedding stored in Pinecone with ID: {firestore_id}")

    except Exception as e:
        print(f"Error processing document {file_path}: {e}")
        # Optionally, delete the file to prevent repeated errors on the same file
        # bucket = storage.bucket(bucket_name)
        # blob = bucket.blob(file_path)
        # blob.delete()

# ==============================================================================
# 5. CLOUD FUNCTION: RAG Document Generation with Google Docs Output
# ==============================================================================
@https_fn.on_request(cors=True)
def generateApplicationDocuments(req: https_fn.Request) -> https_fn.Response:
 """
    HTTP endpoint to generate application documents, using RAG and creating a formatted Google Doc.
    """
    if req.method != 'POST':
        return https_fn.Response("Method not allowed", status=405)
        
    try:
        payload = req.get_json()
        job_description = payload.get("job_description")
        if not job_description:
            return https_fn.Response(json.dumps({"error": "Missing job_description"}), status=400)

        # RAG Workflow: Retrieve relevant documents from Pinecone
 print(f"Starting RAG workflow for job description: {job_description[:50]}...")
        retrieved_docs = main_retriever.retrieve(job_description, k=3)
        context_docs_text = "\n\n---\n\n".join([doc.text for doc in retrieved_docs])

        # Construct Prompt for Gemini
        prompt = f"""
        You are an expert career document writer for the Australian Community Services sector.
        Your task is to generate a tailored resume summary and a full cover letter based on the provided job description and relevant examples from the user's past documents.

        **TARGET JOB DESCRIPTION:**
        {job_description}

        **RELEVANT EXAMPLES FROM USER'S PAST DOCUMENTS (FOR CONTEXT AND STYLE):**
        {context_docs_text}

        **INSTRUCTIONS:**
        1. Analyze the TARGET JOB DESCRIPTION to understand the key requirements.
        2. Use the writing style, skills, and experiences from the RELEVANT EXAMPLES to write a new, tailored resume summary and a compelling cover letter.
        3. Do not copy the examples verbatim. Synthesize and adapt them to the target role.
        4. The output must be a JSON object with two keys: "cover_letter_text" and "resume_text".

        **OUTPUT FORMAT (JSON only):**
        {{
          "cover_letter_text": "...",
          "resume_text": "..."
        }}
        """

        # Generate content with Gemini
        llm_response = genkit.generate(model=generator_model, prompt=prompt, config={"response_format": "json"})
        generated_content = json.loads(llm_response.text())
        cover_letter_text = generated_content.get("cover_letter_text", "Error: Could not generate cover letter.")
        resume_text = generated_content.get("resume_text", "Error: Could not generate resume.")
        print("AI content generated successfully.")

        # Google Docs API Integration
        print("Initializing Google Docs client...")
 creds = get_oauth_credentials() # Ensure these credentials have the Google Docs API scope
        docs_service = build('docs', 'v1', credentials=creds)
        
        # 1. Create the Google Doc
        doc_title = f"Application for {job_description[:40]}..."
        doc = docs_service.documents().create(body={'title': doc_title}).execute()
        doc_id = doc['documentId']
        print(f"Google Doc created with ID: {doc_id}")

 # 2. Prepare text and formatting requests for batchUpdate
        # Note: startIndex and endIndex are 1-based. Insertions shift subsequent indices.
        # Need to carefully calculate indices after each insertion.
        
        requests = [
            {'insertText': {'location': {'index': 1}, 'text': "Cover Letter\n"}},
            {'updateParagraphStyle': {'range': {'startIndex': 1, 'endIndex': 12}, 'paragraphStyle': {'namedStyleType': 'HEADING_1'}, 'fields': 'namedStyleType'}},
            {'insertText': {'location': {'index': 13}, 'text': f"{cover_letter_text}\n\n"}},
 {'insertText': {'location': {'index': 14 + len(cover_letter_text) + 2}, 'text': "Resume Summary\n"}}, # After previous insertion + text length + 2 newlines
 {'updateParagraphStyle': {'range': {'startIndex': 14 + len(cover_letter_text) + 2, 'endIndex': 14 + len(cover_letter_text) + 2 + 15}, 'paragraphStyle': {'namedStyleType': 'HEADING_1'}, 'fields': 'namedStyleType'}}, # "Resume Summary" + newline = 15 chars
            {'insertText': {'location': {'index': 13 + len(cover_letter_text) + 2 + 16}, 'text': resume_text}},
        ]
        
        # 3. Send the update request to the Docs API
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        print("Successfully inserted text into Google Doc.")

        # 4. Return the URL of the new document
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        
        return https_fn.Response(json.dumps({"google_doc_url": doc_url}), status=200)

    except Exception as e:
        print(f"Error in generateApplicationDocuments: {e}")
        return https_fn.Response(json.dumps({"error": str(e)}), status=500)

# ==============================================================================
# 6. CLOUD FUNCTION: Scheduled Job Scout
# ==============================================================================
@scheduler_fn.on_schedule(schedule="0 */1 * * *") # Runs every hour
def jobScout_scheduled(event: scheduler_fn.ScheduledEvent) -> None:
 """Scheduled trigger for the job scout flow."""
    print(f"Job scout triggered by schedule: {event.schedule_time}")
    try:
        asyncio.run(job_scout_flow())
    except Exception as e:
        print(f"Critical error in job scout scheduler: {str(e)}")

async def job_scout_flow():
    """The main async logic for the job scout feature."""
    creds = get_oauth_credentials()
    gmail_service = build('gmail', 'v1', credentials=creds)
    calendar_service = build('calendar', 'v1', credentials=creds)

    senders = ["noreply@s.seek.com.au", "noreply@ethicaljobs.com.au", "donotreply@jora.com"]
    processed_count = 0
    
    for sender in senders:
        results = gmail_service.users().messages().list(userId='me', q=f"is:unread from:{sender}").execute()
        messages = results.get('messages', [])
        
        for message in messages:
            # Simplified logic for creating a calendar reminder
            subject = "Apply for Job (from email alert)"
            event_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
            event = {
                'summary': subject,
                'start': {'date': event_date},
                'end': {'date': event_date},
            }
            calendar_service.events().insert(calendarId='primary', body=event).execute()
            gmail_service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()
            processed_count += 1
            
    print(f"Job scout finished. Processed {processed_count} emails.")