export default function CompanyCheckboxes({ companies, selected, onChange }) {
  function toggle(id) {
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  }

  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginTop: 4 }}>
      {companies.map((c) => (
        <label key={c.id} style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 400 }}>
          <input type="checkbox" checked={selected.includes(c.id)} onChange={() => toggle(c.id)} />
          {c.name}
        </label>
      ))}
    </div>
  );
}
