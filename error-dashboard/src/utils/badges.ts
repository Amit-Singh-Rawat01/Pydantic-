export function getSeverityClass(severity: string) {
  switch (severity.toLowerCase()) {
    case 'critical': return 'bg-red-100 text-red-700 px-2 py-1 rounded';
    case 'high': return 'bg-orange-100 text-orange-700 px-2 py-1 rounded';
    case 'medium': return 'bg-yellow-100 text-yellow-700 px-2 py-1 rounded';
    default: return 'bg-blue-100 text-blue-700 px-2 py-1 rounded';
  }
}

export function getStatusClass(status: string) {
  return status === 'open'
    ? 'bg-green-100 text-green-700 px-2 py-1 rounded'
    : 'bg-red-100 text-red-700 px-2 py-1 rounded';
}