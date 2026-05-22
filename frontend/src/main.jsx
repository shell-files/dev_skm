import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from "react-router";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import App from '@/homes/App.jsx'
import { AuthProvider } from '@hooks/AuthContext.jsx'
import '@styles/App.css'
import "@styles/mains.css";
import { Provider } from 'react-redux';
import store from '@stores'

createRoot(document.getElementById('root')).render(
	<StrictMode>
		<BrowserRouter>
			<Provider store={store}>
				<AuthProvider>
					<App />
				</AuthProvider>
			</Provider>
		</BrowserRouter>
	</StrictMode>,
)
