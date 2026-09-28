import { InvestigationReport } from "../../../../components/investigation-report";

export default async function InvestigationReportPage({
  params,
}: {
  params: Promise<{ "hunt-id": string }>;
}) {
  const { "hunt-id": huntId } = await params;
  return <InvestigationReport huntId={huntId} />;
}
