import { Route, Routes } from "react-router-dom";
import { AuthProvider } from "./AuthContext";
import ProtectedLayout from "./components/ProtectedLayout";
import CustomerDetail from "./pages/CustomerDetail";
import CustomerList from "./pages/CustomerList";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Pipeline from "./pages/Pipeline";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/customers" element={<CustomerList />} />
          <Route path="/customers/:id" element={<CustomerDetail />} />
          <Route path="/pipeline" element={<Pipeline />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
