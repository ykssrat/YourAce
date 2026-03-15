export type HorizonSignals = {
  short: "BUY" | "HOLD" | "SELL";
  mid: "BUY" | "HOLD" | "SELL";
  long: "BUY" | "HOLD" | "SELL";
};

export type Opinion = "BUY" | "HOLD" | "SELL";

export type OpinionMatrix = {
  short: Opinion;
  mid: Opinion;
  long: Opinion;
};

export type AnalyzeResponse = {
  code: string;
  as_of_date: string;
  score: number;
  label: Opinion;
  horizon_signals: HorizonSignals;
  selected_features: string[];
  news_enabled?: boolean;
  latest_news: NewsItem[];
};

export type DiagnoseResponse = AnalyzeResponse & {
  matrix: OpinionMatrix;
};

export type ScreenItem = {
  code: string;
  name: string;
  score: number;
  label: Opinion;
  horizon_signals: HorizonSignals;
};

export type ScreenResponse = {
  items: ScreenItem[];
  scanned_count: number;
  offset: number;
  has_more: boolean;
  total_available: number;
  score_pass_count: number;
  signal_miss_count: number;
};

export type SearchItem = {
  code: string;
  name: string;
};

export type NewsItem = {
  title: string;
  source: string;
  time: string;
  url: string;
};
