"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api/client";
import { refreshServerCart } from "@/lib/cart/useServerCart";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { cn } from "@/lib/utils";
import { parseCheckoutError, type FieldErrors } from "@/lib/checkout/errors";
import type {
  CheckoutPayload,
  DeliveryData,
  FulfillmentType,
  Order,
} from "@/lib/checkout/types";

const PROVINCES = [
  "Eastern Cape",
  "Free State",
  "Gauteng",
  "KwaZulu-Natal",
  "Limpopo",
  "Mpumalanga",
  "Northern Cape",
  "North West",
  "Western Cape",
];

const EMPTY_DELIVERY: DeliveryData = {
  recipient_name: "",
  phone_number: "",
  address_line_1: "",
  address_line_2: "",
  city: "",
  province: "",
  postal_code: "",
};

export function CheckoutForm() {
  const router = useRouter();
  const [fulfillment, setFulfillment] = useState<FulfillmentType>("PICKUP");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [delivery, setDelivery] = useState<DeliveryData>(EMPTY_DELIVERY);
  const [notes, setNotes] = useState("");
  const [promo, setPromo] = useState("");
  const [fields, setFields] = useState<FieldErrors>({});
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const today = new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD

  function setD<K extends keyof DeliveryData>(key: K, value: string) {
    setDelivery((d) => ({ ...d, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setFields({});
    setMessage("");

    const payload: CheckoutPayload = { fulfillment_type: fulfillment };
    if (fulfillment === "PICKUP") {
      payload.scheduled_date = date;
      payload.scheduled_time = time;
    } else {
      payload.delivery_data = {
        ...delivery,
        address_line_2: delivery.address_line_2?.trim() || undefined,
      };
    }
    if (notes.trim()) payload.customer_notes = notes.trim();
    if (promo.trim()) payload.promotion_code = promo.trim();

    try {
      const order = await apiFetch<Order>("/orders/checkout", {
        method: "POST",
        json: payload,
      });
      try {
        void Promise.resolve(refreshServerCart()).catch(() => {});
      } catch {
        /* header count will refresh on next load */
      }
      router.push(
        `/orders/${encodeURIComponent(order.order_number)}?placed=1`,
      );
    } catch (err) {
      const parsed = parseCheckoutError(err);
      if (parsed.status === 401) {
        router.replace("/login?next=/checkout");
        return;
      }
      setFields(parsed.fields);
      setMessage(parsed.message || parsed.fields.delivery_data || "");
      setSubmitting(false);
    }
  }

  const choice = (value: FulfillmentType, label: string) => (
    <button
      type="button"
      onClick={() => setFulfillment(value)}
      aria-pressed={fulfillment === value}
      className={cn(
        "flex-1 rounded-md border px-4 py-3 text-sm font-medium transition-colors",
        fulfillment === value
          ? "border-accent bg-accent text-white"
          : "border-foreground/25 hover:border-foreground/50",
      )}
    >
      {label}
    </button>
  );

  return (
    <form onSubmit={onSubmit} className="space-y-6" noValidate>
      <section>
        <h2 className="mb-3 text-lg font-semibold">How would you like it?</h2>
        <div className="flex gap-3">
          {choice("PICKUP", "Collect")}
          {choice("DELIVERY", "Delivery")}
        </div>
      </section>

      {fulfillment === "PICKUP" ? (
        <section className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Collection date"
            type="date"
            min={today}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            error={fields.scheduled_date}
            required
          />
          <Input
            label="Collection time"
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            error={fields.scheduled_time}
            required
          />
        </section>
      ) : (
        <section className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Recipient name"
            autoComplete="name"
            value={delivery.recipient_name}
            onChange={(e) => setD("recipient_name", e.target.value)}
            error={fields.recipient_name}
            required
          />
          <Input
            label="Phone number"
            type="tel"
            autoComplete="tel"
            value={delivery.phone_number}
            onChange={(e) => setD("phone_number", e.target.value)}
            error={fields.phone_number}
            required
          />
          <div className="sm:col-span-2">
            <Input
              label="Address line 1"
              autoComplete="address-line1"
              value={delivery.address_line_1}
              onChange={(e) => setD("address_line_1", e.target.value)}
              error={fields.address_line_1}
              required
            />
          </div>
          <div className="sm:col-span-2">
            <Input
              label="Address line 2 (optional)"
              autoComplete="address-line2"
              value={delivery.address_line_2 ?? ""}
              onChange={(e) => setD("address_line_2", e.target.value)}
              error={fields.address_line_2}
            />
          </div>
          <Input
            label="City"
            autoComplete="address-level2"
            value={delivery.city}
            onChange={(e) => setD("city", e.target.value)}
            error={fields.city}
            required
          />
          <Input
            label="Postal code"
            autoComplete="postal-code"
            value={delivery.postal_code}
            onChange={(e) => setD("postal_code", e.target.value)}
            error={fields.postal_code}
            required
          />
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm font-medium" htmlFor="province">
              Province
            </label>
            <select
              id="province"
              value={delivery.province}
              onChange={(e) => setD("province", e.target.value)}
              required
              className="w-full rounded-md border border-foreground/25 bg-transparent px-3 py-2"
            >
              <option value="">Select province</option>
              {PROVINCES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            {fields.province && (
              <p className="mt-1 text-sm text-danger">{fields.province}</p>
            )}
          </div>
        </section>
      )}

      <section className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium" htmlFor="notes">
            Notes (optional)
          </label>
          <textarea
            id="notes"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded-md border border-foreground/25 bg-transparent px-3 py-2"
          />
          {fields.customer_notes && (
            <p className="mt-1 text-sm text-danger">{fields.customer_notes}</p>
          )}
        </div>
        <Input
          label="Promotion code (optional)"
          value={promo}
          onChange={(e) => setPromo(e.target.value)}
          error={fields.promotion_code}
        />
      </section>

      {message && (
        <p role="alert" className="rounded-md border border-danger/40 p-3 text-sm text-danger">
          {message}
        </p>
      )}

      <Button type="submit" size="lg" loading={submitting} className="w-full">
        Place order
      </Button>
    </form>
  );
}
