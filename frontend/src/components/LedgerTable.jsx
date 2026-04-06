/** Таблица журнала ОК — единый вид на профиле и у участников. */
export default function LedgerTable({ rows }) {
  if (!rows.length) {
    return <p className="text-muted small mb-0">Записей пока нет.</p>
  }
  return (
    <div className="table-responsive">
      <table className="table table-sm table-striped table-hover align-middle mb-0">
        <thead className="table-light">
          <tr>
            <th>№</th>
            <th>Сумма ОК</th>
            <th>Комментарий</th>
            <th>Кем</th>
            <th className="text-nowrap">Когда</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((e) => (
            <tr key={e.id}>
              <td>{e.id}</td>
              <td className={e.amount < 0 ? 'fw-semibold text-danger' : e.amount > 0 ? 'text-success' : ''}>
                {e.amount > 0 ? `+${e.amount}` : e.amount}
              </td>
              <td>{e.comment || '—'}</td>
              <td>{e.created_by_label || '—'}</td>
              <td className="text-nowrap small">
                {e.created_at ? new Date(e.created_at).toLocaleString('ru-RU') : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
