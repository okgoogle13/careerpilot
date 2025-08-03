import os
import genkit
from genkit.models import gemini

# Genkit/Gemini Model Configuration
EMBEDDER_MODEL = gemini.text_embedding_004
GENERATOR_MODEL = gemini.gemini_1_5_pro

# Pinecone Configuration
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "career-pilot-index")

# Google Cloud Configuration
GCP_PROJECT_ID = os.getenv("GCLOUD_PROJECT")
OAUTH_SECRET_NAME = "job-scout-token"

# Application-specific prompts
GENERATION_SYSTEM_PROMPT = """
You are an expert career document writer for the Australian Community Services sector.
Your task is to generate a tailored resume summary and a full cover letter based on the provided job description and relevant examples from the user's past documents.

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

# Job Scout Configuration
JOB_SCOUT_SENDERS = ["noreply@s.seek.com.au", "noreply@ethicaljobs.com.au", "donotreply@jora.com"]
