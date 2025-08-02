import genkit # Not strictly needed for this function, but good to keep for future Genkit flows
import firebase_admin
from firebase_admin import firestore, storage
from firebase_functions import storage as firebase_storage
# Import necessary libraries for Google Docs API interaction
from googleapiclient.discovery import build
import pinecone
import PyPDF2
from docx import Document
import os
from genkit import flow, tool, run, prompt

# This is a placeholder for the Genkit backend.
# The main Genkit flow and other backend logic will be defined here.

# Initialize Firebase Admin SDK
firebase_admin.initialize_app()
db = firestore.client()

# Initialize Pinecone
# Replace with your Pinecone API key and environment
pinecone.init(api_key="YOUR_PINECONE_API_KEY", environment="YOUR_PINECONE_ENVIRONMENT")
# Replace with your Pinecone index name
index_name = "your-pinecone-index-name"
index = pinecone.Index(index_name)

# Initialize Google AI Generative Model and Embedding Model
# Replace with your Google AI API key
genai.configure(api_key="YOUR_GOOGLE_AI_API_KEY")
embedding_model = "models/embedding-001" # Or another suitable embedding model
generation_model = "models/gemini-1.5-pro" # Or your chosen Gemini generation model

def extract_text_from_pdf(blob):
    """Extracts text from a PDF blob."""
    reader = PyPDF2.PdfReader(blob)
    text = ""
    for page_num in range(len(reader.pages)):
        text += reader.pages[page_num].extract_text()
    return text

def extract_text_from_docx(blob):
    """Extracts text from a DOCX blob."""
    # Note: python-docx works with file paths, so we'll need to save the blob temporarily
    # This is a simplified example; handle temporary file management carefully in production
    temp_filepath = f"/tmp/{os.path.basename(blob.name)}"
    blob.download_to_filename(temp_filepath)
    document = Document(temp_filepath)
    text = ""
    for paragraph in document.paragraphs:
        text += paragraph.text + "\\n"
    os.remove(temp_filepath) # Clean up the temporary file
    return text

@firebase_storage.on_object_finalized()
def process_and_embed_document(event: firebase_storage.StorageEvent):
    """
    Cloud Function triggered by Firebase Storage uploads.
    Extracts text, generates embedding, and stores data in Firestore and Pinecone.
    """
    if event.data is None:
        print("No data in storage event.")
        return

    bucket_name = event.data.bucket
    file_path = event.data.name
    file_extension = os.path.splitext(file_path)[1].lower()

    print(f"Processing file: {file_path} in bucket: {bucket_name}")

    # Download the file blob
    bucket = storage.bucket(bucket_name)
    blob = bucket.blob(file_path)

    raw_text = ""
    if file_extension == ".pdf":
        raw_text = extract_text_from_pdf(blob)
    elif file_extension == ".docx":
        raw_text = extract_text_from_docx(blob)
    else:
        print(f"Unsupported file type: {file_extension}")
        return

    if not raw_text:
        print(f"Could not extract text from {file_path}")
        return

    # Assume user ID can be derived from file path or metadata
    # You'll need to implement your logic for determining the user ID
    # For now, using a placeholder
    user_id = "placeholder_user_id" # REPLACE WITH YOUR LOGIC
    if '/' in file_path:
         # Example: Assuming file path is like 'user_id/document.pdf'
        user_id = file_path.split('/')[0]

    # Store metadata and raw text in Firestore
    doc_ref = db.collection("user_documents").add({
        "user_id": user_id,
        "filename": os.path.basename(file_path),
        "file_path": file_path,
        "raw_text": raw_text,
        "created_at": firestore.SERVER_TIMESTAMP,
        "embedding_status": "pending" # Add a status field
    })
    firestore_doc_id = doc_ref[1].id
    print(f"Stored document metadata in Firestore with ID: {firestore_doc_id}")

    try:
        # Generate embedding
        # Ensure the text is not too long for the embedding model
        # You might need to split text for larger documents
        embedding = genai.embed_content(
            model=embedding_model,
            content=raw_text,
            task_type="models.embedding_content.TaskType.RETRIEVAL_DOCUMENT" # Choose appropriate task type
        )["embedding"]

        # Store embedding in Pinecone
        index.upsert([(firestore_doc_id, embedding)])
        print(f"Stored embedding in Pinecone for Firestore document ID: {firestore_doc_id}")

        # Update embedding status in Firestore
        db.collection("user_documents").document(firestore_doc_id).update({
            "embedding_status": "completed"
        })

    except Exception as e:
        print(f"Error generating embedding or storing in Pinecone: {e}")
        # Update embedding status to indicate failure
        db.collection("user_documents").document(firestore_doc_id).update({
            "embedding_status": "failed",
            "error_message": str(e)
        })

if __name__ == "__main__":
    # This part is for local development/testing if needed
    pass

# Placeholder for Google Docs API credentials and initialization
docs_service = None # Initialize later with credentials


@flow(
    name="generateApplicationDocuments",
    input=str, # Input is the job description text
    output=dict, # Output is a dictionary with generated document texts
)
def generateApplicationDocuments(job_description: str):
    """
    Genkit flow to generate job application documents using a RAG workflow.
    """
    # TODO: Implement user authentication/ID handling.
    # The user ID is needed to query only the current user's documents in Pinecone and Firestore.
    # This could be passed in the HTTP request payload or derived from authentication.
    user_id = "placeholder_user_id" # REPLACE WITH YOUR USER ID LOGIC
    print(f"Generating documents for user: {user_id}")

    # 1. Generate embedding for the job description
    # Ensure the job description text is not too long for the embedding model
    job_description_embedding = genai.embed_content(
        model=embedding_model,
        content=job_description,
        task_type="models.embedding_content.TaskType.RETRIEVAL_QUERY" # Use RETRIEVAL_QUERY for query
    )["embedding"]

    # 2. Query Pinecone to find similar document IDs
    # Adjust top_k as needed (e.g., 3 to 5)
    # TODO: Add a filter to the Pinecone query to only search within the current user's documents.
    # This requires storing the user_id as metadata in Pinecone during ingestion.
    query_results = index.query(
        vector=job_description_embedding,
        top_k=5,
        include_metadata=True, # Include metadata to get document type if stored
        # filter={"user_id": user_id} # Example of user-specific filtering (requires metadata)
    )

    # Extract Firestore document IDs from query results
    similar_document_ids = [match['id'] for match in query_results['matches']]
    print(f"Found {len(similar_document_ids)} similar documents in Pinecone.")

    # 3. Fetch the full text of those documents from Firestore
    retrieved_documents_text = ""
    if similar_document_ids:
        # Ensure we only fetch documents belonging to the current user
        docs = db.collection("user_documents").where(firestore.FieldPath.document_id(), "in", similar_document_ids).where("user_id", "==", user_id).get()
        for doc in docs:
            doc_data = doc.to_dict()
            if doc_data and "raw_text" in doc_data:
                retrieved_documents_text += f"--- Document ID: {doc.id}, Filename: {doc_data.get('filename', 'N/A')} ---\n"
                retrieved_documents_text += doc_data["raw_text"] + "\n\n"

    # 4. Construct the detailed augmented prompt for Gemini
    augmented_prompt = f"""
You are an AI career assistant specializing in the Australian Community Services sector.
Based on the following historical documents and the target job description, generate a tailored Resume, a compelling Cover Letter, and detailed Key Selection Criteria (KSC) responses.

Historical Documents (Context):
{retrieved_documents_text if retrieved_documents_text else "No relevant historical documents found. Generate based on general knowledge and job description."}

Target Job Description:
{job_description}

Instructions:
- Use the historical documents as inspiration for structure, phrasing, and relevant experience, but do not directly copy content. Adapt and synthesize.
- Tailor the language and content specifically to the requirements and keywords in the Target Job Description. Address all explicitly mentioned Key Selection Criteria.
- Generate a professional Resume, a compelling Cover Letter, and detailed responses addressing the Key Selection Criteria.
- Format the output clearly, separating the Resume, Cover Letter, and KSC Responses with clear headings (e.g., "--- Generated Resume ---").

Generated Documents:
"""

    # 5. Call the Gemini model with the augmented prompt
    try:
        response = genai.GenerativeModel(generation_model).generate_content(augmented_prompt)
        generated_text = response.text
    except Exception as e:
        print(f"Error calling Gemini model: {e}")
        # Handle error - perhaps return an error message or raise an exception
        return {"error": f"Failed to generate document content: {e}"}

    # 6. Use Google Docs API to create a document and insert generated text
    # TODO: Authenticate with the Google Docs API.
    # You will need to set up OAuth 2.0 for your application and handle
    # obtaining and refreshing credentials. This might involve using
    # Firebase Authentication to obtain user's Google credentials with
    # the necessary scopes (docs.googleapis.com/auth/documents).
    # Store credentials securely, possibly in Firestore or Secret Manager.
    # This is a placeholder for authentication:
    # credentials = get_google_docs_credentials(user_id) # Your function to retrieve credentials
    # docs_service = build('docs', 'v1', credentials=credentials)

    # For now, assuming docs_service is initialized elsewhere with appropriate credentials
    # You MUST replace this with actual authentication logic.
    if docs_service is None:
         # This is a placeholder; you need proper authentication and initialization
         # Example basic initialization (NOT suitable for production):
         # from google.oauth2 import service_account # If using service accounts
         # credentials = service_account.Credentials.from_service_account_file('path/to/service_account.json', scopes=['https://www.googleapis.com/auth/documents'])
         # docs_service = build('docs', 'v1', credentials=credentials)
         # print("Warning: Google Docs service not properly initialized. Using placeholder.")
         return {"error": "Google Docs API service not initialized. Authentication required."}

    try:
        # Create a new document
        title = f"Application for {job_description[:50]}... - {datetime.now().strftime('%Y-%m-%d')}" # Example title
        new_doc = docs_service.documents().create(body={'title': title}).execute()
        document_id = new_doc.get('documentId')
        document_url = f"https://docs.google.com/document/d/{document_id}/edit"
        print(f"Created new Google Doc: {document_url}")

        # Insert generated text and apply basic formatting
        # TODO: Implement detailed formatting using the Docs API.
        # This will involve sending batchUpdate requests to insert text, apply styles, create lists, etc.
        # Example of inserting text:
        # requests = [{'insertText': {'location': {'index': 1}, 'text': generated_text}}] # Insert at the beginning
        # docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

        # 7. Return the URL of the newly created Google Doc
        return {"google_doc_url": document_url}

    except Exception as e:
        print(f"Error creating Google Doc or inserting content: {e}")
        # Handle error - return an error message
        return {"error": f"Failed to create Google Doc: {e}"}




    # 6. Return the generated content as a JSON object
    # TODO: Parse the generated_text if Gemini returns structured output (e.g., JSON).
    # This currently returns the raw generated text. You might want to parse it into
    # separate fields for resume, cover letter, and ksc responses.
    return {
        "generated_content": generated_text,
        "retrieved_document_ids": similar_document_ids # Optionally return IDs used
    }



@flow(
    name="generateApplicationDocuments",
    input=str, # Input is the job description text
    output=dict, # Output is a dictionary with generated document texts
)
def generateApplicationDocuments(job_description: str):
    """
    Genkit flow to generate job application documents using a RAG workflow.
    """
    # 1. Generate embedding for the job description
    job_description_embedding = genai.embed_content(
        model=embedding_model,
        content=job_description,
        task_type="models.embedding_content.TaskType.RETRIEVAL_QUERY" # Use RETRIEVAL_QUERY for query
    )["embedding"]

    # 2. Query Pinecone to find similar document IDs
    # Adjust top_k as needed (e.g., 3 to 5)
    query_results = index.query(
        vector=job_description_embedding,
        top_k=5,
        include_metadata=True # Include metadata to get document type if stored
    )

    # Extract Firestore document IDs from query results
    similar_document_ids = [match['id'] for match in query_results['matches']]
    print(f"Found {len(similar_document_ids)} similar documents in Pinecone.")

    # 3. Fetch the full text of those documents from Firestore
    retrieved_documents_text = ""
    if similar_document_ids:
        docs = db.collection("user_documents").where(firestore.FieldPath.document_id(), "in", similar_document_ids).get()
        for doc in docs:
            doc_data = doc.to_dict()
            if doc_data and "raw_text" in doc_data:
                retrieved_documents_text += f"--- Document ID: {doc.id}, Filename: {doc_data.get('filename', 'N/A')} ---\n"
                retrieved_documents_text += doc_data["raw_text"] + "\n\n"

    # 4. Construct the detailed augmented prompt for Gemini
    augmented_prompt = f"""
You are an AI career assistant specializing in the Australian Community Services sector.
Based on the following historical documents and the target job description, generate a tailored Resume, Cover Letter, and Key Selection Criteria (KSC) responses.

Historical Documents (Context):
{retrieved_documents_text if retrieved_documents_text else "No relevant historical documents found."}

Target Job Description:
{job_description}

Instructions:
- Use the historical documents as inspiration for structure, phrasing, and relevant experience, but do not directly copy content.
- Tailor the language and content specifically to the requirements and keywords in the Target Job Description.
- Generate a professional Resume, a compelling Cover Letter, and detailed responses addressing the Key Selection Criteria (if any are explicitly mentioned or implied in the job description).
- Format the output clearly, separating the Resume, Cover Letter, and KSC Responses.

Generated Documents:
"""

    # 5. Call the Gemini model with the augmented prompt
    # You'll need to choose a specific Gemini model (e.g., gemini-1.5-pro)
    # and use the appropriate Genkit or Google AI client method to call it.
    # This is a placeholder:
    # response = genai.GenerativeModel('gemini-1.5-pro').generate_content(augmented_prompt)
    # generated_text = response.text

    # For demonstration, returning a placeholder response
    generated_text = f"""
--- Generated Resume ---
[Placeholder Resume based on Job Description and historical context]

--- Generated Cover Letter ---
[Placeholder Cover Letter based on Job Description and historical context]

--- Generated KSC Responses ---
[Placeholder KSC Responses based on Job Description and historical context]

Augmented Prompt Used:
{augmented_prompt}
"""

    # 6. Return the generated content as a JSON object
    # You'll need to parse the generated_text if it's structured, or
    # adapt the output based on how you instruct Gemini to format the response.
    # This is a simplified return format.
    return {
        "generated_content": generated_text,
        "retrieved_document_ids": similar_document_ids # Optionally return IDs used
    }