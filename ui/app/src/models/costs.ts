export interface CostResource {
  id: string;
  name: string;
  costs: Array<CostItem>;
}

export interface CostItem {
  cost: number;
  currency: string;
  date?: string;
}
