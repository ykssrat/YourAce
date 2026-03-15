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
  label: Opinion;
  horizon_signals: HorizonSignals;
  selected_features: string[];
  news_enabled?: boolean;
  latest_news: NewsItem[];
};

export type AnalyzeRequest = {
  code: string;
  strategy?: string;
  long_fund_trend?: number;
  include_news?: boolean;
};

export type DiagnoseResponse = AnalyzeResponse & {
  matrix: OpinionMatrix;
};

export type ScreenItem = {
  code: string;
  name: string;
  label: Opinion;
  horizon_signals: HorizonSignals;
};

export type ScreenResponse = {
  items: ScreenItem[];
  scanned_count: number;
  offset: number;
  has_more: boolean;
  total_available: number;
  signal_miss_count: number;
};

export type ScreenRequest = {
  asset_type?: string;
  horizon?: string;
  opinion?: string;
  strategy?: string;
  round_size?: number;
  offset?: number;
};

export type DiagnoseRequest = {
  code: string;
  strategy?: string;
  include_news?: boolean;
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

export const STRATEGY_OPTIONS = [
  { value: "default", label: "默认" },
  { value: "martingale", label: "马丁策略" },
  { value: "livermore", label: "利弗莫尔策略" },
  { value: "kdj", label: "KDJ策略" },
  { value: "golden_cross", label: "金叉死叉策略" },
  { value: "ml_multi_factor", label: "机器学习多因子策略" },
  { value: "retail_psychology", label: "散户心理学策略" },
];
