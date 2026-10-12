import type { MFAEnrollment } from './mfa-api';

// Enrollment credentials never enter browser history or persistent storage.
let pending: MFAEnrollment | null = null;
export function setPendingEnrollment(value: MFAEnrollment): void { pending = value; }
export function getPendingEnrollment(): MFAEnrollment | null { return pending; }
export function clearPendingEnrollment(): void { pending = null; }
