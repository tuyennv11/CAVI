import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch, apiUpload } from "../api";
import AddressFields from "../components/AddressFields";
import Avatar from "../components/Avatar";
import CompanyCheckboxes from "../components/CompanyCheckboxes";
import { useAuth } from "../AuthContext";
import {
  EDUCATION_LEVEL_LABEL,
  EMPLOYEE_DOC_TYPE_LABEL,
  EMPLOYMENT_TYPE_LABEL,
  formatMoney,
  GENDER_LABEL,
  WORK_STATUS_LABEL,
} from "../constants";

const BASE_TABS = [
  { key: "overview", label: "Tổng quan" },
  { key: "work", label: "Công việc" },
  { key: "documents", label: "Hồ sơ" },
  { key: "training", label: "Đào tạo & năng lực" },
  { key: "emergency", label: "Liên hệ khẩn cấp" },
  { key: "kpi", label: "KPI" },
  { key: "history", label: "Lịch sử thay đổi" },
];

const EMPTY_DOC = { doc_type: "personal", title: "", number: "", issued_at: "", issued_place: "", expires_at: "", note: "" };
const EMPTY_TRAINING = { course_name: "", started_at: "", ended_at: "", trainer: "", result: "", note: "" };
const EMPTY_CONTACT = { name: "", relationship: "", phone: "", address: "", note: "" };

function isExpiringSoon(dateStr) {
  if (!dateStr) return false;
  const days = (new Date(dateStr) - new Date()) / 86400000;
  return days < 30;
}

export default function EmployeeDetail() {
  const { id } = useParams();
  const { user: currentUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [positions, setPositions] = useState([]);
  const [tab, setTab] = useState("overview");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [documents, setDocuments] = useState([]);
  const [docForm, setDocForm] = useState(EMPTY_DOC);
  const [docFile, setDocFile] = useState(null);

  const [trainings, setTrainings] = useState([]);
  const [trainingForm, setTrainingForm] = useState(EMPTY_TRAINING);

  const [contacts, setContacts] = useState([]);
  const [contactForm, setContactForm] = useState(EMPTY_CONTACT);

  const [kpiHistory, setKpiHistory] = useState([]);
  const [changeLog, setChangeLog] = useState([]);

  async function load() {
    try {
      const p = await apiFetch(`/api/hr/employees/${id}/`);
      setProfile(p);
      setForm({
        preferred_name: p.preferred_name || "",
        gender: p.gender || "",
        phone: p.phone || "",
        date_of_birth: p.date_of_birth || "",
        id_number: p.id_number || "",
        country: p.country || "",
        province: p.province || "",
        district: p.district || "",
        ward: p.ward || "",
        street_address: p.street_address || "",
        position: p.position || "",
        manager: p.manager || "",
        work_location: p.work_location || "",
        job_description: p.job_description || "",
        contract_type: p.contract_type || "",
        contract_started_at: p.contract_started_at || "",
        contract_expires_at: p.contract_expires_at || "",
        department: p.department || "",
        work_status: p.work_status,
        employment_type: p.employment_type,
        hired_at: p.hired_at || "",
        resigned_at: p.resigned_at || "",
        education_level: p.education_level || "",
        major: p.major || "",
        skills: p.skills || "",
        companies: (p.companies_detail || []).map((c) => c.id),
      });
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadDocuments() {
    const data = await apiFetch(`/api/hr/documents/?profile=${id}`);
    setDocuments(data.results ?? data);
  }

  async function loadContacts() {
    const data = await apiFetch(`/api/hr/emergency-contacts/?profile=${id}`);
    setContacts(data.results ?? data);
  }

  async function loadTrainings() {
    const data = await apiFetch(`/api/hr/trainings/?profile=${id}`);
    setTrainings(data.results ?? data);
  }

  async function loadKpi() {
    const data = await apiFetch(`/api/hr/employees/${id}/kpi-history/`);
    setKpiHistory(data);
  }

  async function loadChangeLog() {
    const data = await apiFetch(`/api/hr/employees/${id}/change-log/`);
    setChangeLog(data);
  }

  useEffect(() => {
    load();
    loadDocuments();
    loadTrainings();
    loadContacts();
    loadKpi();
    loadChangeLog();
    apiFetch("/api/companies/").then(setCompanies).catch(() => {});
    apiFetch("/api/hr/positions/").then(setPositions).catch(() => {});
  }, [id]);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const payload = { ...form };
      // API nhận JSON (không phải multipart) nên chuỗi rỗng không tự chuyển thành null cho field
      // ngày tháng/khoá ngoại — phải tự chuyển tay, không thì DRF báo "Ngày sai định dạng".
      [
        "manager", "country", "province", "district", "ward",
        "date_of_birth", "contract_started_at", "contract_expires_at", "hired_at", "resigned_at",
      ].forEach((k) => {
        if (payload[k] === "") payload[k] = null;
      });
      const updated = await apiFetch(`/api/hr/employees/${id}/`, { method: "PATCH", body: JSON.stringify(payload) });
      setProfile(updated);
      setSaved(true);
      loadChangeLog();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleAvatarChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.set("avatar", file);
    try {
      const updated = await apiUpload(`/api/hr/employees/${id}/`, fd, "PATCH");
      setProfile(updated);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAddDocument(e) {
    e.preventDefault();
    try {
      const fd = new FormData();
      fd.set("profile", id);
      Object.entries(docForm).forEach(([k, v]) => fd.set(k, v));
      if (docFile) fd.set("file", docFile);
      await apiUpload("/api/hr/documents/", fd);
      setDocForm(EMPTY_DOC);
      setDocFile(null);
      loadDocuments();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteDocument(docId) {
    await apiFetch(`/api/hr/documents/${docId}/`, { method: "DELETE" });
    loadDocuments();
  }

  async function handleAddTraining(e) {
    e.preventDefault();
    try {
      const payload = { ...trainingForm, profile: id };
      ["started_at", "ended_at"].forEach((k) => {
        if (payload[k] === "") payload[k] = null;
      });
      await apiFetch("/api/hr/trainings/", { method: "POST", body: JSON.stringify(payload) });
      setTrainingForm(EMPTY_TRAINING);
      loadTrainings();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteTraining(trainingId) {
    await apiFetch(`/api/hr/trainings/${trainingId}/`, { method: "DELETE" });
    loadTrainings();
  }

  async function handleAddContact(e) {
    e.preventDefault();
    try {
      await apiFetch("/api/hr/emergency-contacts/", {
        method: "POST",
        body: JSON.stringify({ ...contactForm, profile: id }),
      });
      setContactForm(EMPTY_CONTACT);
      loadContacts();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteContact(contactId) {
    await apiFetch(`/api/hr/emergency-contacts/${contactId}/`, { method: "DELETE" });
    loadContacts();
  }

  if (error && !profile) return <p className="error">{error}</p>;
  if (!profile || !form) return <p className="muted">Đang tải...</p>;

  const TABS = BASE_TABS;
  // Trang này (khác với "Hồ sơ cá nhân") chỉ Quản lý/Nhân sự sửa được — Kế toán chỉ có quyền xem,
  // "Lưu thay đổi" phải ẩn đi, không thì bấm Lưu sẽ luôn báo lỗi 403 dù các ô nhìn như sửa được.
  const canEditProfile = currentUser?.is_manager || currentUser?.is_hr;

  return (
    <div>
      <div className="page-head">
        <div className="row-name" style={{ gap: 14 }}>
          <label style={{ cursor: "pointer" }}>
            <Avatar name={profile.full_name} photo={profile.avatar} size="lg" />
            <input type="file" accept="image/*" hidden onChange={handleAvatarChange} />
          </label>
          <div>
            <h1 style={{ margin: 0 }}>{profile.preferred_name || profile.full_name}</h1>
            <div className="page-head-sub">
              {profile.employee_code} · {profile.position_name || "Chưa có chức vụ"} ·{" "}
              {profile.department_name || "Chưa có phòng ban"}
              {(profile.companies_detail || []).length > 0 && (
                <>
                  {" · "}
                  {profile.companies_detail.map((c) => c.code).join(", ")}
                </>
              )}
            </div>
          </div>
        </div>
        {canEditProfile && (
          <button onClick={handleSave} disabled={saving}>
            {saving ? "Đang lưu..." : saved ? "Đã lưu" : "Lưu thay đổi"}
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.key} className={`tab-btn${tab === t.key ? " active" : ""}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="panel field-grid">
          <label>
            Tên thường gọi
            <input value={form.preferred_name} onChange={(e) => setForm({ ...form, preferred_name: e.target.value })} />
          </label>
          <label>
            Giới tính
            <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
              <option value="">—</option>
              {Object.entries(GENDER_LABEL).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ngày sinh
            <input type="date" value={form.date_of_birth} onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} />
          </label>
          <label>
            Số điện thoại
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </label>
          <label>
            Số CCCD/CMND
            <input value={form.id_number} onChange={(e) => setForm({ ...form, id_number: e.target.value })} />
          </label>
          <label>
            Địa chỉ
            <AddressFields value={form} onChange={(addr) => setForm({ ...form, ...addr })} />
          </label>
          <label>
            Trình độ
            <select value={form.education_level} onChange={(e) => setForm({ ...form, education_level: e.target.value })}>
              <option value="">—</option>
              {Object.entries(EDUCATION_LEVEL_LABEL).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label>
            Chuyên môn
            <input value={form.major} onChange={(e) => setForm({ ...form, major: e.target.value })} />
          </label>
          <label>
            Kỹ năng
            <textarea rows={2} placeholder="Cách nhau bằng dấu phẩy" value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} />
          </label>
        </div>
      )}

      {tab === "work" && (
        <div className="panel field-grid">
          <label>
            Chức vụ
            <select value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })}>
              <option value="">—</option>
              {positions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.department_name})
                </option>
              ))}
            </select>
          </label>
          <label>
            Phòng ban
            {/* Tự điền theo Chức vụ đã chọn — không chọn tay được nữa (xem Profile.department: editable=False) */}
            <input value={profile.department_name || "—"} disabled readOnly />
          </label>
          <label>
            Địa điểm làm việc
            <input value={form.work_location} onChange={(e) => setForm({ ...form, work_location: e.target.value })} />
          </label>
          <label>
            Mô tả công việc
            <textarea rows={3} value={form.job_description} onChange={(e) => setForm({ ...form, job_description: e.target.value })} />
          </label>
          <label>
            Loại hợp đồng
            <input value={form.contract_type} onChange={(e) => setForm({ ...form, contract_type: e.target.value })} />
          </label>
          <label>
            Ngày bắt đầu hợp đồng
            <input type="date" value={form.contract_started_at} onChange={(e) => setForm({ ...form, contract_started_at: e.target.value })} />
          </label>
          <label>
            Ngày hết hạn hợp đồng
            <input type="date" value={form.contract_expires_at} onChange={(e) => setForm({ ...form, contract_expires_at: e.target.value })} />
          </label>
          <label>
            Loại nhân sự
            <select value={form.employment_type} onChange={(e) => setForm({ ...form, employment_type: e.target.value })}>
              {Object.entries(EMPLOYMENT_TYPE_LABEL).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label>
            Tình trạng nhân sự
            <select value={form.work_status} onChange={(e) => setForm({ ...form, work_status: e.target.value })}>
              {Object.entries(WORK_STATUS_LABEL).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ngày vào làm
            <input type="date" value={form.hired_at} onChange={(e) => setForm({ ...form, hired_at: e.target.value })} />
          </label>
          <label>
            Ngày nghỉ việc
            <input type="date" value={form.resigned_at} onChange={(e) => setForm({ ...form, resigned_at: e.target.value })} />
          </label>
          <label>
            Thuộc công ty
            <CompanyCheckboxes
              companies={companies}
              selected={form.companies}
              onChange={(companies) => setForm({ ...form, companies })}
            />
          </label>
        </div>
      )}

      {tab === "documents" && (
        <div className="panel">
          <form className="field-grid" onSubmit={handleAddDocument} style={{ marginBottom: 14 }}>
            <select value={docForm.doc_type} onChange={(e) => setDocForm({ ...docForm, doc_type: e.target.value })}>
              {Object.entries(EMPLOYEE_DOC_TYPE_LABEL).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
            <input placeholder="Tên giấy tờ" required value={docForm.title} onChange={(e) => setDocForm({ ...docForm, title: e.target.value })} />
            <input placeholder="Số giấy tờ" value={docForm.number} onChange={(e) => setDocForm({ ...docForm, number: e.target.value })} />
            <label>
              Ngày cấp
              <input type="date" value={docForm.issued_at} onChange={(e) => setDocForm({ ...docForm, issued_at: e.target.value })} />
            </label>
            <input placeholder="Nơi cấp" value={docForm.issued_place} onChange={(e) => setDocForm({ ...docForm, issued_place: e.target.value })} />
            <label>
              Ngày hết hạn
              <input type="date" value={docForm.expires_at} onChange={(e) => setDocForm({ ...docForm, expires_at: e.target.value })} />
            </label>
            <input type="file" onChange={(e) => setDocFile(e.target.files[0] ?? null)} />
            <button type="submit">+ Thêm giấy tờ</button>
          </form>

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Loại</th>
                  <th>Tên</th>
                  <th>Số</th>
                  <th>Ngày cấp</th>
                  <th>Hết hạn</th>
                  <th>File</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {documents.map((d) => (
                  <tr key={d.id}>
                    <td>{EMPLOYEE_DOC_TYPE_LABEL[d.doc_type]}</td>
                    <td>{d.title}</td>
                    <td>{d.number || "—"}</td>
                    <td>{d.issued_at || "—"}</td>
                    <td className={isExpiringSoon(d.expires_at) ? "error" : ""}>{d.expires_at || "—"}</td>
                    <td>
                      {d.file ? (
                        <a href={d.file} target="_blank" rel="noreferrer">
                          Xem
                        </a>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <button type="button" className="link-btn" onClick={() => handleDeleteDocument(d.id)}>
                        Xoá
                      </button>
                    </td>
                  </tr>
                ))}
                {documents.length === 0 && (
                  <tr>
                    <td colSpan={7} className="muted">
                      Chưa có giấy tờ nào.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "training" && (
        <div className="panel">
          {canEditProfile && (
            <form className="field-grid" onSubmit={handleAddTraining} style={{ marginBottom: 14 }}>
              <input placeholder="Khoá đào tạo" required value={trainingForm.course_name} onChange={(e) => setTrainingForm({ ...trainingForm, course_name: e.target.value })} />
              <label>
                Ngày bắt đầu
                <input type="date" value={trainingForm.started_at} onChange={(e) => setTrainingForm({ ...trainingForm, started_at: e.target.value })} />
              </label>
              <label>
                Ngày kết thúc
                <input type="date" value={trainingForm.ended_at} onChange={(e) => setTrainingForm({ ...trainingForm, ended_at: e.target.value })} />
              </label>
              <input placeholder="Người/đơn vị đào tạo" value={trainingForm.trainer} onChange={(e) => setTrainingForm({ ...trainingForm, trainer: e.target.value })} />
              <input placeholder="Kết quả" value={trainingForm.result} onChange={(e) => setTrainingForm({ ...trainingForm, result: e.target.value })} />
              <button type="submit">+ Thêm khoá đào tạo</button>
            </form>
          )}

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Khoá đào tạo</th>
                  <th>Bắt đầu</th>
                  <th>Kết thúc</th>
                  <th>Người/đơn vị đào tạo</th>
                  <th>Kết quả</th>
                  {canEditProfile && <th></th>}
                </tr>
              </thead>
              <tbody>
                {trainings.map((t) => (
                  <tr key={t.id}>
                    <td>{t.course_name}</td>
                    <td>{t.started_at || "—"}</td>
                    <td>{t.ended_at || "—"}</td>
                    <td>{t.trainer || "—"}</td>
                    <td>{t.result || "—"}</td>
                    {canEditProfile && (
                      <td>
                        <button type="button" className="link-btn" onClick={() => handleDeleteTraining(t.id)}>
                          Xoá
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
                {trainings.length === 0 && (
                  <tr>
                    <td colSpan={6} className="muted">
                      Chưa có khoá đào tạo nào.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "emergency" && (
        <div className="panel">
          <form className="field-grid" onSubmit={handleAddContact} style={{ marginBottom: 14 }}>
            <input placeholder="Họ tên" required value={contactForm.name} onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })} />
            <input placeholder="Quan hệ (vd: Vợ, Bố...)" value={contactForm.relationship} onChange={(e) => setContactForm({ ...contactForm, relationship: e.target.value })} />
            <input placeholder="Số điện thoại" value={contactForm.phone} onChange={(e) => setContactForm({ ...contactForm, phone: e.target.value })} />
            <input placeholder="Địa chỉ" value={contactForm.address} onChange={(e) => setContactForm({ ...contactForm, address: e.target.value })} />
            <button type="submit">+ Thêm người liên hệ</button>
          </form>

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Họ tên</th>
                  <th>Quan hệ</th>
                  <th>Số điện thoại</th>
                  <th>Địa chỉ</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {contacts.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td>{c.relationship || "—"}</td>
                    <td>{c.phone || "—"}</td>
                    <td>{c.address || "—"}</td>
                    <td>
                      <button type="button" className="link-btn" onClick={() => handleDeleteContact(c.id)}>
                        Xoá
                      </button>
                    </td>
                  </tr>
                ))}
                {contacts.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted">
                      Chưa có người liên hệ khẩn cấp nào.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "kpi" && (
        <div className="panel">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Tháng</th>
                  <th>Doanh thu</th>
                  <th>Chỉ tiêu</th>
                  <th>% hoàn thành</th>
                </tr>
              </thead>
              <tbody>
                {kpiHistory.map((k) => (
                  <tr key={`${k.year}-${k.month}`}>
                    <td>
                      {k.month}/{k.year}
                    </td>
                    <td>{formatMoney(k.revenue)}</td>
                    <td>{k.revenue_target != null ? formatMoney(k.revenue_target) : "—"}</td>
                    <td>{k.kpi_pct != null ? `${k.kpi_pct}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "history" && (
        <div className="panel">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>Trường thay đổi</th>
                  <th>Giá trị cũ</th>
                  <th>Giá trị mới</th>
                  <th>Người sửa</th>
                </tr>
              </thead>
              <tbody>
                {changeLog.map((l) => (
                  <tr key={l.id}>
                    <td>{new Date(l.changed_at).toLocaleString("vi-VN")}</td>
                    <td>{l.field_label}</td>
                    <td>{l.old_value || "—"}</td>
                    <td>{l.new_value || "—"}</td>
                    <td>{l.changed_by_name || "—"}</td>
                  </tr>
                ))}
                {changeLog.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted">
                      Chưa có thay đổi nào được ghi nhận.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
