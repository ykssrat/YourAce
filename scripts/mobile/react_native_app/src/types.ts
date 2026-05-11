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

export type ScreenActionLogRequest = {
  asset_type?: string;
  horizon?: string;
  opinion?: string;
  strategy?: string;
  round_size?: number;
  offset?: number;
  result_count?: number;
  total_available?: number;
  scanned_count?: number;
  signal_miss_count?: number;
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

export type WatchlistRecommendation = {
  code: string;
  name: string;
  score: number;
  matched_keywords: string[];
};

export type AuthResponse = {
  user_id: string;
  username: string;
  token: string;
  created_at: string;
  updated_at: string;
  /** 服务端会话过期时间（ISO），旧后端可能为空 */
  token_expires_at?: string;
  persist_session?: boolean;
};

export type WatchlistItem = {
  code: string;
  name: string;
  etf_code: string;
  etf_name: string;
  sector_name: string;
  created_at: string;
  updated_at: string;
};

export type QuoteSnapshot = {
  code: string;
  name: string;
  latest_price: number;
  pct_change: number;
  volume: number;
  amount: number;
  turnover: number;
  updated_at: string;
  source: string;
};

export type SignalCandidate = {
  signal_id: string;
  action: Opinion;
  title: string;
  reason: string;
};

export type SignalDecision = {
  primary_signal: string;
  primary_action: Opinion;
  final_action: Opinion;
  final_action_label: string;
  notify: boolean;
  buy_signal_count: number;
  sell_signal_count: number;
  reason_tags: string[];
  reason_text: string;
  signals: SignalCandidate[];
};

export type WatchlistSignalSummary = {
  timestamp: string;
  clock: string;
  signals: SignalCandidate[];
  decision: SignalDecision;
  notification: string;
};

export type WatchlistNotification = {
  code: string;
  name: string;
  sector_name: string;
  etf_code: string;
  etf_name: string;
  action: Opinion;
  action_label: string;
  timestamp: string;
  clock: string;
  reason_tags: string[];
  reason_text: string;
  message: string;
  fingerprint: string;
};

export type WatchlistItemSnapshot = {
  code: string;
  name: string;
  sector_name: string;
  etf_code: string;
  etf_name: string;
  quote: QuoteSnapshot;
  etf_quote?: QuoteSnapshot | null;
  intraday_high: number;
  intraday_high_time: string;
  intraday_low: number;
  intraday_low_time: string;
  minute_volume: Array<{ time: string; volume: number }>;
  signals: WatchlistSignalSummary;
  notification?: WatchlistNotification | null;
};

export type WatchlistSummaryResponse = {
  user_id: string;
  count: number;
  items: WatchlistItemSnapshot[];
  notifications: WatchlistNotification[];
};

export type WatchlistListResponse = {
  user_id: string;
  count: number;
  items: WatchlistItem[];
};

export type WatchlistQuotesResponse = {
  user_id: string;
  count: number;
  items: QuoteSnapshot[];
};

export type WatchlistSignalsResponse = {
  user_id: string;
  count: number;
  items: WatchlistSignalSummary[];
};

export type WatchlistQueueResponse = {
  user_id: string;
  count: number;
  items: WatchlistNotification[];
};

export type WatchlistAddRequest = {
  user_id: string;
  token: string;
  code: string;
  stock_name?: string;
  etf_code?: string;
  etf_name?: string;
  sector_name?: string;
};

export type WatchlistRemoveRequest = {
  user_id: string;
  token: string;
  code: string;
};

export type AuthRequest = {
  username: string;
  password: string;
  /** 与「保持登录」勾选一致，影响服务端 token 有效期 */
  persist_session?: boolean;
};

export const STRATEGY_OPTIONS = [
  { value: "consensus", label: "共识矩阵(五大策略混合)" },
  { value: "momentum_deviation", label: "动量偏离策略" },
  { value: "rsi", label: "RSI策略" },
  { value: "kdj", label: "KDJ策略" },
  { value: "macd", label: "MACD策略" },
  { value: "boll", label: "BOLL策略" },
  { value: "livermore", label: "利弗莫尔策略" },
];
