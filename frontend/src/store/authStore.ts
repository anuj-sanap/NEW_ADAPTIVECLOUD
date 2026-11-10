// frontend/src/store/authStore.ts
import { create } from 'zustand';
import { Role, User } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  role: Role | null;
  isAdmin: boolean;
  isViewer: boolean;
  setAuth: (user: User, token: string) => void;
  setTokens: (accessToken: string, refreshToken?: string) => void;
  setUser: (usernameOrUser: string | User, role?: string) => void;
  logout: () => void;
}

const savedToken = localStorage.getItem('adaptivecloud_token');
let savedUser: User | null = null;
try {
  const rawUser = localStorage.getItem('adaptivecloud_user');
  if (rawUser) {
    savedUser = JSON.parse(rawUser);
  }
} catch {
  savedUser = null;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: savedUser,
  token: savedToken,
  accessToken: savedToken,
  refreshToken: localStorage.getItem('adaptivecloud_refresh_token'),
  isAuthenticated: !!savedToken,
  role: savedUser?.role || null,
  isAdmin: savedUser?.role === 'admin',
  isViewer: savedUser?.role === 'viewer',

  setAuth: (user: User, token: string) => {
    localStorage.setItem('adaptivecloud_token', token);
    localStorage.setItem('adaptivecloud_user', JSON.stringify(user));
    set({
      user,
      token,
      accessToken: token,
      isAuthenticated: true,
      role: user.role,
      isAdmin: user.role === 'admin',
      isViewer: user.role === 'viewer',
    });
  },

  setTokens: (accessToken: string, refreshToken?: string) => {
    localStorage.setItem('adaptivecloud_token', accessToken);
    if (refreshToken) {
      localStorage.setItem('adaptivecloud_refresh_token', refreshToken);
    }
    set({
      token: accessToken,
      accessToken,
      refreshToken: refreshToken || null,
      isAuthenticated: true,
    });
  },

  setUser: (usernameOrUser: string | User, role?: string) => {
    let resolvedUser: User;
    if (typeof usernameOrUser === 'string') {
      const resolvedRole = (role || 'viewer') as Role;
      resolvedUser = {
        id: 'user-default',
        username: usernameOrUser,
        email: `${usernameOrUser}@adaptivecloud.local`,
        role: resolvedRole,
        is_active: true,
        created_at: new Date().toISOString(),
      };
    } else {
      resolvedUser = usernameOrUser;
    }
    localStorage.setItem('adaptivecloud_user', JSON.stringify(resolvedUser));
    set({
      user: resolvedUser,
      role: resolvedUser.role,
      isAdmin: resolvedUser.role === 'admin',
      isViewer: resolvedUser.role === 'viewer',
    });
  },

  logout: () => {
    localStorage.removeItem('adaptivecloud_token');
    localStorage.removeItem('adaptivecloud_refresh_token');
    localStorage.removeItem('adaptivecloud_user');
    set({
      user: null,
      token: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      role: null,
      isAdmin: false,
      isViewer: false,
    });
  },
}));
