import React, { useState } from 'react';
import { storage } from './services/firebase'; // Corrected import path
import { ref, uploadBytesResumable, getDownloadURL } from 'firebase/storage';

function DocumentUpload({ user }) { // Accept user prop
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [uploadStatus, setUploadStatus] = useState({});

  const handleFileChange = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0 || !user) { // Check if user is available
      return;
    }

    setUploading(true);
    setUploadProgress({});
    setUploadStatus({});

    const userId = user.uid; // Use the actual user ID

    const uploadTasks = files.map(file => {
      const storageRef = ref(storage, `user_uploads/${userId}/${file.name}`);
      const uploadTask = uploadBytesResumable(storageRef, file);

      uploadTask.on('state_changed',
        (snapshot) => {
          // Observe state change events such as progress, pause, and resume
          const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100;
          setUploadProgress(prev => ({ ...prev, [file.name]: progress }));
        },
        (error) => {
          // Handle unsuccessful uploads
          console.error(`Upload failed for ${file.name}:`, error);
          setUploadStatus(prev => ({ ...prev, [file.name]: `Error: ${error.message}` }));
        },
        () => {
          // Handle successful uploads on complete
          getDownloadURL(uploadTask.snapshot.ref).then((downloadURL) => {
            console.log(`File available at: ${downloadURL}`);
            setUploadStatus(prev => ({ ...prev, [file.name]: 'Success!' }));
          });
        }
      );
      return uploadTask;
    });

    try {
      await Promise.all(uploadTasks.map(task => new Promise((resolve, reject) => {
        task.on('state_changed', null, reject, resolve);
      })));
      setUploading(false);
    } catch (error) {
      setUploading(false);
      console.error("Overall upload process failed:", error);
    }
  };

  return (
    <div>
      <h2>Upload Documents</h2>
      <input
        type="file"
        multiple
        onChange={handleFileChange}
        disabled={uploading}
      />
      {uploading && <p>Uploading files...</p>}
      <div>
        {Object.keys(uploadProgress).map(fileName => (
          <div key={fileName}>
            {fileName}: {uploadProgress[fileName].toFixed(0)}% {uploadStatus[fileName]}
          </div>
        ))}
      </div>
    </div>
  );
}

export default DocumentUpload;