// Tej - 78879925

/**
 * API service for communicating with the AI Code Generator backend.
 * Provides methods for code generation, status tracking, and LLM usage monitoring.
 */
import axios from 'axios';
import { CodeRequest, CodeGenerationResult, UsageSummary } from '../types';

// Backend API base URL - configurable via environment variable
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8500/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  /**
   * Generate code from requirements
   */
  generateCode: async (request: CodeRequest): Promise<CodeGenerationResult> => {
    const response = await api.post<CodeGenerationResult>('/generate', request);
    return response.data;
  },

  /**
   * Get status of a code generation request
   */
  getStatus: async (requestId: string): Promise<CodeGenerationResult> => {
    const response = await api.get<CodeGenerationResult>(`/status/${requestId}`);
    return response.data;
  },

  /**
   * Submit clarification answer
   */
  submitClarification: async (
    requestId: string,
    questionId: string,
    answer: string
  ): Promise<void> => {
    await api.post(`/clarifications/${requestId}`, {
      question_id: questionId,
      answer: answer,
    });
  },

  /**
   * Get LLM usage statistics
   */
  getUsage: async (): Promise<UsageSummary> => {
    const response = await api.get<UsageSummary>('/usage');
    return response.data;
  },

  /**
   * Reset LLM usage statistics
   */
  resetUsage: async (): Promise<void> => {
    await api.post('/usage/reset');
  },

  /**
   * Health check
   */
  healthCheck: async (): Promise<{ status: string; service: string }> => {
    const response = await api.get('/health');
    return response.data;
  },

  /**
   * Get agent information
   */
  getAgents: async (): Promise<any> => {
    const response = await api.get('/agents');
    return response.data;
  },

  /**
   * Login user
   */
  login: async (email: string, password: string): Promise<{ token: string; user: any }> => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },

  /**
   * Signup user
   */
  signup: async (email: string, password: string, name: string): Promise<{ token: string; user: any }> => {
    const response = await api.post('/auth/signup', { email, password, name });
    return response.data;
  },
};

export default apiService;
