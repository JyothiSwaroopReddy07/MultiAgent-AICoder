/**
 * TypeScript type definitions
 */

export interface CodeRequest {
  description: string;
  language?: string;
  framework?: string;
  requirements?: string[];
}

export interface Plan {
  overview: string;
  steps: string[];
  file_structure: { [key: string]: string };
  dependencies: string[];
  estimated_complexity: string;
}

export interface GeneratedCode {
  filename: string;
  filepath: string;
  content: string;
  language: string;
  description: string;
}

export interface TestCase {
  name: string;
  filepath: string;
  content: string;
  test_type: string;
  target_file?: string;
}

export interface ReviewFeedback {
  file: string;
  issues: string[];
  suggestions: string[];
  quality_score: number;
  approved: boolean;
}

export interface LLMUsage {
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost?: number;
}

export interface AgentActivity {
  agent: string;
  action: string;
  status: string;
  start_time: string;
  end_time?: string;
  llm_usage?: LLMUsage;
}

export interface CodeGenerationResult {
  request_id: string;
  status: string;
  plan?: Plan;
  code_files: GeneratedCode[];
  test_files: TestCase[];
  review?: ReviewFeedback;
  agent_activities: AgentActivity[];
  total_llm_usage: {
    total_calls: number;
    total_tokens: number;
  };
  total_cost: number;
  created_at: string;
  completed_at?: string;
}

export interface UsageSummary {
  total_calls: number;
  total_tokens: number;
  total_cost: number;
  average_tokens_per_call: number;
  usage_by_model: {
    [key: string]: {
      calls: number;
      tokens: number;
      cost: number;
    };
  };
}
