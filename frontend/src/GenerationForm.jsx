// frontend/src/GenerationForm.jsx

import React, { useState, useEffect } from 'react';
import { apiService } from './services/api';
import ReactMarkdown from 'react-markdown'; // Import for rendering
import UserFeedback from './UserFeedback'; // Import the new component

function GenerationForm({ user }) {
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [generatedContent, setGeneratedContent] = useState({ cover_letter_text: '', resume_text: '' });
  const [finalContent, setFinalContent] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!user) {
      setError("You must be signed in to generate documents.");
      return;
    }
    setLoading(true);
    setGeneratedContent({ cover_letter_text: '', resume_text: '' });
    setFinalContent(null);
    setError(null);

    try {
      const token = await user.getIdToken();
      apiService.generateDocumentsStream(
        jobDescription,
        token,
        (data) => {
            setGeneratedContent(prev => ({
                cover_letter_text: prev.cover_letter_text + (data.cover_letter_chunk || ''),
                resume_text: prev.resume_text + (data.resume_chunk || ''),
            }));
        },
        (err) => {
            setError('Failed to stream generated content.');
            console.error('Streaming error:', err);
            setLoading(false);
        },
        (finalData) => {
            setFinalContent(finalData);
            setLoading(false);
        }
      );
    } catch (err) {
      setError(err.message || 'Failed to start generation. Please try again.');
      console.error('Error starting generation:', err);
      setLoading(false);
    }
  };

  const handleFeedback = async (feedback) => {
    if (!user || !finalContent) return;
    try {
      const token = await user.getIdToken();
      await apiService.submitFeedback(
        feedback,
        jobDescription,
        JSON.stringify(finalContent), // Or a more specific part of the content
        token
      );
      alert('Thank you for your feedback!');
    } catch (err) {
      console.error('Error submitting feedback:', err);
      alert('Failed to submit feedback.');
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

      {(generatedContent.cover_letter_text || generatedContent.resume_text) && (
        <div style={{ marginTop: '2rem', textAlign: 'left', border: '1px solid #ccc', padding: '1rem' }}>
          <h3>Generated Content:</h3>
          
          {finalContent && (
            <div style={{ marginBottom: '1.5rem' }}>
                <strong>
                <a href={finalContent.document_url} target="_blank" rel="noopener noreferrer">
                    Open Your Formatted Google Doc
                </a>
                </strong>
            </div>
          )}

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
          {finalContent && <UserFeedback onFeedback={handleFeedback} />}
        </div>
      )}
    </div>
  );
}

export default GenerationForm;
