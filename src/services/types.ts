/**
 * ARIA Research API Type Definitions
 * 
 * These types are derived from PROJECT_SPEC.md section 3 (API Contract)
 * and represent the frontend-facing data structures for the ARIA research system.
 */

// Agent Output (Common to Advocate, Skeptic, Domain)
export interface AgentOutput {
  findings: string[];
  confidence: number;
  sources: string[];
  raw_output: string;
}

// Arbitrator Output (Synthesis only, no raw agent search)
export interface ArbitratorOutput {
  synthesis: string;
  confidence_score: number;
  gaps_identified: string[];
  recommendation: string;
}

// Complete Research Result
export interface ResearchResult {
  request_id: string;
  status: 'queued' | 'running' | 'complete' | 'error';
  topic: string;
  progress?: number; // 0-100 when status === 'running'
  results?: {
    advocate: AgentOutput;
    skeptic: AgentOutput;
    domain: AgentOutput;
    arbitrator: ArbitratorOutput;
  };
  created_at: string;
  completed_at?: string;
  error?: string;
}

// Request to start a research run
export interface ResearchStartRequest {
  topic: string;
  query: string;
}

// Response from POST /v1/research/start
export interface ResearchStartResponse {
  request_id: string;
  status: 'queued';
  created_at: string;
}

// Response from GET /v1/research (list runs)
export interface ResearchListResponse {
  total: number;
  limit: number;
  offset: number;
  runs: ResearchRun[];
}

// Simplified research run for list view
export interface ResearchRun {
  request_id: string;
  topic: string;
  status: 'complete' | 'error';
  created_at: string;
}

// Health check response
export interface HealthResponse {
  status: 'ok';
  version: string;
}

// Error response from backend
export interface ErrorResponse {
  error: string;
  status: number;
  timestamp?: string;
}
