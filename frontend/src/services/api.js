// frontend/src/services/api.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

export const apiService = {
  /**
   * Generates documents by streaming the response.
   * @param {string} jobDescription - The job description.
   * @param {string} token - The user's Firebase ID token.
   * @param {function} onData - Callback for each data chunk.
   * @param {function} onError - Callback for any errors.
   * @param {function} onComplete - Callback when the stream is complete.
   */
  async generateDocumentsStream(jobDescription, token, onData, onError, onComplete) {
    try {
      const response = await fetch(`${API_BASE_URL}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ job_description: jobDescription, stream: true }),
      });

      if (!response.body) {
        throw new Error("ReadableStream not available");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
            if (buffer.length > 0) {
                 try {
                    const finalData = JSON.parse(buffer);
                    onComplete(finalData);
                } catch (e) {
                    console.error("Error parsing final JSON chunk:", buffer); // Log the problematic buffer
                    onError(new Error("Failed to parse final JSON from stream."));
                }
            }
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete JSON objects from the buffer
        let boundary = buffer.lastIndexOf('\n');
        if (boundary !== -1) {
            let chunk = buffer.substring(0, boundary);
            buffer = buffer.substring(boundary + 1);

            try {
                const parsed = JSON.parse(chunk);
                onData(parsed);
            } catch (e) {
                console.error("Error parsing JSON chunk:", chunk);
                // Don't throw an error, just log it and continue
                // onError(new Error("Failed to parse JSON from stream."));
            }
        }
      }

    } catch (err) {
      console.error("Streaming fetch failed:", err);
      onError(err);
    }
  },

  /**
   * Submits feedback for a generated document.
   * @param {string} feedback - The user's feedback ("good" or "bad").
   * @param {string} jobDescription - The job description used for generation.
   * @param {string} generatedContent - The generated content.
   * @param {string} token - The user's Firebase ID token.
   * @returns {Promise<any>} - The response from the server.
   */
  async submitFeedback(feedback, jobDescription, generatedContent, token) {
    const response = await fetch(`${API_BASE_URL}/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        feedback,
        job_description: jobDescription,
        generated_content: generatedContent,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to submit feedback.');
    }

    return response.json();
  },

  /**
   * Gets the user's documents.
   * @param {string} token - The user's Firebase ID token.
   * @returns {Promise<any>} - The user's documents.
   */
  async getDocuments(token) {
    const response = await fetch(`${API_BASE_URL}/documents`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch documents.');
    }

    return response.json();
  },

  /**
   * Deletes a document.
   * @param {string} documentId - The ID of the document to delete.
   * @param {string} token - The user's Firebase ID token.
   * @returns {Promise<any>} - The response from the server.
   */
  async deleteDocument(documentId, token) {
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to delete document.');
    }

    return response.json();
  },
};
