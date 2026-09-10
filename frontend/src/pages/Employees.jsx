import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api";
import Avatar from "../components/Avatar";
import { DEPARTMENT_LABEL, WORK_STATUS_LABEL } from "../constants";

export default function Employees() {
  const navigate = useNavigate();
  const [employees, setEmployees] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(q = "") {
    setLoading(true);
    try {
      const params = q ? `?search=${encodeURIComponent(q)}` : "";
      const data = await apiFetch(`/api/hr/employees/${params}`);
      setEmployees(data.results ?? data);
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

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Nhân viên</h1>
          <div className="page-head-sub">{employees.length} nhân viên</div>
        </div>
      </div>

      <div className="toolbar">
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 8, flex: 1 }}>
          <input
            className="search-input"
            placeholder="Tìm theo mã NV, tên, SĐT..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit" className="secondary">
            Tìm
          </button>
        </form>
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Đang tải...</p>
      ) : employees.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có nhân viên nào.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Mã NV</th>
                <th>Nhân viên</th>
                <th>Chức vụ</th>
                <th>Phòng ban</th>
                <th>Tình trạng</th>
              </tr>
            </thead>
            <tbody>
              {employees.map((e) => (
                <tr key={e.id} className="clickable" onClick={() => navigate(`/employees/${e.id}`)}>
                  <td>{e.employee_code}</td>
                  <td>
                    <div className="row-name">
                      <Avatar name={e.full_name} photo={e.avatar} />
                      {e.preferred_name || e.full_name}
                    </div>
                  </td>
                  <td>{e.job_title || "—"}</td>
                  <td>{DEPARTMENT_LABEL[e.department] || "—"}</td>
                  <td>
                    <span className={`badge badge-${e.work_status === "active" ? "done" : e.work_status === "on_leave" ? "processing" : "cancelled"}`}>
                      {WORK_STATUS_LABEL[e.work_status]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
