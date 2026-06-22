<<<<<<< HEAD
/**
 * authSlice.js
 * 레이어: Store
 * 역할: 인증 Redux 슬라이스 — 로그인·로그아웃·사용자 정보 조회·갱신 Thunk와 auth 상태 관리.
 */
=======
>>>>>>> origin/skm_test
import { createSlice, createAsyncThunk, isPending, isRejected } from '@reduxjs/toolkit';
import { GET, POST, PUT, PATCH, DELETE } from "@utils/Network";
import { encodeJson, safeJsonParse } from "@utils/Base64";
import { showDefaultAlert } from "@components/UI/ServiceAlert";

export const getAuthRedirectUrl = type => type ? "/companyselect" : "/serviceselect";

const initialState = {
  isAuthReady: false,
  redirectUrl: null,
  companies: safeJsonParse(localStorage.getItem("companies"), []),
  loading: false,
  error: null,
  selectedCompany: null,
  userName: null,
  userEmail: null
};

export const checkUser = createAsyncThunk(
  'auth/checkUser',
  async (credentials, { rejectWithValue }) => {
    try {
      const response = await POST('/auth');
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data);
    }
  }
);

export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async (credentials, { rejectWithValue }) => {
    try {
      const response = await POST('/auth/login', credentials);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data);
    }
  }
);

export const logoutUser = createAsyncThunk(
  'auth/logoutUser',
  async (credentials, { rejectWithValue }) => {
    try {
      const response = await DELETE('/auth');
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data);
    }
  }
);

const authAsyncActions = [checkUser, loginUser, logoutUser];

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    updateUserName: (state, action) => {
      state.userName = action.payload;
    },
    updateCompanyName: (state, action) => {
      state.selectedCompany = action.payload;
    },
    setUserEmail: (state, action) => {
      state.userEmail = action.payload;
    }
  },
  extraReducers: (builder) => {  
    builder
      .addCase(checkUser.fulfilled, (state, action) => {
        const res = action.payload;
        if(res.status === true) {
          const data = res?.data || {};
          const storedCompanies = Array.isArray(data.companys)
            ? data.companys
            : [];
          state.companies = storedCompanies;
          state.userName = data.userName || null;
          state.userEmail = data.userEmail || data.user || null;
          state.selectedCompany = data.selectedCompany || null;
          state.isAuthReady = true;
          state.redirectUrl = "/dashboard";
        } else {
          localStorage.removeItem("companies");
          state.companies = [];
          state.selectedCompany = null;
          state.userName = null;
          state.userEmail = null;
          state.isAuthReady = false;
          state.redirectUrl = "/";
        }
        state.loading = false;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        const res = action.payload;
        if(res.status === true) {
          const storedCompanies = res.data.companies;
          localStorage.setItem("companies", encodeJson(storedCompanies));
          state.companies = storedCompanies;
          state.userName = res.data.userName;
          state.userEmail = res.data.userEmail || null;
          state.selectedCompany = res.data.selectedCompany;
          state.isAuthReady = true;
          state.redirectUrl = "/";
        } else {
          localStorage.removeItem("companies");
          state.isAuthReady = false;
          state.redirectUrl = "/";
          showDefaultAlert("로그인 실패", "이메일 또는 비밀번호가 일치하지 않습니다.", "error");
        }
        state.loading = false;
      })
      .addCase(logoutUser.fulfilled, (state, action) => {
        const res = action.payload;
        if(res.status === true) {
          localStorage.clear();
          state.isAuthReady = false;
          state.redirectUrl = "/";
          state.companies = [];
          state.userName = "";
          state.userEmail = null;
          state.selectedCompany = null
          state.loading = false;
        } else {
          showDefaultAlert("로그아웃 실패", "접속 오류가 발생 했습니다.", "error");
        }
        state.loading = false;
      });

    builder
      .addMatcher(
        isPending(...authAsyncActions), 
        (state) => {
          state.loading = true;
          state.error = null;
        }
      )
      .addMatcher(
        isRejected(...authAsyncActions), 
        (state, action) => {
          state.loading = false;
          state.error = action.payload || action.error.message || '알 수 없는 에러가 발생했습니다.';
        }
      );
  },
});

export const { updateUserName, updateCompanyName, setUserEmail } = authSlice.actions;
export default authSlice.reducer;