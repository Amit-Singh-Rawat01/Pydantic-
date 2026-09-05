import StatsCards from "./components/StatsCards";
import ErrorTimelineChart from "./components/ErrorTimelineChart";
import ErrorsList from "./components/ErrorsList";
import IncidentsList from "./components/IncidentsList";

function App() {
  return (
    <div>
      <StatsCards />
      <ErrorTimelineChart />
      <ErrorsList />
      <IncidentsList />
    </div>
  );
}

export default App;