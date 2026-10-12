import '@testing-library/jest-dom/vitest';
import { beforeEach, vi } from 'vitest';

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  vi.restoreAllMocks();
  // jsdom cannot play media; mirror the browser's asynchronous play contract.
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined);
});
