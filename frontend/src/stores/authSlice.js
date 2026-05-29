import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { GET, POST, PUT, PATCH, DELETE } from "@utils/Network";
import { encodeJson, safeJsonParse } from "@utils/Base64";
import { showDefaultAlert } from "@components/UI/ServiceAlert";

export const getAuthRedirectUrl = type => type ? "/companyselect" : "/serviceselect";

const initialState = {
  isAuthReady: false,
  redirectUrl: "/",
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
  reducers: {updateUserName: (state, action) => {
      state.userName = action.payload;
    }
  },
  extraReducers: (builder) => {  
    builder
      .addCase(checkUser.fulfilled, (state, action) => {
        const res = action.payload;
        // console.log(res);
        if(res.status === true) {
          const data = res.data;
          const storedCompanies = data.companys; //safeJsonParse(localStorage.getItem("companies"), []);
          state.companies = storedCompanies;
          state.userName = data.userName;
          state.selectedCompany = data.selectedCompany;
          state.isAuthReady = true;
          state.redirectUrl = getAuthRedirectUrl(storedCompanies.length > 0);
        } else {
          localStorage.removeItem("companies");
          state.isAuthReady = false;
          state.redirectUrl = "/";
        }
        state.loading = false;
      });
    builder
      .addCase(logoutUser.fulfilled, (state, action) => {
        const res = action.payload;
        if(res.status === true) {
          localStorage.removeItem('companies');
          state.isAuthReady = false;
          state.redirectUrl = "/";
          state.companies = [];
          state.userName = "";
          state.selectedCompany = {}
          state.loading = false;
        } else {
          showDefaultAlert("로그아웃 실패", "접속 오류가 발생 했습니다.", "error");
        }
        state.loading = false;
      });

    builder
      .addMatcher((action) => action.type.endsWith('/pending'), (state) => {
        state.loading = true;
        state.error = null;
        }
      );
    builder
      .addMatcher((action) => action.type.endsWith('/rejected'), (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { updateUserName } = authSlice.actions;
export default authSlice.reducer;