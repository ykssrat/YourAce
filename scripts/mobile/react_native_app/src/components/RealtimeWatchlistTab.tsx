/// <reference path="../react_native_shims.d.ts" />
import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";

import {
  addWatchlistItem,
  buildWatchlistStreamUrl,
  getWatchlistSummary,
  recommendWatchlistEtfs,
  removeWatchlistItem,
  searchAssets,
} from "../services/api";
import {
  AuthResponse,
  SearchItem,
  WatchlistItemSnapshot,
  WatchlistNotification,
  WatchlistRecommendation,
  WatchlistSummaryResponse,
} from "../types";

type RealtimeWatchlistTabProps = {
  apiBaseUrl: string;
  auth: AuthResponse;
  onGoToDiagnose: (code: string) => void;
  onAuthExpired: () => void;
};

type MinuteVolumePoint = WatchlistItemSnapshot["minute_volume"][number];
type MinuteChartPoint = MinuteVolumePoint & {
  height: number;
  isLatest: boolean;
};

export function RealtimeWatchlistTab({ apiBaseUrl, auth, onGoToDiagnose, onAuthExpired }: RealtimeWatchlistTabProps) {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<SearchItem | null>(null);
  const [recommendations, setRecommendations] = useState<WatchlistRecommendation[]>([]);
  const [selectedRecommendation, setSelectedRecommendation] = useState<WatchlistRecommendation | null>(null);
  const [summary, setSummary] = useState<WatchlistSummaryResponse | null>(null);
  const [notifications, setNotifications] = useState<WatchlistNotification[]>([]);
  const [error, setError] = useState("");
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [liveEnabled, setLiveEnabled] = useState(true);
  const [lastSyncLabel, setLastSyncLabel] = useState("未同步");
  const [confirmVisible, setConfirmVisible] = useState(false);
  const refreshingRef = useRef(false);
  const streamRef = useRef<EventSource | null>(null);
  const aliveRef = useRef(true);

  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
    };
  }, []);

  useEffect(() => {
    const keyword = query.trim();
    if (!keyword) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setSearching(true);
        const items = await searchAssets(keyword, 8, apiBaseUrl);
        if (aliveRef.current) {
          setSearchResults(items);
        }
      } catch {
        if (aliveRef.current) {
          setSearchResults([]);
        }
      } finally {
        if (aliveRef.current) {
          setSearching(false);
        }
      }
    }, 280);

    return () => clearTimeout(timer);
  }, [query, apiBaseUrl]);

  useEffect(() => {
    void refreshWatchlist(true);

    if (!liveEnabled) {
      return;
    }

    const timer = setInterval(() => {

  useEffect(() => {
    if (!liveEnabled || typeof EventSource === "undefined") {
      return;
    }

    const source = new EventSource(buildWatchlistStreamUrl(auth.user_id, auth.token, apiBaseUrl));
    streamRef.current = source;

    source.onmessage = (event) => {
      if (!aliveRef.current || !event.data) {
        return;
      }

      try {
        const payload = JSON.parse(event.data) as WatchlistNotification;
        if (payload && typeof payload.fingerprint === "string") {
          setNotifications((previous) => mergeNotifications([payload], previous));
          setLastSyncLabel(formatClock(new Date()));
        }
      } catch {
        // SSE 里只接收通知对象，解析失败则忽略。
      }
    };

    source.onerror = () => {
      source.close();
    };

    return () => {
      source.close();
      if (streamRef.current === source) {
        streamRef.current = null;
      }
    };
  }, [apiBaseUrl, auth.token, auth.user_id, liveEnabled]);
      void refreshWatchlist(false);
    }, 20000);

    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBaseUrl, auth.user_id, auth.token, liveEnabled]);

  async function refreshWatchlist(showSpinner: boolean) {
    if (refreshingRef.current) {
      return;
    }

    refreshingRef.current = true;
    if (showSpinner) {
      setRefreshing(true);
    }

    try {
      const payload = await getWatchlistSummary(auth.user_id, auth.token, apiBaseUrl);
      if (!aliveRef.current) {
        return;
      }

      setSummary(payload);
      setError("");
      setLastSyncLabel(formatClock(new Date()));
      const incomingNotifications = collectNotifications(payload);
      if (incomingNotifications.length > 0) {
        setNotifications((previous) => mergeNotifications(incomingNotifications, previous));
        for (const noti of incomingNotifications.slice(0, 1)) {
          if (noti && noti.message) {
            Alert.alert("行情信号", noti.message);
          }
        }
      }
    } catch (err) {
      if (!aliveRef.current) {
        return;
      }

      const message = err instanceof Error ? err.message : "请求失败";
      setError(message);
      if (isAuthIssue(message)) {
        onAuthExpired();
      }
    } finally {
      refreshingRef.current = false;
      if (showSpinner && aliveRef.current) {
        setRefreshing(false);
      }
    }
  }

  function handleQueryChange(value: string) {
    setQuery(value);
    setSelectedAsset(null);
    setRecommendations([]);
    setSelectedRecommendation(null);
    setError("");
  }

  async function handlePickAsset(item: SearchItem) {
    setSelectedAsset(item);
    setQuery(item.code);
    setError("");
    setConfirmVisible(false);

    try {
      setLoadingRecommendations(true);
      const items = await recommendWatchlistEtfs(item.code, apiBaseUrl, item.name, 5);
      if (!aliveRef.current) {
        return;
      }

      setRecommendations(items);
      setSelectedRecommendation(items[0] ?? null);
    } catch (err) {
      if (aliveRef.current) {
        setRecommendations([]);
        setSelectedRecommendation(null);
        setError(err instanceof Error ? err.message : "ETF 推荐加载失败");
      }
    } finally {
      if (aliveRef.current) {
        setLoadingRecommendations(false);
      }
    }
  }

  function handleConfirmAdd() {
    setConfirmVisible(true);
  }

  function handleCancelAdd() {
    setQuery("");
    setSearchResults([]);
    setSelectedAsset(null);
    setRecommendations([]);
    setSelectedRecommendation(null);
    setConfirmVisible(false);
    setError("");
  }

  async function handleSubmitWatchlist() {
    const draft = resolveDraftAsset(query, selectedAsset, searchResults);
    if (!draft) {
      setError("请先输入并选择一只股票");
      return;
    }

    const etf = selectedRecommendation ?? recommendations[0] ?? null;
    setSubmitting(true);
    setError("");

    try {
      await addWatchlistItem(
        {
          user_id: auth.user_id,
          token: auth.token,
          code: draft.code,
          stock_name: draft.name,
          etf_code: etf?.code ?? "",
          etf_name: etf?.name ?? "",
          sector_name: etf?.name ?? draft.name,
        },
        apiBaseUrl,
      );

      if (aliveRef.current) {
        setQuery("");
        setSearchResults([]);
        setSelectedAsset(null);
        setRecommendations([]);
        setSelectedRecommendation(null);
      }
      await refreshWatchlist(true);
    } catch (err) {
      if (aliveRef.current) {
        const message = err instanceof Error ? err.message : "加入失败";
        setError(message);
        if (isAuthIssue(message)) {
          onAuthExpired();
        }
      }
    } finally {
      if (aliveRef.current) {
        setSubmitting(false);
      }
    }
  }

  async function handleRemove(code: string) {
    setSubmitting(true);
    setError("");

    try {
      await removeWatchlistItem({ user_id: auth.user_id, token: auth.token, code }, apiBaseUrl);
      await refreshWatchlist(true);
    } catch (err) {
      if (aliveRef.current) {
        const message = err instanceof Error ? err.message : "移除失败";
        setError(message);
        if (isAuthIssue(message)) {
          onAuthExpired();
        }
      }
    } finally {
      if (aliveRef.current) {
        setSubmitting(false);
      }
    }
  }

  function handleToggleLive() {
    setLiveEnabled(!liveEnabled);
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.headerCard}>
        <View>
          <Text style={styles.pageTitle}>实时看盘</Text>
          <Text style={styles.pageSubtitle}>分钟级刷新，自选池、分时量、通知提醒统一展示。</Text>
        </View>
        <View style={styles.headerMeta}>
          <Text style={styles.headerMetaText}>当前用户：{auth.username}</Text>
          <Text style={styles.headerMetaText}>最后同步：{lastSyncLabel}</Text>
        </View>
      </View>

      <View style={styles.actionRow}>
        <Pressable style={styles.actionBtn} onPress={() => void refreshWatchlist(true)} disabled={refreshing || submitting}>
          {refreshing ? <ActivityIndicator color="#ffffff" size="small" /> : <Text style={styles.actionBtnText}>立即刷新</Text>}
        </Pressable>
        <Pressable style={[styles.actionBtn, liveEnabled ? styles.actionBtnOn : styles.actionBtnOff]} onPress={handleToggleLive}>
          <Text style={styles.actionBtnText}>{liveEnabled ? "自动刷新中" : "已暂停刷新"}</Text>
        </Pressable>
      </View>

      <View style={styles.searchCard}>
        <Text style={styles.sectionTitle}>加入自选</Text>
        <Text style={styles.sectionHint}>输入代码或名称，选中标的后绑定 ETF，最后确认加入。</Text>
        <View style={styles.searchRow}>
          <TextInput
            value={query}
            onChangeText={handleQueryChange}
            placeholder="例如 000001 或 平安银行"
            placeholderTextColor="#7a5b3f"
            autoCapitalize="none"
            autoCorrect={false}
            style={styles.searchInput}
          />
          {selectedAsset && !confirmVisible ? (
            <Pressable style={styles.searchBtn} onPress={handleConfirmAdd} disabled={submitting || loadingRecommendations}>
              <Text style={styles.searchBtnText}>加入</Text>
            </Pressable>
          ) : null}
        </View>

        {searchResults.length > 0 ? (
          <View style={styles.suggestionBox}>
            <Text style={styles.suggestionTitle}>{searching ? "搜索中..." : "搜索结果"}</Text>
            {searchResults.map((item) => (
              <Pressable key={`${item.code}-${item.name}`} style={styles.suggestionItem} onPress={() => void handlePickAsset(item)}>
                <Text style={styles.suggestionCode}>{item.code}</Text>
                <Text style={styles.suggestionName}>{item.name}</Text>
              </Pressable>
            ))}
          </View>
        ) : query.trim() ? (
          <Text style={styles.emptyHint}>{searching ? "正在搜索匹配结果..." : "没有找到匹配结果"}</Text>
        ) : null}

        {selectedAsset ? (
          <View style={styles.selectedAssetBox}>
            <Text style={styles.selectedAssetLabel}>已选中标的</Text>
            <Text style={styles.selectedAssetTitle}>{selectedAsset.code} · {selectedAsset.name}</Text>
          </View>
        ) : null}

        <View style={styles.recommendationSection}>
          <Text style={styles.sectionTitle}>ETF 推荐</Text>
          <Text style={styles.sectionHint}>选择一个绑定基准，用于板块普跌/普涨判断。</Text>
          {loadingRecommendations ? (
            <View style={styles.loadingRow}>
              <ActivityIndicator color="#013E75" size="small" />
              <Text style={styles.loadingText}>正在加载推荐...</Text>
            </View>
          ) : recommendations.length > 0 ? (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.recommendationRow}>
              <Pressable
                style={[styles.recommendationChip, !selectedRecommendation && styles.recommendationChipActive]}
                onPress={() => setSelectedRecommendation(null)}
              >
                <Text style={[styles.recommendationChipText, !selectedRecommendation && styles.recommendationChipTextActive]}>暂不绑定</Text>
              </Pressable>
              {recommendations.map((item) => (
                <Pressable
                  key={item.code}
                  style={[styles.recommendationChip, selectedRecommendation?.code === item.code && styles.recommendationChipActive]}
                  onPress={() => setSelectedRecommendation(item)}
                >
                  <Text style={[styles.recommendationChipText, selectedRecommendation?.code === item.code && styles.recommendationChipTextActive]}>
                    {item.name}
                  </Text>
                </Pressable>
              ))}
            </ScrollView>
          ) : (
            <Text style={styles.emptyHint}>先选中一只股票，系统会给出可绑定的 ETF 候选。</Text>
          )}
          {confirmVisible ? (
            <View style={styles.confirmRow}>
              <Pressable style={styles.confirmCancelBtn} onPress={handleCancelAdd}>
                <Text style={styles.confirmCancelText}>取消</Text>
              </Pressable>
              <Pressable style={styles.confirmOkBtn} onPress={() => void handleSubmitWatchlist()} disabled={submitting}>
                <Text style={styles.confirmOkText}>{submitting ? "处理中…" : "确认加入自选"}</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      </View>

      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <View style={styles.feedCard}>
        <View style={styles.feedHeader}>
          <Text style={styles.sectionTitle}>自选池概览</Text>
          <Text style={styles.sectionHint}>{summary?.count ?? 0} 只标的 · {notifications.length} 条提醒</Text>
        </View>

        {summary?.items?.length ? (
          summary.items.map((item) => (
            <WatchlistItemCard
              key={item.code}
              item={item}
              onGoToDiagnose={onGoToDiagnose}
              onRemove={handleRemove}
            />
          ))
        ) : (
          <View style={styles.emptyState}>
            <Text style={styles.emptyStateTitle}>当前还没有自选标的</Text>
            <Text style={styles.emptyStateHint}>先在上方搜索一个股票，绑定 ETF 后加入自选池。</Text>
          </View>
        )}
      </View>

      {notifications.length > 0 ? (
        <View style={styles.notifyCard}>
          <Text style={styles.sectionTitle}>最新提醒</Text>
          {notifications.slice(0, 5).map((item) => (
            <View key={item.fingerprint} style={styles.notifyItem}>
              <Text style={styles.notifyText}>{item.message}</Text>
              <Text style={styles.notifyMeta}>{item.clock} · {item.action_label}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </ScrollView>
  );
}

function WatchlistItemCard({
  item,
  onGoToDiagnose,
  onRemove,
}: {
  item: WatchlistItemSnapshot;
  onGoToDiagnose: (code: string) => void;
  onRemove: (code: string) => void;
}) {
  const decision = item?.signals?.decision;
  const finalAction = decision?.final_action ?? "HOLD";
  const actionLabel = decision?.final_action_label ?? "静默";
  const reasonText = decision?.reason_text ?? "";
  const actionColor = finalAction === "BUY" ? "#2f9e44" : finalAction === "SELL" ? "#c92a2a" : "#7c8b7a";
  const quote = item?.quote;
  const latestPrice = quote?.latest_price ?? 0;
  const pctChange = quote?.pct_change ?? 0;
  const quoteVolume = quote?.volume ?? 0;
  const intradayHigh = item?.intraday_high ?? 0;
  const intradayHighTime = item?.intraday_high_time ?? "";
  const intradayLow = item?.intraday_low ?? 0;
  const intradayLowTime = item?.intraday_low_time ?? "";
  const etfName = item?.etf_name ?? "";
  const sectorName = item?.sector_name ?? "";
  const code = item?.code ?? "";
  const name = item?.name ?? "";
  const notification = item?.notification;
  const minuteVolume = item?.minute_volume ?? [];
  const isTradingHalted = actionLabel === "休市";

  return (
    <View style={styles.itemCard}>
      <View style={styles.itemHeader}>
        <View>
          <Text style={styles.itemCode}>{code}</Text>
          <Text style={styles.itemName}>{name}</Text>
        </View>
        <View style={[styles.actionBadge, { backgroundColor: isTradingHalted ? "#f1f3f5" : `${actionColor}15` }]}>
          <Text style={[styles.actionBadgeText, { color: isTradingHalted ? "#868e96" : actionColor }]}>
            {isTradingHalted ? "休市" : actionLabel}
          </Text>
        </View>
      </View>

      <View style={styles.metricRow}>
        <Metric label="最新价" value={formatMoney(latestPrice)} />
        <Metric label="涨跌幅" value={formatPercent(pctChange)} valueStyle={pctChange >= 0 ? styles.greenText : styles.redText} />
        <Metric label="成交量" value={formatLargeNumber(quoteVolume)} />
      </View>

      <View style={styles.metricRow}>
        <Metric label="绑定板块" value={etfName || "未绑定"} />
        <Metric label="板块名称" value={sectorName || "未命名"} />
        <Metric label="信号" value={isTradingHalted ? "非交易时段" : (reasonText || "无")} />
      </View>

      <View style={styles.intradayMarkerRow}>
        <IntradayMarkerCard
          label="盘中高点"
          value={intradayHigh}
          time={intradayHighTime}
          tone="high"
        />
        <IntradayMarkerCard
          label="盘中低点"
          value={intradayLow}
          time={intradayLowTime}
          tone="low"
        />
      </View>

      <MinuteVolumeChart points={minuteVolume} />

      <View style={styles.minuteVolumeRow}>
        {minuteVolume.slice(-6).map((point: MinuteVolumePoint) => (
          <View key={`${code}-${point.time}`} style={styles.minuteVolumeChip}>
            <Text style={styles.minuteVolumeTime}>{point.time}</Text>
            <Text style={styles.minuteVolumeValue}>{formatLargeNumber(point.volume ?? 0)}</Text>
          </View>
        ))}
      </View>

      {notification ? (
        <View style={styles.itemNotifyBox}>
          <Text style={styles.itemNotifyText}>{notification.message}</Text>
        </View>
      ) : null}

      <View style={styles.itemActionRow}>
        <Pressable style={styles.itemActionBtn} onPress={() => onGoToDiagnose(code)}>
          <Text style={styles.itemActionBtnText}>去诊股</Text>
        </Pressable>
        <Pressable style={styles.itemActionDangerBtn} onPress={() => onRemove(code)}>
          <Text style={styles.itemActionDangerText}>移除</Text>
        </Pressable>
      </View>
    </View>
  );
}

function Metric({ label, value, valueStyle }: { label: string; value: string; valueStyle?: object }) {
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, valueStyle]} numberOfLines={1}>{value}</Text>
    </View>
  );
}

function IntradayMarkerCard({
  label,
  value,
  time,
  tone,
}: {
  label: string;
  value?: number;
  time?: string;
  tone: "high" | "low";
}) {
  const isHigh = tone === "high";
  const safeValue = value ?? 0;
  const safeTime = time ?? "";
  return (
    <View style={[styles.intradayMarkerCard, isHigh ? styles.intradayMarkerCardHigh : styles.intradayMarkerCardLow]}>
      <Text style={[styles.intradayMarkerLabel, isHigh ? styles.intradayHighText : styles.intradayLowText]}>{label}</Text>
      <Text style={[styles.intradayMarkerValue, isHigh ? styles.intradayHighText : styles.intradayLowText]} numberOfLines={1}>
        {formatMarkerPrice(safeValue)}
      </Text>
      <Text style={styles.intradayMarkerTime}>{safeTime ? `发生于 ${safeTime}` : "暂无时间"}</Text>
    </View>
  );
}

function MinuteVolumeChart({ points, limit = 18 }: { points?: MinuteVolumePoint[]; limit?: number }) {
  const safePoints = points ?? [];
  const chartPoints = buildMinuteChartPoints(safePoints, limit);
  if (chartPoints.length === 0) {
    return (
      <View style={styles.minuteChartEmpty}>
        <Text style={styles.minuteChartEmptyText}>暂无分钟图数据</Text>
      </View>
    );
  }

  const latestVolume = chartPoints[chartPoints.length - 1]?.volume ?? 0;
  const maxVolume = chartPoints.reduce((max, point) => Math.max(max, point.volume), 0);

  return (
    <View style={styles.minuteChartSection}>
      <View style={styles.minuteChartHeader}>
        <View>
          <Text style={styles.minuteChartTitle}>分钟图</Text>
          <Text style={styles.minuteChartSubtitle}>
            最近 {chartPoints.length} 分钟成交量 · 最高 {formatLargeNumber(maxVolume)} · 最新 {formatLargeNumber(latestVolume)}
          </Text>
        </View>
        <View style={styles.minuteChartBadge}>
          <Text style={styles.minuteChartBadgeText}>量图</Text>
        </View>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.minuteChartScroll}>
        {chartPoints.map((point) => (
          <View key={`${point.time}-${point.volume}`} style={styles.minuteChartColumn}>
            <View style={styles.minuteChartTrack}>
              <View
                style={[
                  styles.minuteChartBar,
                  point.isLatest ? styles.minuteChartBarLatest : styles.minuteChartBarNormal,
                  { height: point.height },
                ]}
              />
            </View>
            <Text style={[styles.minuteChartTime, point.isLatest ? styles.minuteChartTimeLatest : null]}>{formatMinuteLabel(point.time)}</Text>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

function buildMinuteChartPoints(points: MinuteVolumePoint[], limit: number): MinuteChartPoint[] {
  const slice = points.slice(-limit);
  if (slice.length === 0) {
    return [];
  }

  const maxVolume = slice.reduce((max, point) => Math.max(max, Number.isFinite(point.volume) ? point.volume : 0), 0);
  const safeMaxVolume = maxVolume > 0 ? maxVolume : 1;

  return slice.map((point, index) => {
    const volume = Number.isFinite(point.volume) ? point.volume : 0;
    return {
      ...point,
      volume,
      height: Math.max(10, Math.round((volume / safeMaxVolume) * 72)),
      isLatest: index === slice.length - 1,
    };
  });
}

function formatMinuteLabel(value: string): string {
  const label = String(value).trim();
  if (!label) {
    return "--";
  }

  if (label.length <= 5) {
    return label;
  }

  return label.slice(-5);
}

function resolveDraftAsset(query: string, selectedAsset: SearchItem | null, searchResults: SearchItem[]): SearchItem | null {
  if (selectedAsset) {
    return selectedAsset;
  }

  const keyword = query.trim();
  if (!keyword) {
    return null;
  }

  const exactMatch = searchResults.find((item) => item.code === keyword || item.name === keyword);
  if (exactMatch) {
    return exactMatch;
  }

  if (searchResults.length === 1) {
    return searchResults[0];
  }

  if (/^\d{6}$/.test(keyword)) {
    return { code: keyword, name: keyword };
  }

  return null;
}

function collectNotifications(payload: WatchlistSummaryResponse): WatchlistNotification[] {
  const queue = Array.isArray(payload.notifications) ? payload.notifications : [];
  const itemNotifications = payload.items.reduce<WatchlistNotification[]>((result, item) => {
    if (item.notification) {
      result.push(item.notification);
    }
    return result;
  }, []);
  return mergeNotifications(queue, itemNotifications);
}

function mergeNotifications(incoming: WatchlistNotification[], previous: WatchlistNotification[]): WatchlistNotification[] {
  const dedup = new Set<string>();
  const merged: WatchlistNotification[] = [];
  for (const item of [...incoming, ...previous]) {
    if (dedup.has(item.fingerprint)) {
      continue;
    }
    dedup.add(item.fingerprint);
    merged.push(item);
  }
  return merged;
}

function isAuthIssue(message: string): boolean {
  return /认证|登录|token|权限|过期/.test(message);
}

function formatPercent(value: number): string {
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}${(value * 100).toFixed(2)}%`;
}

function formatMoney(value: number): string {
  if (!Number.isFinite(value)) {
    return "-";
  }
  return `¥${value.toFixed(2)}`;
}

function formatMarkerPrice(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "--";
  }
  return formatMoney(value);
}

function formatLargeNumber(value: number): string {
  if (!Number.isFinite(value)) {
    return "-";
  }
  if (Math.abs(value) >= 100000000) {
    return `${(value / 100000000).toFixed(2)}亿`;
  }
  if (Math.abs(value) >= 10000) {
    return `${(value / 10000).toFixed(2)}万`;
  }
  return `${Math.round(value)}`;
}

function formatClock(date: Date): string {
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}:${String(date.getSeconds()).padStart(2, "0")}`;
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
    paddingBottom: 28,
    gap: 12,
  },
  headerCard: {
    backgroundColor: "#f7f1df",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#d7ccb5",
    padding: 14,
    gap: 8,
  },
  pageTitle: {
    fontSize: 26,
    fontWeight: "800",
    color: "#203627",
    fontFamily: "Georgia",
  },
  pageSubtitle: {
    marginTop: 4,
    fontSize: 13,
    color: "#4f6b5a",
  },
  headerMeta: {
    gap: 4,
  },
  headerMetaText: {
    fontSize: 11,
    color: "#6d4300",
    fontWeight: "600",
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
  },
  actionBtn: {
    flex: 1,
    height: 42,
    borderRadius: 12,
    backgroundColor: "#2a4a37",
    alignItems: "center",
    justifyContent: "center",
  },
  actionBtnOn: {
    backgroundColor: "#2a4a37",
  },
  actionBtnOff: {
    backgroundColor: "#6b7280",
  },
  actionBtnText: {
    color: "#ffffff",
    fontSize: 13,
    fontWeight: "800",
  },
  searchCard: {
    backgroundColor: "#fff9f0",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#f1d7b2",
    padding: 14,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: "800",
    color: "#6d4300",
  },
  sectionHint: {
    marginTop: 4,
    fontSize: 12,
    color: "#8a7352",
    lineHeight: 18,
  },
  searchRow: {
    marginTop: 10,
    flexDirection: "row",
    gap: 8,
  },
  searchInput: {
    flex: 1,
    height: 44,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#d6c8b0",
    backgroundColor: "#ffffff",
    paddingHorizontal: 12,
    color: "#1f3a2a",
    fontSize: 14,
  },
  searchBtn: {
    width: 76,
    borderRadius: 12,
    backgroundColor: "#2a4a37",
    alignItems: "center",
    justifyContent: "center",
  },
  searchBtnText: {
    color: "#ffffff",
    fontWeight: "800",
  },
  suggestionBox: {
    marginTop: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#ead9b8",
    backgroundColor: "#ffffff",
    padding: 8,
  },
  suggestionTitle: {
    fontSize: 12,
    color: "#6d4300",
    fontWeight: "800",
    marginBottom: 4,
  },
  suggestionItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#f1e6d2",
  },
  suggestionCode: {
    color: "#234130",
    fontWeight: "800",
    fontSize: 13,
  },
  suggestionName: {
    color: "#4f6b5a",
    fontSize: 13,
    marginLeft: 12,
    flex: 1,
    textAlign: "right",
  },
  emptyHint: {
    marginTop: 8,
    fontSize: 12,
    color: "#8a7352",
  },
  selectedAssetBox: {
    marginTop: 10,
    borderRadius: 12,
    backgroundColor: "#eef6ea",
    borderWidth: 1,
    borderColor: "#c6d9c0",
    padding: 10,
  },
  selectedAssetLabel: {
    fontSize: 11,
    color: "#2a4a37",
    fontWeight: "800",
  },
  selectedAssetTitle: {
    marginTop: 4,
    fontSize: 13,
    color: "#203627",
    fontWeight: "700",
  },
  recommendationSection: {
    marginTop: 12,
  },
  loadingRow: {
    marginTop: 8,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  loadingText: {
    fontSize: 12,
    color: "#013E75",
    fontWeight: "600",
  },
  recommendationRow: {
    gap: 8,
    paddingTop: 8,
    paddingRight: 4,
  },
  recommendationChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#d6c8b0",
  },
  recommendationChipActive: {
    backgroundColor: "#2a4a37",
    borderColor: "#2a4a37",
  },
  recommendationChipText: {
    fontSize: 12,
    color: "#6d4300",
    fontWeight: "700",
  },
  recommendationChipTextActive: {
    color: "#ffffff",
  },
  confirmRow: {
    marginTop: 12,
    flexDirection: "row",
    gap: 10,
  },
  confirmCancelBtn: {
    flex: 1,
    height: 42,
    borderRadius: 12,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#d6c8b0",
    alignItems: "center",
    justifyContent: "center",
  },
  confirmCancelText: {
    color: "#6d4300",
    fontWeight: "800",
  },
  confirmOkBtn: {
    flex: 2,
    height: 42,
    borderRadius: 12,
    backgroundColor: "#2a4a37",
    alignItems: "center",
    justifyContent: "center",
  },
  confirmOkText: {
    color: "#ffffff",
    fontWeight: "800",
  },
  errorBox: {
    padding: 12,
    borderRadius: 12,
    backgroundColor: "#ffe3e3",
    borderWidth: 1,
    borderColor: "#ffa8a8",
  },
  errorText: {
    color: "#a61e4d",
    fontWeight: "700",
    fontSize: 12,
  },
  feedCard: {
    backgroundColor: "#f4f8ef",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#d8e7d2",
    padding: 14,
    gap: 12,
  },
  feedHeader: {
    gap: 4,
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 28,
    gap: 8,
  },
  emptyStateTitle: {
    fontSize: 15,
    fontWeight: "800",
    color: "#203627",
  },
  emptyStateHint: {
    fontSize: 12,
    color: "#4f6b5a",
    textAlign: "center",
  },
  itemCard: {
    borderRadius: 16,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#d8e7d2",
    padding: 12,
    gap: 10,
  },
  itemHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 10,
  },
  itemCode: {
    fontSize: 14,
    fontWeight: "800",
    color: "#203627",
  },
  itemName: {
    marginTop: 2,
    fontSize: 12,
    color: "#4f6b5a",
  },
  actionBadge: {
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  actionBadgeText: {
    fontSize: 11,
    fontWeight: "800",
  },
  metricRow: {
    flexDirection: "row",
    gap: 8,
  },
  metricBox: {
    flex: 1,
    borderRadius: 12,
    backgroundColor: "#f8fbf6",
    borderWidth: 1,
    borderColor: "#e3edda",
    paddingHorizontal: 10,
    paddingVertical: 8,
    gap: 4,
  },
  metricLabel: {
    fontSize: 10,
    color: "#7c8b7a",
    fontWeight: "700",
  },
  metricValue: {
    fontSize: 12,
    color: "#203627",
    fontWeight: "800",
  },
  greenText: {
    color: "#2f9e44",
  },
  redText: {
    color: "#c92a2a",
  },
  intradayMarkerRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
  },
  intradayMarkerCard: {
    flex: 1,
    borderRadius: 14,
    paddingHorizontal: 10,
    paddingVertical: 10,
    borderWidth: 1,
    gap: 4,
  },
  intradayMarkerCardHigh: {
    backgroundColor: "#eef6ea",
    borderColor: "#c6d9c0",
  },
  intradayMarkerCardLow: {
    backgroundColor: "#fff3f1",
    borderColor: "#f1c2bc",
  },
  intradayMarkerLabel: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.2,
  },
  intradayMarkerValue: {
    fontSize: 13,
    fontWeight: "800",
  },
  intradayMarkerTime: {
    fontSize: 10,
    color: "#6d4300",
    fontWeight: "600",
  },
  intradayHighText: {
    color: "#2f9e44",
  },
  intradayLowText: {
    color: "#c92a2a",
  },
  minuteChartSection: {
    marginTop: 10,
    padding: 10,
    borderRadius: 14,
    backgroundColor: "#f8fbf6",
    borderWidth: 1,
    borderColor: "#d8e7d2",
    gap: 8,
  },
  minuteChartHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  minuteChartTitle: {
    fontSize: 12,
    color: "#234130",
    fontWeight: "800",
  },
  minuteChartSubtitle: {
    marginTop: 2,
    fontSize: 10,
    color: "#6d4300",
    fontWeight: "600",
  },
  minuteChartBadge: {
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: "#eef6ea",
    borderWidth: 1,
    borderColor: "#d8e7d2",
  },
  minuteChartBadgeText: {
    fontSize: 10,
    color: "#2a4a37",
    fontWeight: "800",
  },
  minuteChartScroll: {
    gap: 8,
    paddingRight: 2,
  },
  minuteChartColumn: {
    width: 24,
    alignItems: "center",
    gap: 4,
  },
  minuteChartTrack: {
    width: 16,
    height: 72,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#d8e7d2",
    backgroundColor: "#edf4eb",
    justifyContent: "flex-end",
    alignItems: "center",
    overflow: "hidden",
  },
  minuteChartBar: {
    width: 12,
    borderRadius: 999,
  },
  minuteChartBarNormal: {
    backgroundColor: "#8fb39b",
  },
  minuteChartBarLatest: {
    backgroundColor: "#2a4a37",
  },
  minuteChartTime: {
    fontSize: 9,
    color: "#6d4300",
    fontWeight: "700",
  },
  minuteChartTimeLatest: {
    color: "#234130",
  },
  minuteChartEmpty: {
    marginTop: 10,
    paddingVertical: 10,
    alignItems: "center",
    borderRadius: 14,
    backgroundColor: "#eef6ea",
    borderWidth: 1,
    borderColor: "#d8e7d2",
  },
  minuteChartEmptyText: {
    fontSize: 11,
    color: "#4f6b5a",
    fontWeight: "600",
  },
  minuteVolumeRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  minuteVolumeChip: {
    minWidth: 68,
    borderRadius: 12,
    backgroundColor: "#eef6ea",
    borderWidth: 1,
    borderColor: "#d8e7d2",
    paddingHorizontal: 8,
    paddingVertical: 6,
    alignItems: "center",
  },
  minuteVolumeTime: {
    fontSize: 10,
    color: "#4f6b5a",
    fontWeight: "700",
  },
  minuteVolumeValue: {
    marginTop: 2,
    fontSize: 11,
    color: "#203627",
    fontWeight: "800",
  },
  itemNotifyBox: {
    borderRadius: 12,
    backgroundColor: "#fff9f0",
    borderWidth: 1,
    borderColor: "#f1d7b2",
    padding: 10,
  },
  itemNotifyText: {
    fontSize: 12,
    color: "#6d4300",
    fontWeight: "700",
  },
  itemActionRow: {
    flexDirection: "row",
    gap: 8,
  },
  itemActionBtn: {
    flex: 1,
    height: 38,
    borderRadius: 12,
    backgroundColor: "#2a4a37",
    alignItems: "center",
    justifyContent: "center",
  },
  itemActionBtnText: {
    color: "#ffffff",
    fontWeight: "800",
    fontSize: 12,
  },
  itemActionDangerBtn: {
    width: 84,
    height: 38,
    borderRadius: 12,
    backgroundColor: "#ffe3e3",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#ffa8a8",
  },
  itemActionDangerText: {
    color: "#a61e4d",
    fontWeight: "800",
    fontSize: 12,
  },
  notifyCard: {
    backgroundColor: "#fff4e3",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#f0d7b7",
    padding: 14,
    gap: 8,
  },
  notifyItem: {
    borderRadius: 12,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#f1e1c5",
    padding: 10,
    gap: 4,
  },
  notifyText: {
    fontSize: 12,
    color: "#5f3b00",
    fontWeight: "700",
  },
  notifyMeta: {
    fontSize: 11,
    color: "#8a7352",
    fontWeight: "600",
  },
});
