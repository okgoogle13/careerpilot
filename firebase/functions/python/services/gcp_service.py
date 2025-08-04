import os
import json
import datetime
from google.cloud import secretmanager
from google.api_core import exceptions
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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
        except exceptions.NotFound:
            print(f"FATAL: Secret '{config.OAUTH_SECRET_NAME}' not found. Ensure it exists.")
            raise
        except exceptions.PermissionDenied:
            print(f"FATAL: Permission denied for secret '{config.OAUTH_SECRET_NAME}'. Ensure the service account has the 'Secret Manager Secret Accessor' role.")
            raise
        except Exception as e:
            print(f"FATAL: An unexpected error occurred while accessing secret '{config.OAUTH_SECRET_NAME}': {e}")
            raise


    def create_google_doc(self, title: str, cover_letter: str, resume_summary: str) -> str:
        """Creates a Google Doc with the provided content and returns its URL."""
        try:
            creds = self.get_oauth_credentials()
            docs_service = build('docs', 'v1', credentials=creds)

            # Create the document
            doc = docs_service.documents().create(body={'title': title}).execute()
            doc_id = doc['documentId']

            # Prepare text and formatting requests
            requests = [
                # Insert "Cover Letter" heading
                {'insertText': {'location': {'index': 1}, 'text': "Cover Letter\n"}},
                {'updateParagraphStyle': {
                    'range': {'startIndex': 1, 'endIndex': 1 + len("Cover Letter")},
                    'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                    'fields': 'namedStyleType'
                }},
                # Insert cover letter text
                {'insertText': {'location': {'index': 1 + len("Cover Letter") + 1}, 'text': f"{cover_letter}\n\n"}},
                # Insert "Resume Summary" heading
                {'insertText': {'location': {'index': 1 + len("Cover Letter") + 1 + len(cover_letter) + 2}, 'text': "Resume Summary\n"}},
                {'updateParagraphStyle': {
                    'range': {
                        'startIndex': 1 + len("Cover Letter") + 1 + len(cover_letter) + 2,
                        'endIndex': 1 + len("Cover Letter") + 1 + len(cover_letter) + 2 + len("Resume Summary")
                    },
                    'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                    'fields': 'namedStyleType'
                }},
                # Insert resume summary text
                {'insertText': {'location': {
                    'index': 1 + len("Cover Letter") + 1 + len(cover_letter) + 2 + len("Resume Summary") + 1
                }, 'text': resume_summary}},
            ]


            # Send the update request
            docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            print(f"Successfully created Google Doc: {doc_url}")
            return doc_url
        except HttpError as e:
            print(f"An error occurred: {e}")
            # Re-raise the exception to be handled by the caller
            raise

    def run_job_scout(self):
        """Scans Gmail for job alerts and creates Calendar reminders."""
        creds = self.get_oauth_credentials()
        gmail_service = build('gmail', 'v1', credentials=creds)
        calendar_service = build('calendar', 'v1', credentials=creds)

        processed_count = 0
        for sender in config.JOB_SCOUT_SENDERS:
            try:
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
            except exceptions.GoogleAPICallError as e:
                print(f"Error processing emails from {sender}: {e}")
            except Exception as e:
                print(f"An unexpected error occurred while processing emails from {sender}: {e}")


        print(f"Job scout finished. Processed {processed_count} emails.")

# A single, shared instance of the service
gcp_service = GCPService(project_id=config.GCP_PROJECT_ID)
