import { configureStore } from "@reduxjs/toolkit";
import operationsReducer from "../components/shared/notifications/operationsSlice";

export const store = configureStore({
  reducer: {
    operations: operationsReducer
  }
});

export type AppDispatch = typeof store.dispatch;
export type RootState = ReturnType<typeof store.getState>;
