import { useState, useCallback } from 'react';
import { authenticatedFetch, apiGet } from '../utils/api';

const DEBUG = process.env.NODE_ENV === 'development';

export const useCheckIns = () => {
  const [checkIns, setCheckIns] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchCheckIns = useCallback(async (serviceUserId) => {
    if (!serviceUserId) {
      setCheckIns([]);
      return;
    }
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    try {
      if (DEBUG) console.log('[useCheckIns] Fetching for user:', serviceUserId);
      const data = await apiGet(
        `/service_user_check_ins/?service_user_id=${serviceUserId}`,
        { signal: controller.signal }
      );
      setCheckIns(data || []);
      if (DEBUG) console.log('[useCheckIns] Loaded', data?.length || 0, 'check-ins');
    } catch (err) {
      if (err.name === 'AbortError') {
        if (DEBUG) console.log('[useCheckIns] Fetch aborted');
        return;
      }
      console.error('[useCheckIns] Error fetching:', err);
      setError(err.message);
      setCheckIns([]);
    } finally {
      setIsLoading(false);
    }
    return () => controller.abort();
  }, []);

  /**
   * Save all check-in mutations in one pass.
   *
   * @param {object}   allEdits      { [checkInId]: { check_in, follow_up_message } }
   * @param {string}   serviceUserId used to refresh after save
   * @param {string[]} deletions     check-in IDs to delete/complete (optional)
   * @param {Array}    additions     [{ checkInDate: 'YYYY-MM-DD', message: '' }] (optional)
   */
  const saveAllCheckIns = useCallback(async (
    allEdits = {},
    serviceUserId,
    deletions = [],
    additions = [],
  ) => {
    const hasEdits = Object.keys(allEdits).length > 0;
    const hasDeletions = deletions.length > 0;
    const hasAdditions = additions.length > 0;

    if (!hasEdits && !hasDeletions && !hasAdditions) {
      throw new Error('No changes to save');
    }

    setIsLoading(true);
    setError(null);

    try {
      const promises = [];

      // 1. Edit existing check-ins
      if (hasEdits) {
        if (DEBUG) console.log('[useCheckIns] Saving edits:', allEdits);
        for (const [id, data] of Object.entries(allEdits)) {
          promises.push(
            authenticatedFetch('/service_user_outreach_edit/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                check_in_id: id,
                check_in: data.check_in,
                follow_up_message: data.follow_up_message,
              }),
            })
          );
        }
      }

      // 2. Delete / complete check-ins
      if (hasDeletions) {
        if (DEBUG) console.log('[useCheckIns] Deleting check-ins:', deletions);
        for (const checkInId of deletions) {
          promises.push(
            authenticatedFetch('/service_user_outreach_delete/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ check_in_id: checkInId }),
            })
          );
        }
      }

      // 3. Add new check-ins
      if (hasAdditions) {
        if (DEBUG) console.log('[useCheckIns] Adding check-ins:', additions);
        for (const addition of additions) {
          if (!addition.checkInDate) continue;
          promises.push(
            authenticatedFetch('/service_user_outreach_add/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                service_user_id: serviceUserId,
                check_in: addition.checkInDate,
                follow_up_message: addition.message || '',
              }),
            })
          );
        }
      }

      const results = await Promise.allSettled(promises);
      const failed = results.filter(r => r.status === 'rejected');
      if (failed.length > 0) {
        console.error('[useCheckIns] Some operations failed:', failed);
        throw new Error(`${failed.length} operation(s) failed. Check console for details.`);
      }

      // Refresh after all mutations
      if (serviceUserId) {
        await fetchCheckIns(serviceUserId);
      }

      if (DEBUG) console.log('[useCheckIns] Successfully saved all changes');
    } catch (err) {
      console.error('[useCheckIns] Error saving:', err);
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchCheckIns]);

  const updatePatientLastSession = useCallback(async (serviceUserId, lastSession) => {
    if (!serviceUserId) {
      throw new Error('Service user ID is required');
    }
    setIsLoading(true);
    setError(null);
    try {
      if (DEBUG) console.log('[useCheckIns] Updating last session:', { serviceUserId, lastSession });
      // Use the new dedicated endpoint (matches all_endpoints_additions.py)
      const response = await authenticatedFetch('/update_last_session/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_user_id: serviceUserId,
          last_session: lastSession,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to update last session');
      }
      if (DEBUG) console.log('[useCheckIns] Successfully updated last session');
    } catch (err) {
      console.error('[useCheckIns] Error updating last session:', err);
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refresh = useCallback(async (serviceUserId) => {
    return fetchCheckIns(serviceUserId);
  }, [fetchCheckIns]);

  return {
    checkIns,
    isLoading,
    error,
    fetchCheckIns,
    saveAllCheckIns,
    updatePatientLastSession,
    refresh,
  };
};