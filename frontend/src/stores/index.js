/**
 * index.js
 * 레이어: Store
 * 역할: Redux 스토어 구성 — auth·report 리듀서를 결합하고 직렬화 검사를 비활성화.
 */
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
