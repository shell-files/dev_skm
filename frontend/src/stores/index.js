import { configureStore } from "@reduxjs/toolkit";
import authReducer from '@stores/authSlice'
import reportReducer from "@stores/reportSlice";

const store = configureStore({
    reducer:{
        auth: authReducer,
        report: reportReducer
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false,
      }),
});

export default store;
