import { AssetDetailExperience } from "@/components/AssetDetailExperience";

export default async function AssetDetailPage({ params }: { params: Promise<{ assetId: string }> }) {
  const { assetId } = await params;

  return <AssetDetailExperience assetId={assetId} />;
}