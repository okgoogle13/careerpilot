import React, { useState } from 'react';

function GenerationForm() {
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleDocUrl, setGoogleDocUrl] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setGoogleDocUrl(null);
    setError(null);

    try {
      // Replace with your actual Cloud Function URL if not using Firebase Hosting rewrites
      const response = await fetch('/generateApplicationDocuments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ job_description: jobDescription }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'An error occurred during document generation.');
      }

      const data = await response.json();
      setGoogleDocUrl(data.google_doc_url);

    } catch (err) {
 setError('Failed to generate document. Please try again.');
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
            cols="50"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Generating...' : 'Generate Documents'}
        </button>
      </form>

      {googleDocUrl && (
        <div>
          <h3>Generated Document:</h3>
          <a href={googleDocUrl} target="_blank" rel="noopener noreferrer">
            View Google Doc
          </a>
        </div>
      )}

      {error && (
        <div style={{ color: 'red' }}>
          Error: {error}
        </div>
      )}
    </div>
  );
}

export default GenerationForm;