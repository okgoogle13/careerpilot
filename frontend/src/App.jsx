import React, { useState, useEffect } from 'react';
import { auth, GoogleAuthProvider, signInWithPopup, onAuthStateChanged } from './services/firebase';
import DocumentUpload from './DocumentUpload';
import GenerationForm from './GenerationForm';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Listen for authentication state changes
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });

    // Unsubscribe from the listener when the component unmounts
    return () => unsubscribe();
  }, []);

  const handleSignIn = async () => {
    const provider = new GoogleAuthProvider();
    try {
      await signInWithPopup(auth, provider);
    } catch (error) {
      console.error("Error signing in:", error);
    }
  };

  const handleSignOut = async () => {
    try {
      await auth.signOut();
    } catch (error) {
      console.error("Error signing out:", error);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>AI Career Co-Pilot</h1>
        {user ? (
          <div>
            <p>Welcome, {user.displayName}!</p>
            <button onClick={handleSignOut}>Sign Out</button>
          </div>
        ) : (
          <button onClick={handleSignIn}>Sign In with Google</button>
        )}
      </header>
      <main>
        {user ? (
          <>
            <DocumentUpload user={user} />
            <GenerationForm user={user} />
          </>
        ) : (
          <p>Please sign in to use the application.</p>
        )}
      </main>
    </div>
  );
}

export default App;
