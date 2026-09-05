import { useEffect, useState } from "react";
import { DragDropContext, Draggable, Droppable } from "@hello-pangea/dnd";
import { Link } from "react-router-dom";
import { apiFetch } from "../api";

const COLUMNS = [
  { key: "new", title: "Mới" },
  { key: "processing", title: "Đang xử lý" },
  { key: "done", title: "Hoàn thành" },
  { key: "cancelled", title: "Huỷ" },
];

async function fetchAllOrders() {
  let path = "/api/orders/";
  let all = [];
  while (path) {
    const data = await apiFetch(path);
    all = all.concat(data.results ?? data);
    if (data.next) {
      const u = new URL(data.next);
      path = u.pathname + u.search;
    } else {
      path = null;
    }
  }
  return all;
}

export default function Pipeline() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAllOrders()
      .then(setOrders)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleDragEnd(result) {
    const { destination, source, draggableId } = result;
    if (!destination) return;
    if (destination.droppableId === source.droppableId) return;

    const orderId = Number(draggableId);
    const newStatus = destination.droppableId;
    setOrders((prev) => prev.map((o) => (o.id === orderId ? { ...o, status: newStatus } : o)));

    try {
      await apiFetch(`/api/orders/${orderId}/`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
    } catch (err) {
      setError(err.message);
      setOrders((prev) => prev.map((o) => (o.id === orderId ? { ...o, status: source.droppableId } : o)));
    }
  }

  if (loading) return <p className="muted">Đang tải...</p>;

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Pipeline bán hàng</h1>
          <div className="page-head-sub">Kéo thả để đổi trạng thái đơn hàng</div>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <DragDropContext onDragEnd={handleDragEnd}>
        <div className="kanban-board">
          {COLUMNS.map((col) => {
            const colOrders = orders.filter((o) => o.status === col.key);
            return (
              <Droppable droppableId={col.key} key={col.key}>
                {(provided) => (
                  <div className="kanban-col" ref={provided.innerRef} {...provided.droppableProps}>
                    <div className="kanban-col-head">
                      <span className="title">{col.title}</span>
                      <span className="kanban-count">{colOrders.length}</span>
                    </div>
                    {colOrders.map((o, index) => (
                      <Draggable draggableId={String(o.id)} index={index} key={o.id}>
                        {(dragProvided, dragSnapshot) => (
                          <div
                            className={`kanban-card${dragSnapshot.isDragging ? " dragging" : ""}`}
                            ref={dragProvided.innerRef}
                            {...dragProvided.draggableProps}
                            {...dragProvided.dragHandleProps}
                          >
                            <div className="kc-id">#{o.id}</div>
                            <div className="kc-customer">
                              <Link to={`/customers/${o.customer}`}>{o.customer_name}</Link>
                            </div>
                            <div className="kc-total">{Number(o.total).toLocaleString("vi-VN")} đ</div>
                          </div>
                        )}
                      </Draggable>
                    ))}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            );
          })}
        </div>
      </DragDropContext>
    </div>
  );
}
