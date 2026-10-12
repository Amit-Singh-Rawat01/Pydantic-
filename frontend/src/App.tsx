import { useEffect, useMemo, useState } from 'react'

const API_BASE = 'http://localhost:8000'
const PAGE_SIZE = 10
const SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const

type ErrorItem = {
  id: number
  service_name: string
  error_type: string
  severity: string
  occurred_at: string
  message?: string
}

type Stats = {
  total_errors: number
  errors_per_minute: number
  active_incidents: number
  system_health: 'HEALTHY' | 'WARNING' | 'CRITICAL'
}

type IncidentItem = {
  id: number
  service_name: string
  error_type: string
  severity: string
  status: 'OPEN' | 'RESOLVED'
  occurrence_count: number
  sample_message: string | null
  first_seen: string
  last_seen: string
}

type TimelinePoint = { minute: string; count: number }
type ServiceStat = { service_name: string; count: number }
type SeverityStat = { severity: string; count: number }

const severityClasses: Record<string, string> = {
  LOW: 'bg-blue-100 text-blue-700',
  MEDIUM: 'bg-yellow-100 text-yellow-700',
  HIGH: 'bg-orange-100 text-orange-700',
  CRITICAL: 'bg-red-100 text-red-700',
}

const severityBarColors: Record<string, string> = {
  LOW: 'bg-blue-500',
  MEDIUM: 'bg-yellow-500',
  HIGH: 'bg-orange-500',
  CRITICAL: 'bg-red-500',
}

function App() {
  const [errors, setErrors] = useState<ErrorItem[]>([])
  const [totalErrorCount, setTotalErrorCount] = useState(0)
  const [stats, setStats] = useState<Stats | null>(null)
  const [incidents, setIncidents] = useState<IncidentItem[]>([])
  const [timeline, setTimeline] = useState<TimelinePoint[]>([])
  const [serviceStats, setServiceStats] = useState<ServiceStat[]>([])
  const [severityStats, setSeverityStats] = useState<SeverityStat[]>([])
  const [search, setSearch] = useState('')
  const [serviceFilter, setServiceFilter] = useState('ALL')
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [incidentFilter, setIncidentFilter] = useState<'ALL' | 'OPEN' | 'RESOLVED'>('ALL')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  useEffect(() => {
    let isMounted = true

    const loadDashboard = async () => {
      try {
        const responses = await Promise.all([
          fetch(`${API_BASE}/errors?limit=100`),
          fetch(`${API_BASE}/stats`),
          fetch(`${API_BASE}/incidents`),
          fetch(`${API_BASE}/stats/timeline`),
          fetch(`${API_BASE}/stats/by-service`),
          fetch(`${API_BASE}/stats/severity-breakdown`),
        ])

        const failedResponse = responses.find((response) => !response.ok)
        if (failedResponse) {
          throw new Error(`Dashboard request failed with status ${failedResponse.status}`)
        }

        const [
          errorsData,
          statsData,
          incidentsData,
          timelineData,
          servicesData,
          severityData,
        ] = await Promise.all(responses.map((response) => response.json()))

        if (!isMounted) return

        const errorPayload = errorsData as { errors?: ErrorItem[]; total?: number }
        const timelinePayload = timelineData as { timeline?: TimelinePoint[] }
        setErrors(Array.isArray(errorPayload.errors) ? errorPayload.errors : [])
        setTotalErrorCount(typeof errorPayload.total === 'number' ? errorPayload.total : 0)
        setStats(statsData as Stats)
        setIncidents(Array.isArray(incidentsData) ? incidentsData : [])
        setTimeline(Array.isArray(timelinePayload.timeline) ? timelinePayload.timeline : [])
        setServiceStats(Array.isArray(servicesData) ? servicesData : [])
        setSeverityStats(Array.isArray(severityData) ? severityData : [])
        setLastUpdated(new Date())
        setError('')
      } catch (loadError) {
        console.error('Dashboard refresh failed:', loadError)
        if (isMounted) {
          setError('Unable to load dashboard data. Make sure the backend is running on localhost:8000.')
        }
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    void loadDashboard()
    const intervalId = window.setInterval(() => void loadDashboard(), 5000)

    return () => {
      isMounted = false
      window.clearInterval(intervalId)
    }
  }, [])

  const healthClass = useMemo(() => {
    if (stats?.system_health === 'HEALTHY') return 'border-green-200 bg-green-50 text-green-700'
    if (stats?.system_health === 'WARNING') return 'border-yellow-200 bg-yellow-50 text-yellow-700'
    if (stats?.system_health === 'CRITICAL') return 'border-red-200 bg-red-50 text-red-700'
    return 'border-slate-200 bg-slate-100 text-slate-700'
  }, [stats])

  const services = useMemo(
    () => [...new Set(errors.map((item) => item.service_name))].sort(),
    [errors],
  )

  const filteredErrors = useMemo(() => {
    const query = search.trim().toLowerCase()
    return errors.filter((item) => {
      const matchesSearch =
        !query ||
        [item.service_name, item.error_type, item.message ?? '']
          .some((value) => value.toLowerCase().includes(query))
      const matchesService = serviceFilter === 'ALL' || item.service_name === serviceFilter
      const matchesSeverity = severityFilter === 'ALL' || item.severity === severityFilter
      return matchesSearch && matchesService && matchesSeverity
    })
  }, [errors, search, serviceFilter, severityFilter])

  const pageCount = Math.max(1, Math.ceil(filteredErrors.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const visibleErrors = filteredErrors.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  const filteredIncidents = incidents.filter(
    (incident) => incidentFilter === 'ALL' || incident.status === incidentFilter,
  )
  const maxTimelineCount = Math.max(1, ...timeline.map((point) => point.count))
  const maxServiceCount = Math.max(1, ...serviceStats.map((item) => item.count))
  const hasSeverityData = severityStats.some((item) => item.count > 0)

  if (loading) {
    return <div className="p-6 text-slate-600">Loading dashboard...</div>
  }

  if (error && !lastUpdated) {
    return (
      <div className="m-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
        {error}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-100 p-4 text-slate-900 sm:p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Operations</p>
            <h1 className="text-2xl font-bold sm:text-3xl">Error Intelligence Dashboard</h1>
          </div>
          <p className="text-xs text-slate-500">
            Auto-refreshes every 5 seconds
            {lastUpdated && ` · Updated ${lastUpdated.toLocaleTimeString()}`}
          </p>
        </header>

        {error && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800" role="status">
            Latest refresh failed. Showing the last successfully loaded data.
          </div>
        )}

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="System overview">
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
            <p className="text-sm text-blue-700">Total Errors</p>
            <p className="mt-2 text-3xl font-bold">{stats?.total_errors ?? 0}</p>
          </div>
          <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4">
            <p className="text-sm text-yellow-700">Errors / Min</p>
            <p className="mt-2 text-3xl font-bold">{stats?.errors_per_minute ?? 0}</p>
          </div>
          <div className="rounded-xl border border-red-200 bg-red-50 p-4">
            <p className="text-sm text-red-700">Active Incidents</p>
            <p className="mt-2 text-3xl font-bold">{stats?.active_incidents ?? 0}</p>
          </div>
          <div className={`rounded-xl border p-4 ${healthClass}`}>
            <p className="text-sm">System Health</p>
            <p className="mt-2 text-3xl font-bold">{stats?.system_health ?? 'UNKNOWN'}</p>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-2" aria-label="Error charts">
          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <h2 className="mb-1 text-lg font-bold">Error Timeline</h2>
            <p className="mb-4 text-xs text-slate-500">Errors per minute · last 15 minutes</p>
            {timeline.length === 0 ? (
              <p className="py-12 text-center text-sm text-slate-500">No timeline data available.</p>
            ) : (
              <div className="flex h-44 items-end gap-1" role="img" aria-label="Errors per minute bar chart">
                {timeline.map((point) => (
                  <div key={point.minute} className="flex h-full min-w-0 flex-1 flex-col justify-end">
                    <span className="mb-1 text-center text-[10px] text-slate-500">{point.count || ''}</span>
                    <div
                      className="min-h-1 rounded-t bg-blue-500"
                      style={{ height: `${Math.max(4, (point.count / maxTimelineCount) * 100)}%` }}
                      title={`${point.minute}: ${point.count} errors`}
                    />
                    <span className="mt-2 truncate text-center text-[9px] text-slate-500">{point.minute}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <h2 className="mb-1 text-lg font-bold">Failing Services</h2>
            <p className="mb-4 text-xs text-slate-500">Errors per service · last 15 minutes</p>
            {serviceStats.length === 0 ? (
              <p className="py-12 text-center text-sm text-slate-500">No service errors in this period.</p>
            ) : (
              <div className="space-y-3">
                {serviceStats.slice(0, 6).map((item) => (
                  <div key={item.service_name}>
                    <div className="mb-1 flex justify-between gap-3 text-sm">
                      <span className="truncate text-slate-700">{item.service_name}</span>
                      <span className="font-semibold text-slate-900">{item.count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100">
                      <div
                        className="h-2 rounded-full bg-red-500"
                        style={{ width: `${(item.count / maxServiceCount) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200 lg:col-span-2">
            <h2 className="mb-1 text-lg font-bold">Severity Breakdown</h2>
            <p className="mb-4 text-xs text-slate-500">Errors by severity · last 15 minutes</p>
            {!hasSeverityData ? (
              <p className="py-8 text-center text-sm text-slate-500">No severity data available.</p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {SEVERITIES.map((severity) => {
                  const count = severityStats.find((item) => item.severity === severity)?.count ?? 0
                  const total = severityStats.reduce((sum, item) => sum + item.count, 0)
                  return (
                    <div key={severity} className="rounded-xl border border-slate-200 p-3">
                      <div className="mb-2 flex items-center justify-between">
                        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${severityClasses[severity]}`}>
                          {severity}
                        </span>
                        <span className="font-bold">{count}</span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100">
                        <div
                          className={`h-2 rounded-full ${severityBarColors[severity]}`}
                          style={{ width: `${total ? (count / total) * 100 : 0}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
          <div className="min-w-0 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold">Recent Errors</h2>
                <p className="mt-1 text-xs text-slate-500">
                  Showing up to {Math.min(totalErrorCount, 100)} latest of {totalErrorCount} records
                </p>
              </div>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                {filteredErrors.length} matching
              </span>
            </div>

            <div className="mb-4 grid gap-3 sm:grid-cols-3">
              <label className="sm:col-span-1">
                <span className="sr-only">Search errors</span>
                <input
                  type="search"
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value)
                    setPage(1)
                  }}
                  placeholder="Search service, type, message"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </label>
              <label>
                <span className="sr-only">Filter by service</span>
                <select
                  value={serviceFilter}
                  onChange={(event) => {
                    setServiceFilter(event.target.value)
                    setPage(1)
                  }}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                >
                  <option value="ALL">All services</option>
                  {services.map((service) => <option key={service} value={service}>{service}</option>)}
                </select>
              </label>
              <label>
                <span className="sr-only">Filter by severity</span>
                <select
                  value={severityFilter}
                  onChange={(event) => {
                    setSeverityFilter(event.target.value)
                    setPage(1)
                  }}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                >
                  <option value="ALL">All severities</option>
                  {SEVERITIES.map((severity) => <option key={severity} value={severity}>{severity}</option>)}
                </select>
              </label>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="w-full min-w-[760px] border-collapse text-left text-sm">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="p-3">Service</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Message</th>
                    <th className="p-3">Severity</th>
                    <th className="p-3">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleErrors.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-4 text-center text-slate-500">No matching errors found.</td>
                    </tr>
                  ) : (
                    visibleErrors.map((item) => (
                      <tr key={item.id} className="border-t border-slate-200">
                        <td className="p-3 font-medium text-slate-800">{item.service_name}</td>
                        <td className="p-3 text-slate-700">{item.error_type}</td>
                        <td className="max-w-64 truncate p-3 text-slate-600" title={item.message ?? ''}>
                          {item.message || '—'}
                        </td>
                        <td className="p-3">
                          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${severityClasses[item.severity] ?? 'bg-slate-100 text-slate-700'}`}>
                            {item.severity}
                          </span>
                        </td>
                        <td className="whitespace-nowrap p-3 text-slate-600">{new Date(item.occurred_at).toLocaleString()}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="mt-3 flex items-center justify-between text-sm">
              <p className="text-slate-500">
                Page {currentPage} of {pageCount} · {filteredErrors.length} matching events
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setPage(currentPage - 1)}
                  disabled={currentPage <= 1}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-slate-700 enabled:hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  type="button"
                  onClick={() => setPage(currentPage + 1)}
                  disabled={currentPage >= pageCount}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-slate-700 enabled:hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold">Incidents</h2>
                <p className="mt-1 text-xs text-slate-500">{filteredIncidents.length} shown of {incidents.length}</p>
              </div>
              <label>
                <span className="sr-only">Filter incidents by status</span>
                <select
                  value={incidentFilter}
                  onChange={(event) => setIncidentFilter(event.target.value as typeof incidentFilter)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                >
                  <option value="ALL">All statuses</option>
                  <option value="OPEN">Open</option>
                  <option value="RESOLVED">Resolved</option>
                </select>
              </label>
            </div>
            <div className="max-h-[34rem] space-y-3 overflow-y-auto">
              {filteredIncidents.length === 0 ? (
                <p className="py-8 text-center text-sm text-slate-500">No incidents match this status.</p>
              ) : (
                filteredIncidents.map((incident) => (
                  <div key={incident.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate font-semibold">{incident.service_name}</p>
                      <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold uppercase ${severityClasses[incident.severity] ?? 'bg-slate-100 text-slate-700'}`}>
                        {incident.severity}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-slate-700">{incident.error_type}</p>
                    {incident.sample_message && (
                      <p className="mt-1 truncate text-xs text-slate-500" title={incident.sample_message}>
                        {incident.sample_message}
                      </p>
                    )}
                    <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                      <span>{incident.status}</span>
                      <span>{incident.occurrence_count} occurrences</span>
                    </div>
                    <p className="mt-1 text-[11px] text-slate-400">
                      Last seen {new Date(incident.last_seen).toLocaleString()}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

export default App
