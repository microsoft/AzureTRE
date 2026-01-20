import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthApiCall, HttpMethod, ResultType } from './useAuthApiCall';
import { useMsal, useAccount } from '@azure/msal-react';

// Mock MSAL hooks
vi.mock('@azure/msal-react', () => ({
  useMsal: vi.fn(),
  useAccount: vi.fn(),
}));

// Mock MSAL browser with proper InteractionRequiredAuthError class
vi.mock('@azure/msal-browser', () => ({
  InteractionRequiredAuthError: class MockInteractionRequiredAuthError extends Error {
    errorCode: string;
    constructor(errorCode: string, errorMessage: string) {
      super(errorMessage);
      this.name = 'InteractionRequiredAuthError';
      this.errorCode = errorCode;
    }
  },
}));

// Mock config
vi.mock('../config.json', () => ({
  default: {
    treUrl: 'https://test-api.example.com',
    treApplicationId: 'test-app-id',
    debug: false,
  }
}));

// Mock fetch
global.fetch = vi.fn();

describe('useAuthApiCall Hook', () => {
  const mockInstance = {
    acquireTokenSilent: vi.fn(),
    acquireTokenPopup: vi.fn(),
  };

  const mockAccount = {
    homeAccountId: 'test-account-id',
    localAccountId: 'test-local-id',
    username: 'test@example.com',
  };

  const mockTokenResponse = {
    accessToken: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJyb2xlcyI6WyJUUkVBZG1pbiJdLCJzdWIiOiJ0ZXN0LXVzZXIifQ.test-signature',
    account: mockAccount,
  };

  beforeEach(() => {
    vi.clearAllMocks();

    (useMsal as vi.Mock).mockReturnValue({
      instance: mockInstance,
      accounts: [mockAccount],
    });

    (useAccount as vi.Mock).mockReturnValue(mockAccount);

    mockInstance.acquireTokenSilent.mockResolvedValue(mockTokenResponse);

    (global.fetch as vi.Mock).mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ data: 'test' }),
      text: vi.fn().mockResolvedValue('test text'),
    });
  });

  it('makes a GET request successfully', async () => {
    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;

    const response = await apiCall('/api/test', HttpMethod.Get);

    expect(mockInstance.acquireTokenSilent).toHaveBeenCalledWith({
      scopes: ['test-app-id/user_impersonation'],
      account: mockAccount,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'https://test-api.example.com/api/test',
      {
        mode: 'cors',
        headers: {
          Authorization: `Bearer ${mockTokenResponse.accessToken}`,
          'Content-Type': 'application/json',
          etag: '',
        },
        method: 'GET',
      }
    );

    expect(response).toEqual({ data: 'test' });
  });

  it('makes a POST request with body', async () => {
    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;

    const requestBody = { name: 'test' };
    await apiCall('/api/test', HttpMethod.Post, undefined, requestBody);

    expect(global.fetch).toHaveBeenCalledWith(
      'https://test-api.example.com/api/test',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(requestBody),
      })
    );
  });

  it('returns text when ResultType is Text', async () => {
    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;

    const response = await apiCall('/api/test', HttpMethod.Get, undefined, undefined, ResultType.Text);

    expect(response).toBe('test text');
  });

  it('returns undefined when ResultType is None', async () => {
    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;

    const response = await apiCall('/api/test', HttpMethod.Get, undefined, undefined, ResultType.None);

    expect(response).toBeUndefined();
  });

  it('sets roles when setRoles function is provided', async () => {
    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;
    const setRoles = vi.fn();

    await apiCall('/api/test', HttpMethod.Get, undefined, undefined, undefined, setRoles);

    expect(setRoles).toHaveBeenCalledWith(['TREAdmin']);
  });

  it('returns early when tokenOnly is true', async () => {
    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;

    const response = await apiCall('/api/test', HttpMethod.Get, undefined, undefined, undefined, undefined, true);

    expect(global.fetch).not.toHaveBeenCalled();
    expect(response).toBeUndefined();
  });

  it('uses workspace scope when provided', async () => {
    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;

    await apiCall('/api/test', HttpMethod.Get, 'workspace-scope-id');

    expect(mockInstance.acquireTokenSilent).toHaveBeenCalledWith({
      scopes: ['workspace-scope-id/user_impersonation'],
      account: mockAccount,
    });
  });

  it('includes etag when provided', async () => {
    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;

    await apiCall('/api/test', HttpMethod.Get, undefined, undefined, undefined, undefined, false, 'test-etag');

    expect(global.fetch).toHaveBeenCalledWith(
      'https://test-api.example.com/api/test',
      expect.objectContaining({
        headers: expect.objectContaining({
          etag: 'test-etag',
        }),
      })
    );
  });

  it('throws error when API call fails', async () => {
    (global.fetch as vi.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      text: vi.fn().mockResolvedValue('Server Error'),
    });

    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;

    await expect(apiCall('/api/test', HttpMethod.Get)).rejects.toThrow();
  });

  it('returns early when no account is available', async () => {
    (useAccount as vi.Mock).mockReturnValue(null);

    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;

    const response = await apiCall('/api/test', HttpMethod.Get);

    expect(response).toBeUndefined();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('falls back to popup when silent token acquisition fails', async () => {
    // Create a proper InteractionRequiredAuthError using the mocked class
    const { InteractionRequiredAuthError } = await import('@azure/msal-browser') as any;
    const interactionError = new InteractionRequiredAuthError('interaction_required', 'InteractionRequiredAuthError');

    mockInstance.acquireTokenSilent.mockRejectedValue(interactionError);
    mockInstance.acquireTokenPopup.mockResolvedValue(mockTokenResponse);

    const { result } = renderHook(() => useAuthApiCall());
    const apiCall = result.current;

    await apiCall('/api/test', HttpMethod.Get);

    expect(mockInstance.acquireTokenPopup).toHaveBeenCalledWith({
      scopes: ['test-app-id/user_impersonation'],
      account: mockAccount,
    });
  });
});
