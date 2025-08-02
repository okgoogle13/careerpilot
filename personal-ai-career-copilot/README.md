# Personal AI Career Co-Pilot

## Project Description

The Personal AI Career Co-Pilot is a serverless Progressive Web Application (PWA) designed to assist users in the Australian Community Services sector with generating personalized and tailored job application documents, including resumes, cover letters, and Key Selection Criteria (KSC) responses. By leveraging a sophisticated RAG (Retrieval Augmented Generation) pipeline, the application learns from the user's historical application documents and combines this knowledge with advanced AI capabilities to produce highly relevant content for specific job opportunities.

## Technology Stack

*   **Platform:** Firebase (Hosting, Cloud Functions, Firestore, Cloud Scheduler, Secret Manager)
*   **Backend:** Python with the Genkit framework
*   **AI Models:** Google Gemini (for generation) and a Google AI Embedding Model (for vector creation)
*   **Vector Database:** Pinecone
*   **Frontend:** React (built with Vite)
*   **Primary Database:** Cloud Firestore (for document metadata and content)
*   **Document Formatting:** Google Docs API

## Setup and Running

To set up and run the Personal AI Career Co-Pilot project, follow these steps:

1.  **Clone the Repository:**
    
```
bash
    git clone <repository_url>
    cd personal-ai-career-copilot
    
```
2.  **Firebase Setup:**
    *   Install the Firebase CLI: `npm install -g firebase-tools`
    *   Log in to Firebase: `firebase login`
    *   Initialize your Firebase project within the `firebase` directory. You will need to set up Hosting, Functions, and Firestore.
    *   Configure your Firebase project ID in your environment variables (e.g., in the `.idx/dev.nix` file if using IDX, or manually in your terminal/IDE).
    *   Set up Firebase Firestore according to your data model.

3.  **Frontend Setup:**
    *   Navigate to the frontend directory: `cd frontend`
    *   Install frontend dependencies: `npm install`

4.  **Backend Setup:**
    *   Navigate to the Python functions directory: `cd ../firebase/functions/python`
    *   Set up a Python virtual environment (recommended): `python -m venv venv`
    *   Activate the virtual environment:
        *   On macOS and Linux: `source venv/bin/activate`
        *   On Windows: `.\\venv\\Scripts\\activate`
    *   Install Python dependencies: `pip install -r requirements.txt`

5.  **Pinecone Setup:**
    *   Create a Pinecone account and obtain your API key and environment.
    *   Create a Pinecone index for storing document embeddings.
    *   Configure your Pinecone API key and environment in your environment variables (e.g., in `Secret Manager` for Cloud Functions and potentially in your `.idx/dev.nix` file for local development).

6.  **Google AI Setup:**
    *   Obtain API keys for Google Gemini and the embedding model.
    *   Configure these API keys securely (e.g., using Firebase Secret Manager).

7.  **Build and Deploy:**
    *   Build the frontend: `cd ../../../frontend && npm run build`
    *   Deploy to Firebase: `cd ../firebase && firebase deploy`

8.  **Running Locally (for Development):**
    *   Set up your environment variables (Firebase project ID, Pinecone keys, Google AI keys).
    *   Start the Firebase emulator suite: `firebase emulators:start`
    *   Run the frontend development server: `cd frontend && npm run dev`
    *   Run the Python Genkit backend (this will depend on your specific Genkit setup and how you trigger it during local development, often involves running a script that initializes Genkit and your flows).

**Note:** This is a basic setup guide. More detailed configuration for Firebase services, Genkit flows, embedding pipelines, and Pinecone integration will be required during development.