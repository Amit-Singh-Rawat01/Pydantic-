import { useState, useEffect } from 'react'
import axios from 'axios'

interface ErrorItem {
  id: number
  service_name: string
  error_type: string
  severity: string
  occurred_at: string
}

const severityColor: Record<string, string> = {
  LOW: 'bg-blue-100 text-blue-700',
  MEDIUM: 'bg-yellow-100 text-yellow-700',
  HIGH: 'bg-orange-100 text-orange-700',
  CRITICAL: 'bg-red-100 text-red-700',
}

function ErrorList() {
  const [errors, setErrors] = useState<ErrorItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get('http://localhost:8000/errors')
      .then((res) => {
        setErrors(res.data.errors)
        setLoading(false)
      })
      .catch((err) => {
        console.error('Fetch failed:', err)
        setLoading(false)
      })
  }, [])

  if (loading) return <p className="p-4">Loading errors...</p>

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Error Dashboard</h1>
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-100 text-left">
            <th className="p-2">Service</th>
            <th className="p-2">Type</th>
            <th className="p-2">Severity</th>
            <th className="p-2">Time</th>
          </tr>
        </thead>
        <tbody>
          {errors.map((err) => (
            <tr key={err.id} className="border-b">
              <td className="p-2">{err.service_name}</td>
              <td className="p-2">{err.error_type}</td>
              <td className="p-2">
                <span className={`px-2 py-1 rounded text-sm ${severityColor[err.severity]}`}>
                  {err.severity}
                </span>
              </td>
              <td className="p-2">{new Date(err.occurred_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ErrorList