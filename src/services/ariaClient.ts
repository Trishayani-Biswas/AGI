/**
 * ARIA Client
 * 
 * Typed HTTP client for interacting with the ARIA research backend.
 * Handles retry logic, error parsing, and type-safe requests/responses.
 */

import type {
  ResearchStartRequest,
  ResearchStartResponse,
  ResearchResult,
  ResearchListResponse,
  HealthResponse,
  ErrorResponse,
} from './types';

interface FetchOptions {
  retries?: number;
  timeout?: number;
}

const DEFAULT_RETRIES = 3;
const DEFAULT_TIMEOUT = 10000; // 10 seconds

class AriaClientError extends Error {
  status: number;
  data?: ErrorResponse;

  constructor(
    status: number,
    message: string,
    data?: ErrorResponse
  ) {
    super(message);
    this.name = 'AriaClientError';
    this.status = status;
    this.data = data;
  }
}

/**
 * ARIA API Client
 * 
 * Usage:
 * ```
 * const client = new AriaClient('http://localhost:8000');
 * const { request_id } = await client.startResearch({
 *   topic: 'Climate Change',
 *   query: 'Is climate change real?'
 * });
 * const result = await client.getResearchResult(request_id);
 * ```
 */
export class AriaClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    const url = baseUrl || (typeof import.meta !== 'undefined' && import.meta.env.VITE_BACKEND_URL) || 'http://localhost:8000';
    this.baseUrl = url.replace(/\/$/, ''); // Remove trailing slash
  }

  /**
   * Start a new research run
   */
  async startResearch(
    request: ResearchStartRequest,
    options?: FetchOptions
  ): Promise<ResearchStartResponse> {
    return this.fetch<ResearchStartResponse>(
      '/v1/research/start',
      {
        method: 'POST',
        body: JSON.stringify(request),
      },
      options
    );
  }

  /**
   * Get research result by request ID (includes polling for in-progress)
   */
  async getResearchResult(
    requestId: string,
    options?: FetchOptions
  ): Promise<ResearchResult> {
    return this.fetch<ResearchResult>(
      `/v1/research/${requestId}`,
      { method: 'GET' },
      options
    );
  }

  /**
   * List all research runs with pagination
   */
  async listResearchRuns(
    limit: number = 10,
    offset: number = 0,
    options?: FetchOptions
  ): Promise<ResearchListResponse> {
    const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
    return this.fetch<ResearchListResponse>(
      `/v1/research?${params.toString()}`,
      { method: 'GET' },
      options
    );
  }

  /**
   * Health check
   */
  async health(options?: FetchOptions): Promise<HealthResponse> {
    return this.fetch<HealthResponse>(
      '/health',
      { method: 'GET' },
      options
    );
  }

  /**
   * Internal fetch wrapper with retry logic and timeout
   */
  private async fetch<T>(
    endpoint: string,
    init?: RequestInit,
    options?: FetchOptions
  ): Promise<T> {
    const retries = options?.retries ?? DEFAULT_RETRIES;
    const timeout = options?.timeout ?? DEFAULT_TIMEOUT;

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeout);

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
          ...init,
          headers: {
            'Content-Type': 'application/json',
            ...init?.headers,
          },
          signal: controller.signal,
        });

        clearTimeout(timer);

        // Parse response
        let data: unknown;
        const contentType = response.headers.get('content-type');
        if (contentType?.includes('application/json')) {
          data = await response.json();
        } else {
          data = await response.text();
        }

        // Handle error responses
        if (!response.ok) {
          const errorData = typeof data === 'object' ? (data as ErrorResponse) : undefined;
          throw new AriaClientError(
            response.status,
            errorData?.error || `HTTP ${response.status}`,
            errorData
          );
        }

        return data as T;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        // Don't retry on client errors (4xx)
        if (error instanceof AriaClientError && error.status >= 400 && error.status < 500) {
          throw error;
        }

        // Don't retry on last attempt
        if (attempt === retries) {
          break;
        }

        // Exponential backoff: 100ms, 200ms, 400ms
        await this.sleep(Math.pow(2, attempt) * 100);
      }
    }

    throw lastError || new Error('Unknown error');
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

// Export singleton instance
export const ariaClient = new AriaClient();

export { AriaClientError };
