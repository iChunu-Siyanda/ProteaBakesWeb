export type FulfillmentType = "PICKUP" | "DELIVERY";

export interface DeliveryData {
  recipient_name: string;
  phone_number: string;
  address_line_1: string;
  address_line_2?: string;
  city: string;
  province: string;
  postal_code: string;
}

export interface CheckoutPayload {
  fulfillment_type: FulfillmentType;
  customer_notes?: string;
  scheduled_date?: string; // YYYY-MM-DD (pickup only)
  scheduled_time?: string; // HH:MM (pickup only)
  delivery_data?: DeliveryData; // delivery only
  promotion_code?: string;
}

export interface CartLine {
  id: number;
  product: number;
  product_name: string;
  unit_price: string;
  quantity: number;
  subtotal: string;
}

export interface CheckoutCart {
  id: number;
  items: CartLine[];
  total: string;
}

export interface OrderLine {
  id: number;
  product: number;
  product_name: string;
  unit_price: string;
  quantity: number;
  subtotal: string;
}

export interface OrderFulfillment {
  type: FulfillmentType;
  status: string;
  scheduled_date?: string;
  scheduled_time?: string;
  recipient_name?: string;
  address_line_1?: string;
  address_line_2?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  tracking_reference?: string | null;
}

export interface OrderPayment {
  status: string;
  amount: string;
  currency: string;
  paid_at: string | null;
}

export interface Order {
  id: number;
  order_number: string;
  status: string;
  fulfillment_type: FulfillmentType;
  subtotal: string;
  discount_amount: string;
  delivery_fee: string;
  total: string;
  customer_notes: string;
  items: OrderLine[];
  created_at: string;
  fulfillment?: OrderFulfillment | null;
  payment?: OrderPayment | null;
}
