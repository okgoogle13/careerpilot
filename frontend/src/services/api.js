import { getAuth, getIdToken } from 'firebase/auth';

const API_BASE_URL = 'http://localhost:5001/your-project-id/us-central1/api'; // Replace with your actual project ID

const getAuthToken = async () => {
  const auth = getAuth();
  const user = auth.currentUser;
  if (user) {
    return await getIdToken(user);
  }
  return null;
};

export const generateDocumentsStream = async (jobDescription, onData, onComplete, onError) => {
  const token = await getAuthToken();
  if (!token) {
    onError(new Error('User not authenticated'));
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/generate-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ job_description: jobDescription }),
    });

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete server-sent events
      const events = buffer.split('\n\n');
      buffer = events.pop() || ''; // Keep the last, possibly incomplete event in the buffer

      for (const event of events) {
        if (event.startsWith('event: partial_result\ndata: ')) {
          const dataString = event.substring('event: partial_result\ndata: '.length);
          try {
            const data = JSON.parse(dataString);
            onData(data);
          } catch (error) {
            console.error('Failed to parse partial result:', error);
          }
        } else if (event.startsWith('event: final_result\ndata: ')) {
          const dataString = event.substring('event: final_result\ndata: '.length);
          try {
            const data = JSON.parse(dataString);
            onComplete(data);
          } catch (error) {
            console.error('Failed to parse final result:', error);
          }
        } else if (event.startsWith('event: message\ndata: ')) {
          // You can handle message events if needed
        } else if (event.startsWith('event: error\ndata: ')) {
          const errorMsg = event.substring('event: error\ndata: '.length);
          onError(new Error(errorMsg));
        }
      }
    }
  } catch (error) {
    onError(error);
  }
};
