/// <reference path="../react_native_shims.d.ts" />
import React, { useState } from "react";
import {
  Alert,
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { logScreenAction, screenAssets } from "../services/api";
import { Opinion, ScreenItem, STRATEGY_OPTIONS } from "../types";

// 筛选参数类型
type ScreenFilter = {
  asset_type: "" | "stock" | "etf" | "fund";
  horizon: "" | "short" | "mid" | "long";
  opinion: Opinion | "";
  strategy: string;
};

const ASSET_TYPE_OPTIONS: { value: ScreenFilter["asset_type"]; label: string }[] = [
  { value: "", label: "不限" },
  { value: "stock", label: "股票" },
  { value: "etf", label: "ETF" },
  { value: "fund", label: "场外基金" },
];

const HORIZON_OPTIONS: { value: ScreenFilter["horizon"]; label: string }[] = [
  { value: "", label: "不限" },
  { value: "short", label: "短期" },
  { value: "mid", label: "中期" },
  { value: "long", label: "长期" },
];


const OPINION_OPTIONS: { value: Opinion | ""; label: string }[] = [
  { value: "", label: "不限" },
  { value: "BUY", label: "看多" },
  { value: "HOLD", label: "观望" },
  { value: "SELL", label: "看空" },
];

const OPINION_COLORS: Record<string, string> = {
  BUY: "#2f9e44",
  HOLD: "#f08c00",
  SELL: "#c92a2a",
};

const LABEL_MAP: Record<string, string> = {
  BUY: "看多",
  HOLD: "观望",
  SELL: "看空",
};

type ScreenTabProps = {
  apiBaseUrl: string;
  onGoToDiagnose: (code: string) => void;
};

const DEFAULT_FILTER: ScreenFilter = {
  asset_type: "",
  horizon: "",
  opinion: "",
  strategy: "momentum_deviation",
};

export function ScreenTab({ apiBaseUrl, onGoToDiagnose }: ScreenTabProps) {
  const [filter, setFilter] = useState<ScreenFilter>(DEFAULT_FILTER);
  const [filterCollapsed, setFilterCollapsed] = useState(false);

  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<ScreenItem[]>([]);
  const [stats, setStats] = useState({
    scanned: 0,
    signalMiss: 0,
    rounds: 0,
    hasMore: false,
    totalAvailable: 0,
  });
  const [error, setError] = useState("");

  const ROUND_SIZE = 50;

  async function handleStart() {
    setRunning(true);
    setFilterCollapsed(true);  // 开始选股后折叠筛选区
    setResults([]);
    setError("");
    setStats({ scanned: 0, signalMiss: 0, rounds: 0, hasMore: false, totalAvailable: 0 });

    try {
      const resp = await screenAssets(
        {
          asset_type: filter.asset_type,
          horizon: filter.horizon,
          opinion: filter.opinion,
          strategy: filter.strategy,
          round_size: ROUND_SIZE,
          offset: 0,
        },
        apiBaseUrl,
      );

      setResults(resp.items);
      setStats({
        scanned: resp.scanned_count,
        signalMiss: resp.signal_miss_count,
        rounds: 1,
        hasMore: resp.has_more,
        totalAvailable: resp.total_available,
      });
      void logScreenAction({
        asset_type: filter.asset_type,
        horizon: filter.horizon,
        opinion: filter.opinion,
        strategy: filter.strategy,
        round_size: ROUND_SIZE,
        offset: 0,
        result_count: resp.items.length,
        total_available: resp.total_available,
        scanned_count: resp.scanned_count,
        signal_miss_count: resp.signal_miss_count,
      }, apiBaseUrl).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      setRunning(false);
    }
  }

  async function handleLoadMore() {
    if (running || !stats.hasMore) {
      return;
    }
    setRunning(true);
    setError("");

    try {
      const nextOffset = stats.rounds * ROUND_SIZE;
      const resp = await screenAssets(
        {
          asset_type: filter.asset_type,
          horizon: filter.horizon,
          opinion: filter.opinion,
          strategy: filter.strategy,
          round_size: ROUND_SIZE,
          offset: nextOffset,
        },
        apiBaseUrl,
      );

      setResults((prev) => [...prev, ...resp.items]);
      setStats((prev) => ({
        scanned: prev.scanned + resp.scanned_count,
        signalMiss: prev.signalMiss + resp.signal_miss_count,
        rounds: prev.rounds + 1,
        hasMore: resp.has_more,
        totalAvailable: resp.total_available,
      }));
      void logScreenAction({
        asset_type: filter.asset_type,
        horizon: filter.horizon,
        opinion: filter.opinion,
        strategy: filter.strategy,
        round_size: ROUND_SIZE,
        offset: nextOffset,
        result_count: resp.items.length,
        total_available: resp.total_available,
        scanned_count: resp.scanned_count,
        signal_miss_count: resp.signal_miss_count,
      }, apiBaseUrl).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      setRunning(false);
    }
  }

  function handleReset() {
    setFilter(DEFAULT_FILTER);
    setFilterCollapsed(false);
    setResults([]);
    setError("");
    setStats({ scanned: 0, signalMiss: 0, rounds: 0, hasMore: false, totalAvailable: 0 });
  }


  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.pageTitle}>选股</Text>
      <Text style={styles.pageSubtitle}>按窗口期和主观看法筛选候选标的</Text>

      {/* 筛选区：运行中折叠为摘要栏 */}
      {filterCollapsed ? (
        <Pressable style={styles.filterSummary} onPress={() => setFilterCollapsed(false)}>
          <Text style={styles.filterSummaryText}>
            {ASSET_TYPE_OPTIONS.find((o) => o.value === filter.asset_type)?.label ?? filter.asset_type}
            {" · "}
            {HORIZON_OPTIONS.find((o) => o.value === filter.horizon)?.label ?? (filter.horizon || "不限")}
            {" · "}
            {STRATEGY_OPTIONS.find((o) => o.value === filter.strategy)?.label ?? filter.strategy}
            {filter.opinion ? " · " + (LABEL_MAP[filter.opinion] ?? filter.opinion) : " · 看法不限"}
          </Text>
          <Text style={styles.filterSummaryEdit}>▼ 展开修改</Text>
        </Pressable>
      ) : (
      <View style={styles.filterCard}>
        <FilterRow label="策略算法">
          {STRATEGY_OPTIONS.map(({ value, label }) => (
            <OptionChip
              key={value}
              label={label}
              active={filter.strategy === value}
              onPress={() => {
                if (value !== "momentum_deviation") {
                  Alert.alert("该策略暂未上线", "敬请期待");
                  return;
                }
                setFilter({ ...filter, strategy: value });
              }}
            />
          ))}
        </FilterRow>

        <FilterRow label="产品类型">
          {ASSET_TYPE_OPTIONS.map(({ value, label }) => (
            <OptionChip
              key={value}
              label={label}
              active={filter.asset_type === value}
              onPress={() => setFilter({ ...filter, asset_type: value })}
            />
          ))}
        </FilterRow>

        <FilterRow label="窗口期">
          {HORIZON_OPTIONS.map(({ value, label }) => (
            <OptionChip
              key={value}
              label={label}
              active={filter.horizon === value}
              onPress={() => setFilter({ ...filter, horizon: value })}
            />
          ))}
        </FilterRow>


        <FilterRow label="看法">
          {OPINION_OPTIONS.map(({ value, label }) => (
            <OptionChip
              key={value}
              label={label}
              active={filter.opinion === value}
              onPress={() => setFilter({ ...filter, opinion: value })}
            />
          ))}
        </FilterRow>
      </View>
      )}

      {/* 操作区 */}
      <View style={styles.actionRow}>
        <Pressable style={styles.primaryBtn} onPress={handleStart} disabled={running}>
          {running ? (
            <ActivityIndicator color="#ffffff" size="small" />
          ) : (
            <Text style={styles.primaryBtnText}>开始选股</Text>
          )}
        </Pressable>
        <Pressable style={styles.secondaryBtn} onPress={handleReset} disabled={running}>
          <Text style={styles.secondaryBtnText}>重置</Text>
        </Pressable>
      </View>

      {/* 进度统计 */}
      {stats.rounds > 0 ? (
        <View style={styles.statsCard}>
          <Text style={styles.statsTitle}>扫描进度</Text>
          <View style={styles.statsGrid}>
            <StatItem label="已扫描" value={stats.scanned} />
            <StatItem label="信号不匹配" value={stats.signalMiss} />
            <StatItem label="命中结果" value={results.length} />
          </View>
          <Text style={styles.statsHint}>
            第 {stats.rounds} 轮 · 共 {stats.totalAvailable} 个可用标的
          </Text>
        </View>
      ) : null}

      {/* 错误提示 */}
      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {/* 结果列表 */}
      {results.length > 0 ? (
        <View style={styles.resultsSection}>
          <Text style={styles.resultsTitle}>命中标的 ({results.length})</Text>
          {results.map((item) => (
            <ScreenResultCard
              key={item.code}
              item={item}
              onDiagnose={() => onGoToDiagnose(item.code)}
            />
          ))}

          {stats.hasMore ? (
            <Pressable style={styles.loadMoreBtn} onPress={handleLoadMore} disabled={running}>
              {running ? (
                <ActivityIndicator color="#2a4a37" size="small" />
              ) : (
                <Text style={styles.loadMoreText}>继续扫描下一轮</Text>
              )}
            </Pressable>
          ) : (
            <Text style={styles.noMoreText}>已扫描全部标的</Text>
          )}
        </View>
      ) : stats.rounds > 0 && !running ? (
        <View style={styles.emptyBox}>
          <Text style={styles.emptyTitle}>本轮无命中</Text>
          <Text style={styles.emptyHint}>
            建议：切换筛选的窗口期，或将看法改为「不限」
          </Text>
          {stats.hasMore ? (
            <Pressable style={styles.loadMoreBtn} onPress={handleLoadMore} disabled={running}>
              <Text style={styles.loadMoreText}>继续扫描下一轮</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}
    </ScrollView>
  );
}

// 单结果卡片
function ScreenResultCard({
  item,
  onDiagnose,
}: {
  item: ScreenItem;
  onDiagnose: () => void;
}) {
  const labelColor = OPINION_COLORS[item.label] ?? "#555";
  return (
    <View style={styles.resultCard}>
      <View style={styles.resultCardHeader}>
        <View>
          <Text style={styles.resultCode}>{item.code}</Text>
          <Text style={styles.resultName}>{item.name}</Text>
        </View>
        <View style={styles.resultScoreBox}>
          <Text style={[styles.resultLabel, { color: labelColor }]}>{LABEL_MAP[item.label] ?? item.label}</Text>
        </View>
      </View>

      <View style={styles.resultSignalRow}>
        {(["short", "mid", "long"] as const).map((h) => {
          const sig = item.horizon_signals[h];
          const sigColor = sig === "BUY" ? "#2f9e44" : sig === "SELL" ? "#c92a2a" : "#f08c00";
          const hLabel = h === "short" ? "短" : h === "mid" ? "中" : "长";
          return (
            <View key={h} style={styles.signalChip}>
              <Text style={styles.signalChipLabel}>{hLabel}</Text>
              <Text style={[styles.signalChipValue, { color: sigColor }]}>{sig}</Text>
            </View>
          );
        })}
      </View>

      <Pressable style={styles.diagnoseBtn} onPress={onDiagnose}>
        <Text style={styles.diagnoseBtnText}>进入诊股 →</Text>
      </Pressable>
    </View>
  );
}

// 筛选行容器
function FilterRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.filterRow}>
      <Text style={styles.filterLabel}>{label}</Text>
      <View style={styles.filterOptions}>{children}</View>
    </View>
  );
}

// 选项芯片
function OptionChip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[styles.chip, active && styles.chipActive]}
      onPress={onPress}
    >
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

// 统计格
function StatItem({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.statItem}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
    paddingBottom: 32,
  },
  pageTitle: {
    fontSize: 26,
    fontWeight: "700",
    color: "#203627",
    fontFamily: "Georgia",
  },
  pageSubtitle: {
    marginTop: 4,
    fontSize: 13,
    color: "#4f6b5a",
    marginBottom: 14,
  },
  filterCard: {
    backgroundColor: "#f7f1df",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#d7ccb5",
    padding: 12,
    gap: 10,
  },
  filterSummary: {
    backgroundColor: "#f7f1df",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#d7ccb5",
    paddingHorizontal: 14,
    paddingVertical: 10,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  filterSummaryText: {
    fontSize: 12,
    color: "#2a4a37",
    fontWeight: "600",
    flex: 1,
  },
  filterSummaryEdit: {
    fontSize: 11,
    color: "#7c8b7a",
    marginLeft: 8,
  },
  filterRow: {
    gap: 6,
  },
  filterLabel: {
    fontSize: 12,
    fontWeight: "700",
    color: "#2a4a37",
  },
  filterOptions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: "#eef6ea",
    borderWidth: 1,
    borderColor: "#c6d9c0",
  },
  chipActive: {
    backgroundColor: "#2a4a37",
    borderColor: "#2a4a37",
  },
  chipText: {
    fontSize: 12,
    color: "#335240",
    fontWeight: "600",
  },
  chipTextActive: {
    color: "#ffffff",
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 14,
  },
  primaryBtn: {
    flex: 1,
    height: 44,
    borderRadius: 12,
    backgroundColor: "#2a4a37",
    justifyContent: "center",
    alignItems: "center",
  },
  primaryBtnText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 15,
  },
  secondaryBtn: {
    paddingHorizontal: 20,
    height: 44,
    borderRadius: 12,
    backgroundColor: "#eef6ea",
    borderWidth: 1,
    borderColor: "#c6d9c0",
    justifyContent: "center",
    alignItems: "center",
  },
  secondaryBtnText: {
    color: "#2a4a37",
    fontWeight: "600",
    fontSize: 14,
  },
  statsCard: {
    marginTop: 14,
    backgroundColor: "#eef6ea",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#c6d9c0",
    padding: 12,
  },
  statsTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: "#2a4a37",
    marginBottom: 8,
  },
  statsGrid: {
    flexDirection: "row",
    justifyContent: "space-around",
  },
  statItem: {
    alignItems: "center",
  },
  statValue: {
    fontSize: 20,
    fontWeight: "800",
    color: "#203627",
  },
  statLabel: {
    fontSize: 11,
    color: "#4f6b5a",
    marginTop: 2,
  },
  statsHint: {
    marginTop: 8,
    fontSize: 11,
    color: "#7c8b7a",
    textAlign: "center",
  },
  errorBox: {
    marginTop: 12,
    padding: 10,
    borderRadius: 10,
    backgroundColor: "#ffe3e3",
    borderWidth: 1,
    borderColor: "#ffa8a8",
  },
  errorText: {
    color: "#a61e4d",
    fontWeight: "600",
    fontSize: 13,
  },
  resultsSection: {
    marginTop: 16,
  },
  resultsTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#203627",
    marginBottom: 10,
  },
  resultCard: {
    backgroundColor: "#fff4e3",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#f0d7b7",
    padding: 12,
    marginBottom: 10,
  },
  resultCardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  resultCode: {
    fontSize: 15,
    fontWeight: "800",
    color: "#203627",
  },
  resultName: {
    fontSize: 12,
    color: "#4f6b5a",
    marginTop: 2,
  },
  resultScoreBox: {
    alignItems: "flex-end",
  },
  resultLabel: {
    fontSize: 12,
    fontWeight: "700",
  },
  resultSignalRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
  },
  signalChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "#fff9f0",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderWidth: 1,
    borderColor: "#f1d7b2",
  },
  signalChipLabel: {
    fontSize: 11,
    color: "#7b5b35",
    fontWeight: "600",
  },
  signalChipValue: {
    fontSize: 11,
    fontWeight: "700",
  },
  diagnoseBtn: {
    marginTop: 10,
    paddingVertical: 7,
    borderRadius: 8,
    backgroundColor: "#eef6ea",
    borderWidth: 1,
    borderColor: "#c6d9c0",
    alignItems: "center",
  },
  diagnoseBtnText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#2a4a37",
  },
  loadMoreBtn: {
    marginTop: 10,
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#d8e7d2",
    backgroundColor: "#eef6ea",
    alignItems: "center",
  },
  loadMoreText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#2a4a37",
  },
  noMoreText: {
    marginTop: 10,
    textAlign: "center",
    fontSize: 12,
    color: "#7c8b7a",
  },
  emptyBox: {
    marginTop: 16,
    padding: 16,
    backgroundColor: "#f4f8ef",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#d8e7d2",
    alignItems: "center",
  },
  emptyTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#335240",
  },
  emptyHint: {
    marginTop: 8,
    fontSize: 12,
    color: "#4f6b5a",
    textAlign: "center",
    lineHeight: 18,
  },
});
