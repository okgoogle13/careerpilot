import axios from 'axios';

const API_URL = '/api'; // Using rewrites, so this points to our backend

const getAuthHeaders = (token) => ({
  headers: {
    'Authorization': `Bearer ${token}`,
  },
});

export const apiService = {
  generateDocuments: async (jobDescription, token) => {
    const response = await axios.post(
      `${API_URL}/generate`,
      { job_description: jobDescription },
      getAuthHeaders(token)
    );
    return response.data;
  },

  sendFeedback: async (feedback, job_description, generated_text, token) => {
    const response = await axios.post(
      `${API_URL}/feedback`,
      { feedback, job_description, generated_text },
      getAuthHeaders(token)
    );
    return response.data;
  },

  getUserDocuments: async (token) => {
    const response = await axios.get(`${API_URL}/documents`, getAuthHeaders(token));
    return response.data;
  },
};
