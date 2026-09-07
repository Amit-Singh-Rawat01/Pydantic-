import StatsCards from "./components/StatsCards";
import ErrorTimelineChart from "./components/ErrorTimelineChart";
import FailingServicesChart from "./components/FailingServicesChart";
import SeverityChart from "./components/SeverityChart";
import ErrorsList from "./components/ErrorsList";
import IncidentsList from "./components/IncidentsList";

function App() {
  return (
    <div>
      <StatsCards />
      <div className="grid gap-6 p-6 pb-0 lg:grid-cols-2">
        <ErrorTimelineChart />
        <FailingServicesChart />
        <SeverityChart />
      </div>
      <ErrorsList />
      <IncidentsList />
    </div>
  );
}

export default App;