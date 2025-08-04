import json
import genkit
from . import config
import asyncio

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

    async def generate_document_content_stream(self, job_description: str, context_docs_text: str):
        """
        Generates a cover letter and resume summary using the LLM and streams the response.
        """
        prompt = f"""
        {config.GENERATION_SYSTEM_PROMPT}

        **TARGET JOB DESCRIPTION:**
        {job_description}

        **RELEVANT EXAMPLES FROM USER'S PAST DOCUMENTS (FOR CONTEXT AND STYLE):**
        {context_docs_text}
        """

        llm_response_stream = await genkit.generate(
            model=self.generator,
            prompt=prompt,
            stream=True,
            config={"response_format": "json"}
        )

        async for chunk in llm_response_stream:
            try:
                # Try to parse the chunk as JSON
                yield json.loads(chunk.text())
            except json.JSONDecodeError:
                # If it's not valid JSON, it's likely a partial string
                # In a more robust implementation, you would buffer these
                # and try to parse them together. For now, we'll just
                # yield the raw text as a chunk.
                yield {"cover_letter_chunk": chunk.text(), "resume_chunk": ""}


# A single, shared instance of the service
ai_service = AIService(
    embedder=config.EMBEDDER_MODEL,
    generator=config.GENERATOR_MODEL
)
