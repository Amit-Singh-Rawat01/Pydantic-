export function statusColor(status: string) {
  if (status === "ANOMALY") return "bg-red-100 text-red-700";
  if (status === "WARNING") return "bg-yellow-100 text-yellow-700";
  return "bg-green-100 text-green-700";
}

export function borderColor(status: string) {
  if (status === "ANOMALY") return "border-red-400";
  if (status === "WARNING") return "border-yellow-400";
  return "border-green-400";
}
