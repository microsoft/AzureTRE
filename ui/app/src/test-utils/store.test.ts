import { createMockStore } from '../test-utils';

describe('mock store', () => {
  test('createMockStore returns a store with operations slice', () => {
    const store = createMockStore();
    const state = store.getState();

    expect(typeof store.dispatch).toBe('function');
    expect(state).toHaveProperty('operations');
    expect(Array.isArray(state.operations.items)).toBe(true);
  });
});
