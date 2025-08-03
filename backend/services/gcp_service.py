import os
import json
import datetime
from google.cloud import secretmanager
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from . import config

class GCPService:
    def __init__(self, project_id: str):
        if not project_id:
            raise ValueError("GCP_PROJECT_ID environment variable is not set.")
        self.project_id = project_id

    def get_oauth_credentials(self) -> Credentials:
        """Fetches stored OAuth credentials from Google Secret Manager."""
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{self.project_id}/secrets/{config.OAUTH_SECRET_NAME}/versions/latest"
        try:
            response = client.access_secret_version(request={"name": name})
            creds_json = response.payload.data.decode("UTF-8")
            return Credentials.from_authorized_user_info(json.loads(creds_json))
        except Exception as e:
            print(f"FATAL: Could not access secret. Ensure it exists and the service account has the 'Secret Manager Secret Accessor' role. Error: {e}")
            raise

    def create_google_doc(self, title: str, cover_letter: str, resume_summary: str) -> str:
        """Creates a Google Doc with the provided content and returns its URL."""
        creds = self.get_oauth_credentials()
        docs_service = build('docs', 'v1', credentials=creds)

        # Create the document
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc['documentId']

        # Prepare text and formatting requests
        requests = [
            {'insertText': {'location': {'index': 1}, 'text': "Cover Letter\n"}},
            {'updateParagraphStyle': {'range': {'startIndex': 1, 'endIndex': 12}, 'paragraphStyle': {'namedStyleType': 'HEADING_1'}, 'fields': 'namedStyleType'}},
            {'insertText': {'location': {'index': 13}, 'text': f"{cover_letter}\n\n"}},
            {'insertText': {'location': {'index': 14 + len(cover_letter)}, 'text': "Resume Summary\n"}},
            {'updateParagraphStyle': {'range': {'startIndex': 14 + len(cover_letter), 'endIndex': 14 + len(cover_letter) + 15}, 'paragraphStyle': {'namedStyleType': 'HEADING_1'}, 'fields': 'namedStyleType'}},
            {'insertText': {'location': {'index': 14 + len(cover_letter) + 16}, 'text': resume_summary}},
        ]

        # Send the update request
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        print(f"Successfully created Google Doc: {doc_url}")
        return doc_url

    def run_job_scout(self):
        """Scans Gmail for job alerts and creates Calendar reminders."""
        creds = self.get_oauth_credentials()
        gmail_service = build('gmail', 'v1', credentials=creds)
        calendar_service = build('calendar', 'v1', credentials=creds)

        processed_count = 0
        for sender in config.JOB_SCOUT_SENDERS:
            results = gmail_service.users().messages().list(userId='me', q=f"is:unread from:{sender}").execute()
            messages = results.get('messages', [])

            for message in messages:
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

# A single, shared instance of the service
gcp_service = GCPService(project_id=config.GCP_PROJECT_ID)
