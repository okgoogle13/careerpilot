nix
{ pkgs ? import <nixpkgs> {} }:

let
  pythonWithPackages = pkgs.python3.withPackages (p: with p; [
    pip
    virtualenv
    # Add any other Python packages you need here
    # Firebase Core Libraries
firebase-functions
firebase-admin

# Genkit and Google AI
google-cloud-genkit
google-generativeai

# Vector Database Client
pinecone-client

# Google API Libraries (for Docs, Gmail, Calendar, and Secrets)
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
google-cloud-secret-manager

# Document Parsing Utilities
pypdf
python-docx

# Web Scraping Utilities
requests
beautifulsoup4

# Environment Variable Management (Good Practice)
python-dotenv

  ]);

in
pkgs.mkShell {
  buildInputs = [
    pkgs.nodejs
    pkgs.nodePackages.npm
    pythonWithPackages
    pkgs.firebase-cli
    # Add any other development tools you need here
  ];

  shellHook = ''
    # Set environment variables
    export FIREBASE_PROJECT_ID="YOUR_FIREBASE_PROJECT_ID" # Replace with your actual Firebase Project ID
    export GOOGLE_CLOUD_PROJECT="$FIREBASE_PROJECT_ID" # Often the same as Firebase Project ID
    export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service/account/key.json" # Optional: Path to your service account key file if needed for local development authentication

    # Add variables for secrets managed by Firebase Secret Manager
    # Reminder: In production, fetch secrets directly in Cloud Functions using Secret Manager API
    export GENKIT_API_KEY="YOUR_GENKIT_API_KEY" # Replace with your Genkit API Key
    export PINECONE_API_KEY="YOUR_PINECONE_API_KEY" # Replace with your Pinecone API Key
    export PINECONE_ENVIRONMENT="YOUR_PINECONE_ENVIRONMENT" # Replace with your Pinecone Environment
    # Add other secrets as needed

    echo "Development environment activated."
    echo "FIREBASE_PROJECT_ID: $FIREBASE_PROJECT_ID"
    # Avoid echoing sensitive secrets in the shell hook output

    # Optional: Activate a Python virtual environment automatically
    # if [ ! -d "firebase/functions/python/venv" ]; then
    #   echo "Creating Python virtual environment..."
    #   virtualenv firebase/functions/python/venv
    # fi
    # source firebase/functions/python/venv/bin/activate
    # echo "Python virtual environment activated."

    # Install Python dependencies (uncomment and adapt if not using a virtual env or if needed)
    # pip install -r firebase/functions/python/requirements.txt

  '';

  # Set environment variables directly using the environment attribute
  # This is an alternative to using export in shellHook
  # environment = {
  #   FIREBASE_PROJECT_ID = "YOUR_FIREBASE_PROJECT_ID"; # Replace
  #   GOOGLE_CLOUD_PROJECT = builtins.getEnv "FIREBASE_PROJECT_ID"; # Can reference other env vars
  # };
}