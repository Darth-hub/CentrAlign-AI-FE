/** Coalesce concurrent rejected requests into one local sign-out. */
export function createSessionInvalidator(clearSession: () => Promise<void>, notify: () => void) {
  let pending: Promise<void> | undefined;
  return () => {
    pending ??= Promise.resolve().then(clearSession).catch(() => undefined).then(notify);
    return pending;
  };
}
