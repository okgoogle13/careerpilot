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
      // Corrected the endpoint to /generate-stream
      const response = await fetch(`${API_BASE_URL}/generate-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ job_description: jobDescription }),
      });

      if (!response.body) {
        throw new Error("ReadableStream not available");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = '';

      // Improved SSE parsing logic
      const processStream = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            if (onComplete) onComplete();
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop(); // Keep the last, possibly incomplete, line in the buffer

          for (const line of lines) {
            if (line.startsWith('event: ')) {
                const eventData = line.split('\n');
                const eventType = eventData[0].substring(7).trim();
                const dataLine = eventData[1].substring(5).trim();
                
                try {
                    const data = JSON.parse(dataLine);
                    if (onData) onData({ event: eventType, data });
                } catch (e) {
                    // Handle non-JSON data, like simple messages
                    if (onData) onData({ event: eventType, data: dataLine });
                }
