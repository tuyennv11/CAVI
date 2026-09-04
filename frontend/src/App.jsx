import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./AuthContext";
import ProtectedLayout from "./components/ProtectedLayout";
import CustomerDetail from "./pages/CustomerDetail";
import CustomerList from "./pages/CustomerList";
import Login from "./pages/Login";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/customers" element={<CustomerList />} />
          <Route path="/customers/:id" element={<CustomerDetail />} />
          <Route path="/" element={<Navigate to="/customers" replace />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
