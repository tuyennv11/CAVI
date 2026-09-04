import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api";

export default function CustomerList() {
  const [customers, setCustomers] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ name: "", company: "", phone: "", email: "", address: "" });
  const [error, setError] = useState("");

  async function load(q = "") {
    setLoading(true);
    try {
      const params = q ? `?search=${encodeURIComponent(q)}` : "";
      const data = await apiFetch(`/api/customers/${params}`);
      setCustomers(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function handleSearchSubmit(e) {
    e.preventDefault();
    load(search);
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    try {
      await apiFetch("/api/customers/", { method: "POST", body: JSON.stringify(form) });
      setForm({ name: "", company: "", phone: "", email: "", address: "" });
      setShowNew(false);
      load(search);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Khách hàng</h1>
        <button onClick={() => setShowNew((v) => !v)}>{showNew ? "Đóng" : "+ Thêm khách hàng"}</button>
      </div>

      <form className="search-bar" onSubmit={handleSearchSubmit}>
        <input
          placeholder="Tìm theo tên, công ty, SĐT, email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="submit">Tìm</button>
      </form>

      {showNew && (
        <form className="card new-customer-form" onSubmit={handleCreate}>
          <input placeholder="Tên khách hàng *" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input placeholder="Công ty" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
          <input placeholder="Số điện thoại" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input placeholder="Địa chỉ" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          <button type="submit">Lưu khách hàng</button>
        </form>
      )}

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Đang tải...</p>
      ) : customers.length === 0 ? (
        <p className="muted">Chưa có khách hàng nào.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Tên</th>
              <th>Công ty</th>
              <th>Điện thoại</th>
              <th>Phụ trách</th>
              <th>Đơn hàng</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id}>
                <td>
                  <Link to={`/customers/${c.id}`}>{c.name}</Link>
                </td>
                <td>{c.company}</td>
                <td>{c.phone}</td>
                <td>{c.assigned_to_detail?.username ?? "—"}</td>
                <td>{c.order_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
