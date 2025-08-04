# firebase/functions/python/services/test_ai_service.py

import pytest
from .ai_service import AIService
from genkit.api.dot import Dot
import json

@pytest.fixture
def ai_service_fixture(mocker):
    """Fixture to create an AIService instance with mocked dependencies."""
    # Mock the genkit.init call to avoid actual initialization
    mocker.patch('genkit.init')
    
    # Mock the embedder and generator models
    mock_embedder = "mock_embedder"
    mock_generator = "mock_generator"
    
    return AIService(embedder=mock_embedder, generator=mock_generator)

def test_embed_text(ai_service_fixture, mocker):
    """Test that embed_text calls the genkit.embed function correctly."""
    mock_embed = mocker.patch('genkit.embed', return_value=[0.1, 0.2, 0.3])
    
    text_to_embed = "This is a test sentence."
    embedding = ai_service_fixture.embed_text(text_to_embed)

    mock_embed.assert_called_once_with(embedder="mock_embedder", content=text_to_embed)
    assert embedding == [0.1, 0.2, 0.3]

def test_generate_document_content_success(ai_service_fixture, mocker):
    """Test successful generation of document content."""
    # Create a mock Dot object with a text() method
    mock_llm_response = Dot(data=None)
    mock_llm_response.text = lambda: json.dumps({
        "cover_letter_text": "Dear Hiring Manager...",
        "resume_text": "Experienced professional..."
    })
    
    mock_generate = mocker.patch('genkit.generate', return_value=mock_llm_response)

    job_description = "Software Engineer"
    context_docs_text = "My resume..."
    
    content = ai_service_fixture.generate_document_content(job_description, context_docs_text)

    mock_generate.assert_called_once()
    assert content["cover_letter_text"] == "Dear Hiring Manager..."
    assert content["resume_text"] == "Experienced professional..."

def test_generate_document_content_json_error(ai_service_fixture, mocker):
    """Test handling of JSON decoding errors."""
    # Create a mock Dot object with a text() method that returns invalid JSON
    mock_llm_response = Dot(data=None)
    mock_llm_response.text = lambda: "This is not valid JSON"
    
    mocker.patch('genkit.generate', return_value=mock_llm_response)

    job_description = "Software Engineer"
    context_docs_text = "My resume..."

    content = ai_service_fixture.generate_document_content(job_description, context_docs_text)

    assert "Error: Could not parse the generated content." in content["cover_letter_text"]
    assert "Error: Could not parse the generated content." in content["resume_text"]

@pytest.mark.asyncio
async def test_generate_document_content_stream(ai_service_fixture, mocker):
    """Test the streaming generation of document content."""
    
    # Mock async stream
    async def mock_stream_generator():
        yield Dot(data=None, text='{"cover_letter_chunk": "Dear"}')
        yield Dot(data=None, text='{"resume_chunk": " Experienced"}')

    mocker.patch('genkit.generate', return_value=mock_stream_generator())
    
    job_description = "Streamer"
    context_docs_text = "My streaming history..."
    
    generated_content = []
    async for chunk in ai_service_fixture.generate_document_content_stream(job_description, context_docs_text):
        generated_content.append(chunk)
        
    assert len(generated_content) == 2
    assert generated_content[0] == {"cover_letter_chunk": "Dear"}
    assert generated_content[1] == {"resume_chunk": " Experienced"}

