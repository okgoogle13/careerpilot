import io
import pypdf
import docx
from firebase_admin import initialize_app, firestore, storage

class FirebaseService:
    def __init__(self):
        try:
            # This will work in a Cloud environment where GOOGLE_APPLICATION_CREDENTIALS is set
            initialize_app()
        except ValueError:
            # This handles local development where the app might be initialized multiple times
            print("Firebase app already initialized.")
        self.db = firestore.client()
        self.storage = storage.bucket()

    def store_document_metadata(self, user_id: str, file_path: str, raw_text: str) -> str:
        """
        Stores document metadata in a user's subcollection in Firestore.
        Returns the ID of the new document.
        """
        doc_ref = self.db.collection("users").document(user_id).collection("user_documents").document()
        doc_ref.set({
            "original_storage_path": file_path,
            "raw_text": raw_text,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        print(f"Document metadata stored in Firestore with ID: {doc_ref.id}")
        return doc_ref.id

    def get_user_documents(self, user_id: str):
        """
        Retrieves a list of documents for a given user.
        """
        docs_ref = self.db.collection("users").document(user_id).collection("user_documents")
        docs = docs_ref.stream()
        user_documents = []
        for doc in docs:
            doc_data = doc.to_dict()
            user_documents.append({
                "id": doc.id,
                "original_storage_path": doc_data.get("original_storage_path"),
                "created_at": doc_data.get("created_at").isoformat()
            })
        return user_documents

    def delete_document(self, user_id: str, document_id: str):
        """
        Deletes a document's metadata from Firestore and the file from Storage.
        """
        doc_ref = self.db.collection("users").document(user_id).collection("user_documents").document(document_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ValueError("Document not found")

        # Delete the file from Cloud Storage
        storage_path = doc.to_dict().get("original_storage_path")
        if storage_path:
            blob = self.storage.blob(storage_path)
            blob.delete()
            print(f"Deleted {storage_path} from Cloud Storage")

        # Delete the Firestore document
        doc_ref.delete()
        print(f"Deleted document {document_id} from Firestore")

    def store_feedback(self, feedback: str, job_description: str, generated_text: str):
        """
        Stores user feedback in a dedicated collection.
        """
        self.db.collection("generation_feedback").add({
            "feedback": feedback,
            "job_description": job_description,
            "generated_text": generated_text,
            "created_at": firestore.SERVER_TIMESTAMP
        })

    def download_file_from_storage(self, bucket_name: str, file_path: str) -> bytes:
        """Downloads a file from Firebase Cloud Storage."""
        bucket = storage.bucket(bucket_name)
        blob = bucket.blob(file_path)
        return blob.download_as_bytes()

    def extract_text_from_file(self, file_bytes: bytes, content_type: str) -> str:
        """Extracts raw text from PDF or DOCX file bytes."""
        if content_type == "application/pdf":
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            return "".join(page.extract_text() for page in pdf_reader.pages)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join(para.text for para in doc.paragraphs)
        else:
            raise ValueError(f"Unsupported file type for text extraction: {content_type}")

    @staticmethod
    def get_user_id_from_path(file_path: str) -> str:
        """
        Extracts the user ID from the file path.
        Assumes file paths are in the format: user_uploads/{user_id}/{filename}
        """
        parts = file_path.split('/')
        if len(parts) > 1 and parts[0] == "user_uploads":
            return parts[1]
        raise ValueError(f"Could not extract user ID from file path: {file_path}")

# A single, shared instance of the service
firebase_service = FirebaseService()
