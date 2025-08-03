import React, { useState } from 'react';
import { apiService } from './services/api'; // Import the new API service

function GenerationForm({ user }) { // Receive the user object as a prop
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
      // Get the Firebase ID token from the user object
      const token = await user.getIdToken();

      // Call the new API service
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
            cols="80" // Made it wider
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

      {error && (
        <div style={{ color: 'red', marginTop: '1rem' }}>
          Error: {error}
        </div>
      )}

      {generatedContent && (
        <div style={{ marginTop: '2rem' }}>
          <h3>Generated Content:</h3>
          <div>
            <h4>Cover Letter</h4>
            <textarea
              readOnly
              rows="15"
              cols="80"
              value={generatedContent.cover_letter_text}
            />
          </div>
          <div style={{ marginTop: '1rem' }}>
            <h4>Resume Summary</h4>
            <textarea
              readOnly
              rows="8"
              cols="80"
              value={generatedContent.resume_text}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default GenerationForm;