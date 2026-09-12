import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import Modal from "../components/Modal";
import { formatMoney, MOVEMENT_TYPE_LABEL } from "../constants";

const TABS = [
  { key: "products", label: "Sản phẩm" },
  { key: "warehouses", label: "Kho" },
  { key: "movements", label: "Nhật ký kho" },
];

function emptyProductForm() {
  return { sku: "", name: "", unit: "", cost_price: "", sale_price: "" };
}

function emptyWarehouseForm() {
  return { name: "", address: "" };
}

function emptyMovementForm(movementType) {
  return { movement_type: movementType, product: "", warehouse: "", quantity: "", unit_cost: "", supplier: "", note: "" };
}

export default function Inventory() {
  const [tab, setTab] = useState("products");
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [movements, setMovements] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showNewProduct, setShowNewProduct] = useState(false);
  const [productForm, setProductForm] = useState(emptyProductForm());
  const [showNewWarehouse, setShowNewWarehouse] = useState(false);
  const [warehouseForm, setWarehouseForm] = useState(emptyWarehouseForm());
  const [showMovement, setShowMovement] = useState(null); // "in" | "adjustment" | null
  const [movementForm, setMovementForm] = useState(emptyMovementForm("in"));
  const [saving, setSaving] = useState(false);

  async function loadAll() {
    setLoading(true);
    try {
      const [p, w, m, s] = await Promise.all([
        apiFetch("/api/products/"),
        apiFetch("/api/warehouses/"),
        apiFetch("/api/stock-movements/"),
        apiFetch("/api/partners/?is_supplier=true"),
      ]);
      setProducts(p.results ?? p);
      setWarehouses(w.results ?? w);
      setMovements(m.results ?? m);
      setSuppliers(s.results ?? s);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleCreateProduct(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await apiFetch("/api/products/", {
        method: "POST",
        body: JSON.stringify({
          ...productForm,
          cost_price: productForm.cost_price || 0,
          sale_price: productForm.sale_price || 0,
        }),
      });
      setProductForm(emptyProductForm());
      setShowNewProduct(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateWarehouse(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await apiFetch("/api/warehouses/", { method: "POST", body: JSON.stringify(warehouseForm) });
      setWarehouseForm(emptyWarehouseForm());
      setShowNewWarehouse(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateMovement(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {
        movement_type: movementForm.movement_type,
        product: movementForm.product,
        warehouse: movementForm.warehouse,
        quantity: movementForm.quantity,
        note: movementForm.note,
      };
      if (movementForm.movement_type === "in") {
        payload.unit_cost = movementForm.unit_cost || null;
        payload.supplier = movementForm.supplier || null;
      }
      await apiFetch("/api/stock-movements/", { method: "POST", body: JSON.stringify(payload) });
      setShowMovement(null);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function openMovementModal(movementType) {
    setMovementForm(emptyMovementForm(movementType));
    setShowMovement(movementType);
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Tồn kho</h1>
          <div className="page-head-sub">Sản phẩm, kho hàng và nhật ký nhập-xuất</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="secondary" onClick={() => openMovementModal("adjustment")}>
            + Điều chỉnh
          </button>
          <button onClick={() => openMovementModal("in")}>+ Nhập kho</button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab-btn${tab === t.key ? " active" : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="muted">Đang tải...</p>
      ) : tab === "products" ? (
        <div className="panel">
          <div className="panel-head">
            <h3>Sản phẩm ({products.length})</h3>
            <button onClick={() => setShowNewProduct(true)}>+ Thêm sản phẩm</button>
          </div>
          {products.length === 0 ? (
            <p className="muted">Chưa có sản phẩm nào.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Mã hàng</th>
                    <th>Tên hàng hoá</th>
                    <th>ĐVT</th>
                    <th>Giá vốn</th>
                    <th>Giá bán</th>
                    <th>Tồn kho</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.id}>
                      <td>{p.sku}</td>
                      <td>{p.name}</td>
                      <td>{p.unit}</td>
                      <td>{formatMoney(p.cost_price)}</td>
                      <td>{formatMoney(p.sale_price)}</td>
                      <td>
                        <span className={`badge badge-${Number(p.stock_on_hand) > 0 ? "new" : "neutral"}`}>
                          {p.stock_on_hand}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : tab === "warehouses" ? (
        <div className="panel">
          <div className="panel-head">
            <h3>Kho hàng ({warehouses.length})</h3>
            <button onClick={() => setShowNewWarehouse(true)}>+ Thêm kho</button>
          </div>
          {warehouses.length === 0 ? (
            <p className="muted">Chưa có kho nào.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Tên kho</th>
                    <th>Địa chỉ</th>
                    <th>Trạng thái</th>
                  </tr>
                </thead>
                <tbody>
                  {warehouses.map((w) => (
                    <tr key={w.id}>
                      <td>{w.name}</td>
                      <td>{w.address || "—"}</td>
                      <td>
                        <span className={`badge badge-${w.is_active ? "new" : "neutral"}`}>
                          {w.is_active ? "Đang hoạt động" : "Ngừng"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="panel">
          <div className="panel-head">
            <h3>Nhật ký kho ({movements.length})</h3>
          </div>
          {movements.length === 0 ? (
            <p className="muted">Chưa có phát sinh nhập/xuất nào.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Thời gian</th>
                    <th>Loại</th>
                    <th>Sản phẩm</th>
                    <th>Kho</th>
                    <th>Số lượng</th>
                    <th>Giá vốn</th>
                    <th>NCC</th>
                    <th>Ghi chú</th>
                  </tr>
                </thead>
                <tbody>
                  {movements.map((m) => (
                    <tr key={m.id}>
                      <td>{new Date(m.created_at).toLocaleString("vi-VN")}</td>
                      <td>
                        <span
                          className={`badge badge-${
                            m.movement_type === "out" ? "cancelled" : m.movement_type === "in" ? "new" : "processing"
                          }`}
                        >
                          {MOVEMENT_TYPE_LABEL[m.movement_type]}
                        </span>
                      </td>
                      <td>
                        {m.product_sku} — {m.product_name}
                      </td>
                      <td>{m.warehouse_name}</td>
                      <td>{m.quantity}</td>
                      <td>{m.unit_cost ? formatMoney(m.unit_cost) : "—"}</td>
                      <td>{m.supplier_name || "—"}</td>
                      <td>{m.note || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {showNewProduct && (
        <Modal title="Thêm sản phẩm" onClose={() => setShowNewProduct(false)}>
          <form className="field-grid" onSubmit={handleCreateProduct}>
            <label>
              Mã hàng *
              <input
                required
                value={productForm.sku}
                onChange={(e) => setProductForm({ ...productForm, sku: e.target.value })}
              />
            </label>
            <label>
              Tên hàng hoá *
              <input
                required
                value={productForm.name}
                onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
              />
            </label>
            <label>
              ĐVT
              <input
                value={productForm.unit}
                onChange={(e) => setProductForm({ ...productForm, unit: e.target.value })}
              />
            </label>
            <label>
              Giá vốn tham khảo
              <input
                type="number"
                step="0.01"
                value={productForm.cost_price}
                onChange={(e) => setProductForm({ ...productForm, cost_price: e.target.value })}
              />
            </label>
            <label>
              Giá bán mặc định
              <input
                type="number"
                step="0.01"
                value={productForm.sale_price}
                onChange={(e) => setProductForm({ ...productForm, sale_price: e.target.value })}
              />
            </label>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowNewProduct(false)}>
                Huỷ
              </button>
              <button type="submit" disabled={saving}>
                {saving ? "Đang lưu..." : "Thêm sản phẩm"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showNewWarehouse && (
        <Modal title="Thêm kho" onClose={() => setShowNewWarehouse(false)}>
          <form className="field-grid" onSubmit={handleCreateWarehouse}>
            <label>
              Tên kho *
              <input
                required
                value={warehouseForm.name}
                onChange={(e) => setWarehouseForm({ ...warehouseForm, name: e.target.value })}
              />
            </label>
            <label>
              Địa chỉ
              <input
                value={warehouseForm.address}
                onChange={(e) => setWarehouseForm({ ...warehouseForm, address: e.target.value })}
              />
            </label>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowNewWarehouse(false)}>
                Huỷ
              </button>
              <button type="submit" disabled={saving}>
                {saving ? "Đang lưu..." : "Thêm kho"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showMovement && (
        <Modal
          title={showMovement === "in" ? "Nhập kho" : "Điều chỉnh tồn kho"}
          onClose={() => setShowMovement(null)}
        >
          <form className="field-grid" onSubmit={handleCreateMovement}>
            <label>
              Sản phẩm *
              <select
                required
                value={movementForm.product}
                onChange={(e) => setMovementForm({ ...movementForm, product: e.target.value })}
              >
                <option value="">— Chọn sản phẩm —</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.sku} — {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Kho *
              <select
                required
                value={movementForm.warehouse}
                onChange={(e) => setMovementForm({ ...movementForm, warehouse: e.target.value })}
              >
                <option value="">— Chọn kho —</option>
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {showMovement === "in" ? "Số lượng *" : "Số lượng điều chỉnh (âm = giảm) *"}
              <input
                required
                type="number"
                step="0.01"
                value={movementForm.quantity}
                onChange={(e) => setMovementForm({ ...movementForm, quantity: e.target.value })}
              />
            </label>
            {showMovement === "in" && (
              <>
                <label>
                  Giá vốn
                  <input
                    type="number"
                    step="0.01"
                    value={movementForm.unit_cost}
                    onChange={(e) => setMovementForm({ ...movementForm, unit_cost: e.target.value })}
                  />
                </label>
                <label>
                  Nhà cung cấp
                  <select
                    value={movementForm.supplier}
                    onChange={(e) => setMovementForm({ ...movementForm, supplier: e.target.value })}
                  >
                    <option value="">— Không chọn —</option>
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            )}
            <label>
              Ghi chú
              <input
                value={movementForm.note}
                onChange={(e) => setMovementForm({ ...movementForm, note: e.target.value })}
              />
            </label>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowMovement(null)}>
                Huỷ
              </button>
              <button type="submit" disabled={saving}>
                {saving ? "Đang lưu..." : "Lưu"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
