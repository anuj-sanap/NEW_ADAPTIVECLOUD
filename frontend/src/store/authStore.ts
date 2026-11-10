// frontend/src/store/authStore.ts
import { create } from 'zustand';
import { Role, User } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  role: Role | null;
  isViewer: boolean;
  setAuth: (user: User, token: string) => void;
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
  isAuthenticated: !!savedToken,
  role: savedUser?.role || null,
  isViewer: savedUser?.role === 'viewer',

  setAuth: (user: User, token: string) => {
    localStorage.setItem('adaptivecloud_token', token);
    localStorage.setItem('adaptivecloud_user', JSON.stringify(user));
    set({
      user,
      token,
      isAuthenticated: true,
      role: user.role,
      isViewer: user.role === 'viewer',
    });
  },

  logout: () => {
    localStorage.removeItem('adaptivecloud_token');
    localStorage.removeItem('adaptivecloud_user');
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      role: null,
      isViewer: false,
    });
  },
}));
