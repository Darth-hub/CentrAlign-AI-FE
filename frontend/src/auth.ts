// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { UserManager, WebStorageStateStore } from 'oidc-client-ts';
import type { User } from 'oidc-client-ts';
import { OIDC_AUTHORITY, OIDC_CLIENT_ID } from './runtimeConfig';

export interface AuthUser {
  username: string; displayName: string; email: string; role: string; sapUser: string; department: string;
}
let manager: UserManager | undefined;
function auth(): UserManager {
  if (!OIDC_AUTHORITY) throw new Error('Authentication is not configured. Set VITE_OIDC_AUTHORITY in Netlify and redeploy.');
  manager ??= new UserManager({
    authority: OIDC_AUTHORITY, client_id: OIDC_CLIENT_ID,
    redirect_uri: window.location.origin + '/', post_logout_redirect_uri: window.location.origin + '/',
    response_type: 'code', scope: 'openid profile email', automaticSilentRenew: true,
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
  });
  return manager;
}
function convert(user: User): AuthUser {
  const p = user.profile;
  const roles = (p.realm_access as { roles?: string[] } | undefined)?.roles || [];
  const role = ['admin', 'procurement', 'approver', 'ap_clerk', 'executive', 'requester'].find(r => roles.includes(r)) || '';
  return { username: p.preferred_username || p.email || p.sub, displayName: p.name || p.email || p.sub,
    email: p.email || '', role, sapUser: '', department: String(p.department || '') };
}
export async function login(_username?: string, _password?: string): Promise<AuthUser> {
  await auth().signinRedirect();
  throw new Error('Redirecting to secure sign-in…');
}
export async function logout(): Promise<void> { await auth().signoutRedirect(); }
let callback: Promise<User> | undefined;
export async function getAuthUser(): Promise<AuthUser> {
  const params = new URLSearchParams(window.location.search);
  if (params.has('state') && (params.has('code') || params.has('error'))) {
    callback ??= auth().signinRedirectCallback();
    const user = await callback;
    window.history.replaceState({}, document.title, window.location.pathname);
    return convert(user);
  }
  const user = await auth().getUser();
  if (!user || user.expired) throw new Error('Sign in to continue');
  return convert(user);
}
export async function getToken(): Promise<string | null> {
  const user = await auth().getUser();
  return user && !user.expired ? user.access_token : null;
}
export const getAccessToken = getToken;
export async function isAuthenticated(): Promise<boolean> {
  try { await getAuthUser(); return true; } catch { return false; }
}
