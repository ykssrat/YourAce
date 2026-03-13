export type HorizonSignals = {
  short: "BUY" | "HOLD" | "SELL";
  mid: "BUY" | "HOLD" | "SELL";
  long: "BUY" | "HOLD" | "SELL";
};

export type AnalyzeResponse = {
  code: string;
  as_of_date: string;
  score: number;
  label: "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL";
  horizon_signals: HorizonSignals;
  selected_features: string[];
};

export type SearchItem = {
  code: string;
  name: string;
};
