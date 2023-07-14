import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { completedStates, Operation } from '../../../models/operation';

interface OperationsState {
  items: Array<Operation>
}

const initialState: OperationsState = {
  items: []
};

// note - we can write what looks like state mutations here because the redux toolkit uses
// Immer under the hood to make everything immutable
const operationsSlice = createSlice({
  name: 'operations',
  initialState,
  reducers: {
    setInitialOperations(state, action: PayloadAction<Array<Operation>>) {
      state.items = action.payload;
    },
    addUpdateOperation(state, action: PayloadAction<Operation>) {
      let i = state.items.findIndex((f: Operation) => f.id === action.payload.id);
      if (i !== -1) {
        state.items.splice(i, 1, action.payload);
      } else {
        state.items.push(action.payload);
      }
    },
    dismissCompleted(state) {
      state.items.forEach((o: Operation) => {
        if (completedStates.includes(o.status)) {
          o.dismiss = true;
        }
      });
    }
  }
});

export const { setInitialOperations, addUpdateOperation, dismissCompleted } = operationsSlice.actions;
export default operationsSlice.reducer;
