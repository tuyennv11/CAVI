import { Route, Routes } from "react-router-dom";
import { AuthProvider } from "./AuthContext";
import ProtectedLayout from "./components/ProtectedLayout";
import ApprovalsPage from "./pages/ApprovalsPage";
import Attendance from "./pages/Attendance";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Notices from "./pages/Notices";
import PartnerDetail from "./pages/PartnerDetail";
import PartnerList from "./pages/PartnerList";
import Pipeline from "./pages/Pipeline";
import Profile from "./pages/Profile";
import ShipmentBatches from "./pages/ShipmentBatches";
import Shipments from "./pages/Shipments";
import TierRequests from "./pages/TierRequests";
import Workspace from "./pages/Workspace";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<Workspace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/notices" element={<Notices />} />
          <Route path="/partners" element={<PartnerList />} />
          <Route path="/partners/:id" element={<PartnerDetail />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/tier-requests" element={<TierRequests />} />
          <Route path="/approvals" element={<ApprovalsPage />} />
          <Route path="/shipments" element={<Shipments />} />
          <Route path="/shipment-batches" element={<ShipmentBatches />} />
          <Route path="/attendance" element={<Attendance />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
