import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-visual">
        <div className="brand">
          <img src="/logo.jpg" alt="CAVI" />
          <span>CAVI</span>
        </div>
        <div className="pitch">
          <h2>Vận hành toàn bộ công ty trên một nền tảng.</h2>
          <p>
            Đối tác, đơn hàng, ký duyệt, vận hành, chấm công — quản lý xuyên suốt cho đội ngũ vận tải
            Việt Nam · Campuchia · Lào.
          </p>
        </div>
        <div className="foot">© {new Date().getFullYear()} CAVI</div>
      </div>

      <div className="login-form-side">
        <form className="login-card" onSubmit={handleSubmit}>
          <div>
            <h1>Đăng nhập</h1>
            <p className="subtitle">Nhập tài khoản nội bộ để tiếp tục</p>
          </div>
          <label>
            Tên đăng nhập
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
          </label>
          <label>
            Mật khẩu
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={submitting}>
            {submitting ? "Đang đăng nhập..." : "Đăng nhập"}
          </button>
        </form>
      </div>
    </div>
  );
}
