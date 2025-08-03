import json
import genkit
from . import config

class AIService:
    def __init__(self, embedder, generator):
        genkit.init(log_level="INFO")
        self.embedder = embedder
        self.generator = generator

    def embed_text(self, text: str) -> list[float]:
        """Generates a vector embedding for the given text."""
        return genkit.embed(embedder=self.embedder, content=text)

    def generate_document_content(self, job_description: str, context_docs_text: str) -> dict:
        """
        Generates a cover letter and resume summary using the LLM.
        Returns a dictionary with 'cover_letter_text' and 'resume_text'.
        """
        prompt = f"""
        {config.GENERATION_SYSTEM_PROMPT}

        **TARGET JOB DESCRIPTION:**
        {job_description}

        **RELEVANT EXAMPLES FROM USER'S PAST DOCUMENTS (FOR CONTEXT AND STYLE):**
        {context_docs_text}
        """

        try:
            llm_response = genkit.generate(
                model=self.generator,
                prompt=prompt,
                config={"response_format": "json"}
            )
            generated_content = json.loads(llm_response.text())
            return {
                "cover_letter_text": generated_content.get("cover_letter_text", "Error: Could not generate cover letter."),
                "resume_text": generated_content.get("resume_text", "Error: Could not generate resume.")
            }
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error decoding LLM response: {e}")
            return {
                "cover_letter_text": "Error: Could not parse the generated content.",
                "resume_text": "Error: Could not parse the generated content."
            }

# A single, shared instance of the service
ai_service = AIService(
    embedder=config.EMBEDDER_MODEL,
    generator=config.GENERATOR_MODEL
)
