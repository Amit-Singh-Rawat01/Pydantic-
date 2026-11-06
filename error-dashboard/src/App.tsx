import StatsCards from "./components/StatsCards";
import ErrorTimelineChart from "./components/ErrorTimelineChart";
import FailingServicesChart from "./components/FailingServicesChart";
import SeverityChart from "./components/SeverityChart";
import ErrorsList from "./components/ErrorsList";
import IncidentsList from "./components/IncidentsList";
import AnomalyEvents from "./components/AnomalyEvents";
import ServiceHealth from "./components/ServiceHealth";
import ErrorGroups from "./components/ErrorGroups";
import RootCauseCard from "./components/RootCauseCard";

function App() {
  return (
    <div>
      <StatsCards />
      <ServiceHealth />
      <RootCauseCard />
      <div className="grid gap-6 p-6 pb-0 lg:grid-cols-2">
        <ErrorTimelineChart />
        <FailingServicesChart />
        <SeverityChart />
      </div>
      <ErrorGroups />
      <ErrorsList />
      <IncidentsList />
      <AnomalyEvents />
    </div>
  );
}

export default App;