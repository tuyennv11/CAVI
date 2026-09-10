function initials(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

export default function Avatar({ name, size = "md", photo }) {
  if (photo) {
    return (
      <div className={`avatar${size === "lg" ? " lg" : ""}`} style={{ padding: 0, overflow: "hidden" }}>
        <img src={photo} alt={name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </div>
    );
  }
  return <div className={`avatar${size === "lg" ? " lg" : ""}`}>{initials(name)}</div>;
}
