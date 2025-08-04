// frontend/src/GenerationForm.test.jsx

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import GenerationForm from './GenerationForm';

// Mock the apiService to avoid actual API calls during testing
vi.mock('./services/api', () => ({
  apiService: {
    generateDocumentsStream: vi.fn((...args) => console.log('generateDocumentsStream called with:', ...args)),
    submitFeedback: vi.fn(),
  },
}));

import { afterEach } from 'vitest';

describe('GenerationForm', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  const mockUser = {
    getIdToken: async () => 'test-token',
  };

  it('renders the form correctly', () => {
    render(<GenerationForm user={mockUser} />);

    expect(screen.getByLabelText(/job description/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate documents/i })).toBeInTheDocument();
  });

  it('enables the generate button when user is logged in and there is a job description', () => {
    render(<GenerationForm user={mockUser} />);
    
    const jobDescriptionInput = screen.getByLabelText(/job description/i);
    const generateButton = screen.getByRole('button', { name: /generate documents/i });

    // Initially, the button is enabled as the user is present
    expect(generateButton).not.toBeDisabled();

    // Clear the job description
    fireEvent.change(jobDescriptionInput, { target: { value: '' } });

    // The button should still be enabled as we don't disable it based on the input field's content
    expect(generateButton).not.toBeDisabled();

    // Write something in the job description
    fireEvent.change(jobDescriptionInput, { target: { value: 'A great job opportunity!' } });

    expect(generateButton).not.toBeDisabled();
  });

  it('disables the generate button when no user is logged in', () => {
    render(<GenerationForm user={null} />);
    const generateButton = screen.getByRole('button', { name: /generate documents/i });
    expect(generateButton).toBeDisabled();
  });

  it('calls the apiService on form submission', async () => {
    const { apiService } = await import('./services/api');
    render(<GenerationForm user={mockUser} />);

    const jobDescriptionInput = screen.getByLabelText(/job description/i);
    const generateButton = screen.getByRole('button', { name: /generate documents/i });

    fireEvent.change(jobDescriptionInput, { target: { value: 'A new job' } });
    fireEvent.click(generateButton);

    expect(apiService.generateDocumentsStream).toHaveBeenCalledWith(
      'A new job',
      'test-token',
      expect.any(Function),
      expect.any(Function),
      expect.any(Function)
    );
  });
});
