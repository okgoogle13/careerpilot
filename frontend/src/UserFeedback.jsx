import React from 'react';

function UserFeedback({ onFeedback }) {
  return (
    <div className="user-feedback">
      <p>Was this generation helpful?</p>
      <button onClick={() => onFeedback('positive')}>Helpful</button>
      <button onClick={() => onFeedback('negative')}>Not Helpful</button>
    </div>
  );
}

export default UserFeedback;
