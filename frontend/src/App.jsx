import { Route, Routes } from "react-router-dom";
import { AuthProvider } from "./AuthContext";
import ProtectedLayout from "./components/ProtectedLayout";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Notices from "./pages/Notices";
import PartnerDetail from "./pages/PartnerDetail";
import PartnerList from "./pages/PartnerList";
import Pipeline from "./pages/Pipeline";
import TierRequests from "./pages/TierRequests";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/notices" element={<Notices />} />
          <Route path="/partners" element={<PartnerList />} />
          <Route path="/partners/:id" element={<PartnerDetail />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/tier-requests" element={<TierRequests />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
