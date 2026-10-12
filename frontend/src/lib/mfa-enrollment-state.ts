import type { MFAEnrollment } from './mfa-api';

// Enrollment credentials never enter browser history or persistent storage.
let pending: MFAEnrollment | null = null;
// Used only for the immediate setup request; never stored in browser storage.
let setupPassword = '';
export function setPendingEnrollment(value: MFAEnrollment, password = ''): void { pending = value; setupPassword = password; }
export function getPendingEnrollment(): MFAEnrollment | null { return pending; }
export function getEnrollmentPassword(): string { return setupPassword; }
export function clearEnrollmentPassword(): void { setupPassword = ''; }
export function clearPendingEnrollment(): void { pending = null; setupPassword = ''; }
