// frontend/src/store/__tests__/authStore.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../authStore';

describe('authStore', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.getState().logout();
  });

  it('initializes with null unauthenticated user', () => {
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isViewer).toBe(false);
    expect(state.isAdmin).toBe(false);
  });

  it('sets authentication tokens properly', () => {
    useAuthStore.getState().setTokens('test_access_jwt', 'test_refresh_jwt');
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.token).toBe('test_access_jwt');
    expect(state.accessToken).toBe('test_access_jwt');
    expect(localStorage.getItem('adaptivecloud_token')).toBe('test_access_jwt');
  });

  it('updates role and permissions when user is set', () => {
    useAuthStore.getState().setUser('analyst_user', 'analyst');
    let state = useAuthStore.getState();
    expect(state.user?.username).toBe('analyst_user');
    expect(state.role).toBe('analyst');
    expect(state.isViewer).toBe(false);
    expect(state.isAdmin).toBe(false);

    useAuthStore.getState().setUser('viewer_user', 'viewer');
    state = useAuthStore.getState();
    expect(state.isViewer).toBe(true);
    expect(state.isAdmin).toBe(false);

    useAuthStore.getState().setUser('admin_user', 'admin');
    state = useAuthStore.getState();
    expect(state.isViewer).toBe(false);
    expect(state.isAdmin).toBe(true);
  });

  it('clears state on logout', () => {
    useAuthStore.getState().setTokens('test_token');
    useAuthStore.getState().setUser('admin', 'admin');
    expect(useAuthStore.getState().isAuthenticated).toBe(true);

    useAuthStore.getState().logout();
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(localStorage.getItem('adaptivecloud_token')).toBeNull();
  });
});