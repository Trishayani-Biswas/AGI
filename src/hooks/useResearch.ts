/**
 * useResearch Hook
 * 
 * Manages polling for research results with automatic retry, timeout, and cleanup.
 * 
 * Usage:
 * ```typescript
 * const { data, loading, error, progress, cancel } = useResearch(requestId);
 * 
 * useEffect(() => {
 *   return cancel; // Cleanup on unmount
 * }, [cancel]);
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { ariaClient, AriaClientError } from '../services/ariaClient';
import type { ResearchResult } from '../services/types';

interface UseResearchOptions {
  pollInterval?: number; // Default: 2000ms
  maxAttempts?: number; // Default: 30 (1 minute at 2s interval)
  enabled?: boolean; // Default: true
}

interface UseResearchResult {
  data: ResearchResult | null;
  loading: boolean;
  error: Error | null;
  progress: number; // 0-100
  cancel: () => void;
}

/**
 * Poll for research results until completion
 */
export function useResearch(
  requestId: string | null,
  options?: UseResearchOptions
): UseResearchResult {
  const pollInterval = options?.pollInterval ?? 2000;
  const maxAttempts = options?.maxAttempts ?? 30;
  const enabled = options?.enabled ?? true;

  const [data, setData] = useState<ResearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [progress, setProgress] = useState(0);

  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const attemptsRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
    attemptsRef.current = 0;
  }, []);

  const fetch = useCallback(async () => {
    if (!requestId) return;

    try {
      setError(null);
      const result = await ariaClient.getResearchResult(requestId);

      setData(result);
      setProgress(result.progress || 0);

      // Stop polling when complete
      if (result.status === 'complete' || result.status === 'error') {
        cancel();
        setLoading(false);
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);

      // Stop on client errors (4xx), continue on server errors (5xx)
      if (err instanceof AriaClientError && err.status >= 400 && err.status < 500) {
        cancel();
      }

      // Stop after max attempts
      attemptsRef.current++;
      if (attemptsRef.current >= maxAttempts) {
        cancel();
        setLoading(false);
      }
    }
  }, [requestId, maxAttempts, cancel]);

  // Initial fetch + setup polling
  useEffect(() => {
    if (!enabled || !requestId) {
      cancel();
      return;
    }

    setLoading(true);
    attemptsRef.current = 0;

    // Fetch immediately
    fetch();

    // Set up polling
    pollingIntervalRef.current = setInterval(fetch, pollInterval);

    // Cleanup on unmount
    return () => {
      cancel();
    };
  }, [requestId, enabled, pollInterval, fetch, cancel]);

  return { data, loading, error, progress, cancel };
}
