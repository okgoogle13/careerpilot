import functions_framework
import os
import fitz  # PyMuPDF
import docx
from google.cloud import firestore
import google.generativeai as genai
from pinecone import Pinecone
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Initialization ---

# Initialize Firestore client
db = firestore.Client()

# Initialize Pinecone
# TODO: You need to set up Pinecone and get your API key, environment, and index name
# You need to set up Pinecone and get your API key, environment, and index name
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_ENVIRONMENT = os.environ.get('PINECONE_ENVIRONMENT')
PINECONE_INDEX_NAME = os.environ.get('PINECONE_INDEX_NAME')

pinecone_client = None
index = None

if PINECONE_API_KEY and PINECONE_ENVIRONMENT and PINECONE_INDEX_NAME:
    try:
        pinecone_client = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
        index = pinecone_client.Index(PINECONE_INDEX_NAME)
        logging.info("Pinecone client and index initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing Pinecone: {e}")
else:
    logging.warning("Pinecone environment variables not fully set. Pinecone integration will be skipped.")


# Initialize Generative AI model
# You need to set your Google AI API key in environment variables
# TODO: Set GOOGLE_AI_API_KEY in your Cloud Functions environment variables
GOOGLE_AI_API_KEY = os.environ.get('GOOGLE_AI_API_KEY')
embedding_model = "models/embedding-001"  # Choose an appropriate embedding model
if GOOGLE_AI_API_KEY:
    genai.configure(api_key=GOOGLE_AI_API_KEY)
    embedding_model = "models/embedding-001"  # Choose an appropriate embedding model
    logging.info(f"Google AI model configured using {embedding_model} for embeddings.")
else:
    logging.warning("GOOGLE_AI_API_KEY environment variable not set. AI operations will be skipped.")

# TODO: Placeholder for Google Docs API credentials and initialization
docs_service = None # Initialize later with credentials fetched from Secret Manager (in the jobScout function example).

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        logging.info(f"Successfully extracted text from PDF: {pdf_path}")
    except Exception as e:
        logging.error(f"Error extracting text from PDF {pdf_path}: {e}")
        text = None
    return text


def extract_text_from_docx(docx_path):
    """Extracts text from a DOCX file."""
    text = ""
    try:
        doc = docx.Document(docx_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        logging.info(f"Successfully extracted text from DOCX: {docx_path}")
    except Exception as e:
        logging.error(f"Error extracting text from DOCX {docx_path}: {e}")
        text = None
    return text


@functions_framework.cloud_event
def process_and_embed_document(cloud_event):
    """
    Cloud Function to process uploaded documents, extract text,
    generate embeddings, and store data in Firestore and Pinecone.
    Triggered by Firebase Storage uploads.
    """
    logging.info(f"Received Cloud Storage event: {cloud_event.data}")

    data = cloud_event.data
    bucket = data.get("bucket")
    file_path = data.get("name")

    if not bucket or not file_path:
        logging.error("Missing bucket or file_path in event data.")
        return

    logging.info(f"Processing file: gs://{bucket}/{file_path}")

    # TODO: Download the file from Firebase Storage to a temporary directory.
    # You'll need to use the Firebase Admin SDK for Python to download the file.
    # Example (requires firebase_admin initialization):
    # from firebase_admin import storage
    # bucket_obj = storage.bucket(bucket)
    # blob = bucket_obj.blob(file_path)
    # local_file_path = f"/tmp/{os.path.basename(file_path)}" # Download to a temporary directory
    # try:
    #     blob.download_to_filename(local_file_path)
    # except Exception as e:
    #      logging.error(f"Error downloading file {file_path}: {e}")
    #      return
    local_file_path = file_path # Placeholder - REPLACE WITH ACTUAL DOWNLOAD PATH

    # Ensure the placeholder path exists for basic local testing
    # In a real Cloud Function, the file must be downloaded to /tmp
    if not os.path.exists(local_file_path):
         logging.error(f"Error: Local file not found at {local_file_path}. This should be a downloaded file.")
         return

    raw_text = None
    if local_file_path.lower().endswith('.pdf'):
        raw_text = extract_text_from_pdf(local_file_path)
    elif local_file_path.lower().endswith('.docx'):
        raw_text = extract_text_from_docx(local_file_path)
    else:
        logging.warning(f"Unsupported file type for text extraction: {local_file_path}")
        # TODO: Decide how to handle unsupported file types (e.g., skip, log, error)
        return

    if raw_text is None:
        logging.error(f"Failed to extract text from {local_file_path}")
        # TODO: Decide how to handle text extraction failure (e.g., log, error, update Firestore status)
        return

    # TODO: Implement your logic for determining the user ID.
    # This might involve parsing the file_path (e.g., if files are stored in user-specific folders)
    # or extracting from metadata if available.
    user_id = "placeholder_user_id" # REPLACE WITH YOUR LOGIC
    if '/' in file_path:
         # Example: Assuming file path is like 'user_id/document.pdf'
         user_id = file_path.split('/')[0]
         logging.info(f"Deduced user ID: {user_id} from file path: {file_path}")


    # Store metadata and raw text in Firestore
    firestore_doc_id = None
    try:
        doc_ref = db.collection("user_documents").add({
            "user_id": user_id,
            "filename": os.path.basename(file_path),
            "file_path": file_path,
            "raw_text": raw_text,
            "created_at": firestore.SERVER_TIMESTAMP,
            "embedding_status": "pending" # Add a status field
        })
        firestore_doc_id = doc_ref[1].id
        logging.info(f"Stored document metadata in Firestore with ID: {firestore_doc_id}")

    except Exception as e:
        logging.error(f"Error storing document metadata in Firestore for {file_path}: {e}")
        # If Firestore storage fails, we cannot link the embedding, so we stop.
        return

    # Generate embedding and store in Pinecone
    if pinecone_client and index and GOOGLE_AI_API_KEY:
        try:
            # TODO: Ensure the text is not too long for the embedding model.
            # You might need to split text for larger documents and generate embeddings for chunks.
            # This example assumes the whole text fits in one embedding call.
            embedding_response = genai.embed_content(
                model=embedding_model,
                content=raw_text,
                task_type="models.embedding_content.TaskType.RETRIEVAL_DOCUMENT" # Choose appropriate task type
            )
            embedding = embedding_response["embedding"]
            logging.info(f"Generated embedding for Firestore document ID: {firestore_doc_id}")

            # Store embedding in Pinecone
            index.upsert([(firestore_doc_id, embedding)])
            logging.info(f"Stored embedding in Pinecone for Firestore document ID: {firestore_doc_id}")

            # Update embedding status in Firestore
            db.collection("user_documents").document(firestore_doc_id).update({
                "embedding_status": "completed"
            })
            logging.info(f"Updated Firestore embedding status to 'completed' for ID: {firestore_doc_id}")


        except Exception as e:
            logging.error(f"Error generating embedding or storing in Pinecone for Firestore document ID {firestore_doc_id}: {e}")
            # Update embedding status to indicate failure
            db.collection("user_documents").document(firestore_doc_id).update({
                "embedding_status": "failed",
                "error_message": str(e)
            })
            logging.info(f"Updated Firestore embedding status to 'failed' for ID: {firestore_doc_id}")

    else:
        logging.warning("Pinecone or Google AI not fully initialized. Skipping embedding for Firestore document ID: {firestore_doc_id}.")
        # TODO: Decide how to handle skipping embedding (e.g., update Firestore status)


    # TODO: Clean up the downloaded temporary file (if downloaded)
    # if os.path.exists(local_file_path) and local_file_path.startswith("/tmp/"):
    #     try:
    #         os.remove(local_file_path)
    #         logging.info(f"Cleaned up temporary file: {local_file_path}")
    #     except Exception as e:
    #         logging.error(f"Error cleaning up temporary file {local_file_path}: {e}")


# --- Core Document Generation Flow ---

@functions_framework.http
def generateApplicationDocuments(request):
    """
    HTTP Cloud Function (Genkit flow) to generate application documents
    based on a job description and retrieved relevant documents,
    and create a Google Doc with the generated content.
    """
    try:
        # Parse the JSON payload from the request
        request_json = request.get_json(silent=True)
        if not request_json or 'job_description' not in request_json:
            return jsonify({"error": "Invalid request. Please provide a 'job_description' in the JSON payload."}), 400

        job_description = request_json['job_description']
        print(f"Received job description: {job_description[:100]}...") # Log first 100 chars

        # 1. Generate a vector embedding for the incoming job_description.
        if not embedding_model:
             return jsonify({"error": "Embedding model not initialized."}), 500

        try:
            job_description_embedding = genai.embed_content(
                model=embedding_model,
                content=job_description,
                task_type="models.embedding_content.TaskType.RETRIEVAL_QUERY" # Use RETRIEVAL_QUERY for querying
            )["embedding"]
            print("Generated embedding for job description.")
        except Exception as e:
            print(f"Error generating embedding for job description: {e}")
            return jsonify({"error": "Error generating embedding for job description."}), 500

        # 2. Query the Pinecone index to find the IDs of the top 3 most semantically similar documents.
        if not index:
             return jsonify({"error": "Pinecone index not initialized."}), 500

        try:
            # Query Pinecone index
            # Replace with your actual index.query parameters
            query_response = index.query(
                vector=job_description_embedding,
                top_k=3, # Get top 3 similar documents
                include_metadata=False # We only need the IDs for now
            )

            # Extract document IDs from the query response
            # Assuming the response structure has 'matches' with 'id'
            document_ids = [match['id'] for match in query_response.matches]
            print(f"Found {len(document_ids)} similar documents in Pinecone.")
            print(f"Document IDs: {document_ids}")

        except Exception as e:
            print(f"Error querying Pinecone index: {e}")
            return jsonify({"error": "Error querying Pinecone index."}), 500

        # 3. Fetch the full text of these documents from Firestore.
        if not db:
             return jsonify({"error": "Firestore client not initialized."}), 500

        retrieved_texts = []
        if document_ids:
            try:
                # Fetch documents from Firestore by ID
                docs = [db.collection('user_documents').document(doc_id).get() for doc_id in document_ids]

                for doc in docs:
                    if doc.exists:
                        retrieved_texts.append(doc.to_dict().get('raw_text', '')) # Get raw_text field
                print(f"Fetched {len(retrieved_texts)} documents from Firestore.")
            except Exception as e:
                 print(f"Error fetching documents from Firestore: {e}")
                 return jsonify({"error": "Error fetching documents from Firestore."}), 500
        else:
            print("No similar documents found in Pinecone.")

        # 4. Construct an augmented prompt for the Gemini model.
        prompt_text = f"""
You are an AI career co-pilot specializing in the Australian Community Services sector.
Your task is to generate a personalized cover letter and resume content based on the provided job description and the user's historical documents.

Job Description:
{job_description}

Historical Document Content (for context):
{chr(10).join(retrieved_texts)}

Instructions:
- Generate content for a cover letter and a resume that highlights relevant skills and experiences from the historical documents, tailored to the job description.
- Ensure the content is professional and relevant to the Australian Community Services sector.
- Do NOT include placeholders like [Your Name], [Address], etc. Just provide the core text content for the cover letter and resume sections.
- Clearly separate the cover letter and resume content with distinct headings like "Cover Letter" and "Resume".

Generated Content:
"""
        print("Constructed augmented prompt for Gemini.")

        # 5. Call the Gemini model to generate the text content.
        if not generation_model:
            return jsonify({"error": "Generative model not initialized."}), 500

        try:
            # Call the Gemini model
            response = generation_model.generate_content(prompt_text)
            generated_text = response.text
            print("Generated content using Gemini.")
            # print(f"Generated text: {generated_text}") # Log generated text (be mindful of size)

        except Exception as e:
            print(f"Error calling Gemini model: {e}")
            return jsonify({"error": "Error calling Gemini model."}), 500

        # 6. Integrate Google Docs API
        # Initialize the Docs API client
        try:
            # Assuming you have a function to get OAuth credentials
            # You need to implement get_oauth_credentials() based on your credential management
            # This might involve using google-auth-oauthlib or fetching from Secret Manager
            # For example:
            # credentials = get_oauth_credentials()
            # docs_service = build('docs', 'v1', credentials=credentials)

            # Placeholder for credentials and service initialization
            # Replace with your actual credential loading and service building
            # For demonstration, let's assume a global docs_service is initialized elsewhere
            global docs_service # Use global if docs_service is initialized outside

            if docs_service is None:
                 # Attempt to initialize the Docs service if not already done
                 # This part needs to be adapted based on your actual initialization logic
                 try:
                     # Example: Using Application Default Credentials if available
                     import google.auth
                     credentials, project = google.auth.default()
                     docs_service = build('docs', 'v1', credentials=credentials)
                     print("Google Docs service initialized within function.")
                 except Exception as e:
                      print(f"Error initializing Google Docs service within function: {e}")
                      return jsonify({"error": "Error initializing Google Docs service."}), 500


        except Exception as e:
            print(f"Error getting Google Docs API credentials or initializing service: {e}")
            return jsonify({"error": "Error getting Google Docs API credentials or initializing service."}), 500

        try:
            # Create a new Google Doc
            title = "AI-Generated Application Documents"
            new_doc = docs_service.documents().create(body={'title': title}).execute()
            document_id = new_doc.get('documentId')
            print(f"Created Google Doc with ID: {document_id}")

            # Insert the text with headings
            # You'll need to split the generated_text into cover_letter_text and resume_text
            # based on your prompt's separation instructions.
            # For now, let's assume generated_text contains both with a clear separator.
            # Example splitting (adapt to your actual generated text format):
            # if "Resume" in generated_text:
            #     cover_letter_text, resume_text = generated_text.split("Resume", 1)
            # else:
            #      cover_letter_text = generated_text
            #      resume_text = "" # Or handle as a single document

            # For this example, let's assume you have already separated them
            # Replace with your actual separated cover_letter_text and resume_text
            cover_letter_text = "..." # Your logic to extract cover letter
            resume_text = "..." # Your logic to extract resume


            requests = []

            # Add Cover Letter Heading and Text
            requests.append({
                'insertText': {
                    'location': { 'index': 1 },
                    'text': "Cover Letter\n\n"
                }
            })
            requests.append({
                'updateParagraphStyle': {
                    'range': { 'startIndex': 1, 'endIndex': len("Cover Letter\n\n") + 1},
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_1'
                    }
                }
            })
            requests.append({
                 'insertText': {
                     'location': { 'index': len("Cover Letter\n\n") + 1},
                     'text': cover_letter_text + "\n\n"
                 }
             })

            # Add Resume Heading and Text
            requests.append({
                'insertText': {
                    'location': { 'index': len("Cover Letter\n\n" + cover_letter_text + "\n\n") + 1},
                    'text': "Resume\n\n"
                }
            })
            requests.append({
                'updateParagraphStyle': {
                    'range': { 'startIndex': len("Cover Letter\n\n" + cover_letter_text + "\n\n") + 1, 'endIndex': len("Cover Letter\n\n" + cover_letter_text + "\n\n") + len("Resume\n\n") + 1},
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_1'
                    }
                }
            })
            requests.append({
                 'insertText': {
                     'location': { 'index': len("Cover Letter\n\n" + cover_letter_text + "\n\n") + len("Resume\n\n") + 1},
                     'text': resume_text
                 }
             })


            # Execute the batch update
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}).execute()
            print("Inserted generated text into Google Doc with headings.")

            # Get the URL of the created document
            document_url = f"https://docs.google.com/document/d/{document_id}/edit"
            print(f"Google Doc URL: {document_url}")

            # Return the URL
            return jsonify({"google_doc_url": document_url}), 200

        except Exception as e:
            print(f"Error creating or updating Google Doc: {e}")
            return jsonify({"error": "Error creating or updating Google Doc."}), 500


    except Exception as e:
        print(f"An unexpected error occurred in generateApplicationDocuments: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500


# --- Scheduled Job Scout Flow ---

# TODO: Implement the scheduled Cloud Function 'jobScout' here (Step 5).
# This function will fetch credentials, scan Gmail/Calendar, and create events.


# --- Local Testing ---

# This part is for local development/testing of individual functions if needed
if __name__ == "__main__":
    # Example usage for local testing
    # You would need to have a dummy file at a path like "test_user_id/test_document.pdf"
    # and set up environment variables (GOOGLE_APPLICATION_CREDENTIALS for Firestore,
    # and the Pinecone/Google AI env vars).
    # # Create a dummy file for testing if it doesn't exist
    # dummy_pdf_path = "test_user_id/test_document.pdf"
    # if not os.path.exists(dummy_pdf_path):
    #     os.makedirs(os.path.dirname(dummy_pdf_path), exist_ok=True)
    #     with open(dummy_pdf_path, "w") as f:
    #         f.write("This is a test PDF document.")
    #
    # # Simulate a Cloud Storage event structure
    # dummy_event_data = {
    #     "bucket": "your-test-bucket", # Replace with a dummy bucket name
    #     "name": dummy_pdf_path,
    #     "metageneration": "1",
    #     "resourceState": "exists",
    #     "timeCreated": "2023-01-01T00:00:00Z",
    #     "updated": "2023-01-01T00:00:00Z"
    # }
    #
    # # Create a dummy CloudEvent object (simplified)
    # class DummyCloudEvent:
    #     def __init__(self, data):
    #         self.data = data
    #
    # dummy_cloud_event = DummyCloudEvent(dummy_event_data)
    #
    # # Call the function
    # process_and_embed_document(dummy_cloud_event)
    pass


# TODO: Placeholder for Google Docs API credentials and initialization
# You will need to initialize the Google Docs API client here using credentials
# fetched from Secret Manager (in the jobScout function example).
docs_service = None # Initialize later with credentials

# TODO: Implement the HTTP-triggered Genkit flow 'generateApplicationDocuments' here.
# This function will handle the core RAG logic for generating cover letters and resumes.

# TODO: Implement the scheduled Cloud Function 'jobScout' here.
# This function will fetch credentials, scan Gmail/Calendar, and create events.


# Note: You will need to define the actual trigger for the process_and_embed_document function
# in your firebase.json file or through the Firebase console.
# It should be a Firebase Storage trigger that provides the file path as part of the event data.