import * as SecureStore from 'expo-secure-store';

// ⚠️  Change this to your server IP/hostname before building
// For local dev with Expo Go on device: use your machine's LAN IP e.g. http://192.168.1.10:3001
// For production: https://your-domain.com
export const API_BASE = 'http://192.168.1.100:3001';

const TOKEN_KEY = 'gk_token';

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

export async function api(path: string, opts: RequestInit = {}): Promise<any> {
  const token = await getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string> || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  return res.json();
}
