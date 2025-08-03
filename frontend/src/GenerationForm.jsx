// frontend/src/GenerationForm.jsx

import React, { useState } from 'react';
import { apiService } from './services/api';
import ReactMarkdown from 'react-markdown'; // Import for rendering

function GenerationForm({ user }) {
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [generatedContent, setGeneratedContent] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!user) {
      setError("You must be signed in to generate documents.");
      return;
    }
    setLoading(true);
    setGeneratedContent(null);
    setError(null);
    try {
      const token = await user.getIdToken();
      const data = await apiService.generateDocuments(jobDescription, token);
      setGeneratedContent(data);
    } catch (err) {
      setError(err.message || 'Failed to generate document. Please try again.');
      console.error('Error generating document:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Generate Application Documents</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="jobDescription">Job Description:</label>
          <br />
          <textarea
            id="jobDescription"
            rows="10"
            cols="80"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        <button type="submit" disabled={loading || !user}>
          {loading ? 'Generating...' : 'Generate Documents'}
        </button>
      </form>

      {error && <div style={{ color: 'red', marginTop: '1rem' }}>Error: {error}</div>}

      {generatedContent && (
        <div style={{ marginTop: '2rem', textAlign: 'left', border: '1px solid #ccc', padding: '1rem' }}>
          <h3>Generated Content:</h3>
          
          {/* Display the Google Doc link prominently */}
          <div style={{ marginBottom: '1.5rem' }}>
            <strong>
              <a href={generatedContent.document_url} target="_blank" rel="noopener noreferrer">
                Open Your Formatted Google Doc
              </a>
            </strong>
          </div>

          <div>
            <h4>Cover Letter Preview</h4>
            <div className="markdown-preview">
              <ReactMarkdown>{generatedContent.cover_letter_text}</ReactMarkdown>
            </div>
          </div>
          <div style={{ marginTop: '1rem' }}>
            <h4>Resume Summary Preview</h4>
            <div className="markdown-preview">
              <ReactMarkdown>{generatedContent.resume_text}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default GenerationForm;
