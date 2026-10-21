import { OrderView } from "@/components/orders/OrderView";

export default async function OrderPage({
  params,
  searchParams,
}: {
  params: Promise<{ orderNumber: string }>;
  searchParams: Promise<{ placed?: string }>;
}) {
  const { orderNumber } = await params;
  const { placed } = await searchParams;

  return (
    <main className="container-page py-10">
      <OrderView orderNumber={orderNumber} placed={placed === "1"} />
    </main>
  );
}
