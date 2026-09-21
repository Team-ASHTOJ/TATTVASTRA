import { PlatformOverview } from "../components/platform-overview";
import { DemoScreen } from "../components/demo-presentation";
export default function Home() {
  return (
    <DemoScreen section="home">
      <PlatformOverview />
    </DemoScreen>
  );
}
