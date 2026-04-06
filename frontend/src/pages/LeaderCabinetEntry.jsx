import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getLeaderCabinetEntryPath } from '../api/client'

/** Редирект с /leader: заявки при наличии pending, иначе участники. */
export default function LeaderCabinetEntry() {
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    getLeaderCabinetEntryPath().then((path) => {
      if (!cancelled) navigate(path, { replace: true })
    })
    return () => {
      cancelled = true
    }
  }, [navigate])

  return (
    <div className="d-flex justify-content-center align-items-center p-5 text-muted">
      <span className="spinner-border spinner-border-sm me-2" role="status" />
      Загрузка…
    </div>
  )
}
