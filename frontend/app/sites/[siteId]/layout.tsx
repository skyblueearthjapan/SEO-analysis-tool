import { SideRail } from "@/components/layout/SideRail";

export default function SiteLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { siteId: string };
}) {
  return (
    <div className="flex">
      <SideRail siteId={params.siteId} />
      <div className="flex-1 ml-[72px] p-6">{children}</div>
    </div>
  );
}
