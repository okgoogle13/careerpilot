#Genkit

## Personal AI Career Co-pilot

This project is a serverless Progressive Web Application (PWA) designed to assist users in the Australian Community Services sector by generating personalized job application documents using AI.

## Architecture and Technology Stack

The application leverages a modern serverless architecture built on Firebase and integrates various Google Cloud services and external APIs.

*   **Platform:** Firebase (Hosting, Cloud Functions, Firestore, Cloud Scheduler, Secret Manager)
*   **Backend:** Python with the Genkit framework for AI orchestration.
*   **Frontend:** A modern React application built with Vite.
*   **Database:** Cloud Firestore for document metadata and Pinecone as a vector database for semantic search.
*   **AI Models:** Google Gemini for text generation and a Google AI embedding model for vector creation.
*   **Document Generation API:** Google Docs API for formatting and creating final application documents.
*   **Email and Calendar Integration:** Gmail API and Google Calendar API for the job scouting feature.

## Project Structure

*   `/firebase`: Contains Firebase-specific configuration and cloud functions.
*   `/firebase/functions/python`: Houses the Python backend code, including Cloud Functions and Genkit flows.
    *   `main.py`: Contains the implementation of the Cloud Functions: `process_and_embed_document` (triggered by storage uploads), `generateApplicationDocuments` (HTTP triggered Genkit flow for document generation), and `jobScout` (scheduled function for email scanning and calendar event creation).
    *   `requirements.txt`: Lists the Python dependencies for the backend functions.
*   `/frontend`: Contains the React application built with Vite.
    *   `/frontend/src`: Contains the React source code.
        *   `DocumentUpload.jsx`: Component for uploading historical application documents.
        *   `GenerationForm.jsx`: Component for inputting a job description and triggering document generation.
*   `firestore.rules`: Defines security rules for Cloud Firestore.
*   `storage.rules`: Defines security rules for Firebase Storage.

## Getting Started

1.  **Set up Firebase:** Initialize Firebase in your project and set up Hosting, Cloud Functions, Firestore, Cloud Scheduler, and Secret Manager.
2.  **Configure Environment:** Obtain necessary API keys (e.g., Google Gemini, Pinecone) and store sensitive information in Google Secret Manager. Configure these in your development environment (e.g., `.idx/dev.nix`).
3.  **Install Dependencies:**
    *   For the backend: Navigate to `/firebase/functions/python` and run `pip install -r requirements.txt`.
    *   For the frontend: Navigate to `/frontend` and run `npm install`.
4.  **Deploy Backend:** Deploy the Cloud Functions to Firebase.
5.  **Deploy Frontend:** Build and deploy the React application to Firebase Hosting.
6.  **Configure Rules:** Deploy the `firestore.rules` and `storage.rules` to your Firebase project.

## Functionality

*   **Document Ingestion:** Users can upload historical application documents (PDF/DOCX) via the frontend. The `process_and_embed_document` function extracts text, creates embeddings, and stores data in Firestore and Pinecone.
*   **Document Generation:** Users provide a job description through the `GenerationForm`. The `generateApplicationDocuments` Genkit flow retrieves relevant historical documents using RAG, uses Gemini to generate a cover letter and resume, and formats them into a new Google Doc using the Google Docs API. The URL of the generated document is provided to the user.
*   **Job Scouting:** The scheduled `jobScout` function automatically scans for job emails from specified senders and creates corresponding events in the user's Google Calendar.
