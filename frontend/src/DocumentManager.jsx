// frontend/src/DocumentManager.jsx

import React, { useState, useEffect } from 'react';
import { apiService } from './services/api';

function DocumentManager({ user }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (user) {
      fetchDocuments();
    }
  }, [user]);

  const fetchDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await user.getIdToken();
      const userDocuments = await apiService.getDocuments(token);
      setDocuments(userDocuments);
    } catch (err) {
      setError('Failed to fetch documents.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (documentId) => {
    if (!window.confirm("Are you sure you want to delete this document?")) return;
    
    try {
      const token = await user.getIdToken();
      await apiService.deleteDocument(documentId, token);
      // Refresh the list after deletion
      fetchDocuments(); 
    } catch (err) {
      setError('Failed to delete document.');
      console.error(err);
    }
  };

  if (!user) {
    return <div>Please sign in to manage your documents.</div>;
  }

  return (
    <div>
      <h2>Your Uploaded Documents</h2>
      {loading && <div>Loading documents...</div>}
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {documents.length > 0 ? (
        <ul>
          {documents.map((doc) => (
            <li key={doc.id}>
              {doc.file_name}
              <button onClick={() => handleDelete(doc.id)} style={{ marginLeft: '1rem' }}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      ) : (
        !loading && <div>You have no uploaded documents.</div>
      )}
    </div>
  );
}

export default DocumentManager;
