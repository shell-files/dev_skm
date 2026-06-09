import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
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
  userName: null
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

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    updateUserName: (state, action) => {
      state.userName = action.payload;
    },
    updateCompanyName: (state, action) => {
      state.selectedCompany = action.payload;
    }
  },
  extraReducers: (builder) => {  
    builder
      .addCase(checkUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(checkUser.fulfilled, (state, action) => {
        const res = action.payload;
        if(res.status === true) {
          const data = res?.data || {};
          const storedCompanies = Array.isArray(data.companys)
            ? data.companys
            : [];
          state.companies = storedCompanies;
          state.userName = data.userName || null;
          state.selectedCompany = data.selectedCompany || null;
          state.isAuthReady = true;
          state.redirectUrl = "/dashboard";
        } else {
          localStorage.removeItem("companies");
          state.companies = [];
          state.selectedCompany = null;
          state.userName = null;
          state.isAuthReady = false;
          state.redirectUrl = "/";
        }
        state.loading = false;
      })
      .addCase(checkUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    builder
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        const res = action.payload;
        if(res.status === true) {
          const storedCompanies = res.data.companies;
          localStorage.setItem("companies", encodeJson(storedCompanies));
          state.companies = storedCompanies;
          state.userName = res.data.userName;
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
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    builder
      .addCase(logoutUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(logoutUser.fulfilled, (state, action) => {
        const res = action.payload;
        if(res.status === true) {
          localStorage.removeItem('companies');
          state.isAuthReady = false;
          state.redirectUrl = "/";
          state.companies = [];
          state.userName = "";
          state.selectedCompany = null
          state.loading = false;
        } else {
          showDefaultAlert("로그아웃 실패", "접속 오류가 발생 했습니다.", "error");
        }
        state.loading = false;
      })
      .addCase(logoutUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { updateUserName, updateCompanyName } = authSlice.actions;
export default authSlice.reducer;
