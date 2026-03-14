/// <reference path="../react_native_shims.d.ts" />
import React, { useEffect, useRef, useState } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { diagnoseAsset, searchAssets } from "../services/api";
import { DiagnoseResponse, SearchItem } from "../types";
import { OpinionMatrixCard } from "./OpinionMatrix";
import { ScoreSignalCard } from "./ScoreSignalCard";

const LABEL_MAP: Record<string, string> = {
  STRONG_BUY: "强烈看多",
  BUY: "看多",
  HOLD: "观望",
  SELL: "看空",
  STRONG_SELL: "强烈看空",
};

type DiagnoseTabProps = {
  apiBaseUrl: string;
  newsEnabled: boolean;
  /** 从选股跳转时预填的代码 */
  initialCode?: string;
};

export function DiagnoseTab({ apiBaseUrl, newsEnabled, initialCode }: DiagnoseTabProps) {
  const [query, setQuery] = useState(initialCode ?? "");
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [suggestions, setSuggestions] = useState<SearchItem[]>([]);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DiagnoseResponse | null>(null);
  const analyzingRef = useRef(false);

  // 从选股跳转时自动触发诊断
  useEffect(() => {
    if (initialCode && initialCode.trim()) {
      setQuery(initialCode.trim());
      void handleDiagnose(initialCode.trim());
    }
    // 仅在 initialCode 变化时触发
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialCode]);

  async function handleDiagnose(inputCode?: string) {
    const finalCode = (inputCode ?? query).trim();
    if (!finalCode) {
      setError("请输入代码或名称");
      return;
    }

    if (analyzingRef.current) {
      return;
    }

    try {
      analyzingRef.current = true;
      setLoading(true);
      setError("");
      setSuggestions([]);
      const data = await diagnoseAsset(finalCode, apiBaseUrl, newsEnabled);
      setResult(data);
      setQuery(finalCode);
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      analyzingRef.current = false;
      setLoading(false);
    }
  }

  // 搜索建议防抖
  useEffect(() => {
    const keyword = query.trim();
    if (!keyword) {
      setSuggestions([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setSearching(true);
        const items = await searchAssets(keyword, 8, apiBaseUrl);
        setSuggestions(items);
      } catch {
        setSuggestions([]);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query, apiBaseUrl]);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.pageTitle}>诊股</Text>
      <Text style={styles.pageSubtitle}>输入代码查看三窗口诊断与总体分数</Text>

      {/* 输入区 */}
      <View style={styles.inputCard}>
        <View style={styles.inputRow}>
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="例如 000001 或 平安银行"
            placeholderTextColor="#7c8b7a"
            style={styles.input}
          />
          <Pressable style={styles.diagnoseBtn} onPress={() => handleDiagnose()} disabled={loading}>
            <Text style={styles.diagnoseBtnText}>{loading ? "分析中" : "诊断"}</Text>
          </Pressable>
        </View>

        {/* 搜索建议 */}
        {suggestions.length > 0 ? (
          <View style={styles.suggestionBox}>
            <Text style={styles.suggestionTitle}>{searching ? "检索中..." : "搜索建议"}</Text>
            {suggestions.map((item) => (
              <Pressable
                key={`${item.code}-${item.name}`}
                style={styles.suggestionItem}
                onPress={() => {
                  setQuery(item.code);
                  void handleDiagnose(item.code);
                }}
              >
                <Text style={styles.suggestionCode}>{item.code}</Text>
                <Text style={styles.suggestionName}>{item.name}</Text>
              </Pressable>
            ))}
          </View>
        ) : null}
      </View>

      {/* 错误提示 */}
      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {/* 总览卡片（复用已有 ScoreSignalCard） */}
      <ScoreSignalCard result={result} />

      {/* 看法矩阵卡片 */}
      {result?.matrix ? (
        <View style={styles.matrixCard}>
          <Text style={styles.matrixTitle}>三窗口看法矩阵</Text>
          <Text style={styles.matrixSubtitle}>
            每行高亮当前窗口期的看法位置 · 总分综合了三个窗口期的加权结果
          </Text>
          <OpinionMatrixCard matrix={result.matrix} />

          {/* 结构解读 */}
          <View style={styles.structSection}>
            <Text style={styles.structTitle}>结构解读</Text>
            <StructLine
              horizon="短期"
              signal={result.horizon_signals.short}
              matrixOpinion={result.matrix.short}
            />
            <StructLine
              horizon="中期"
              signal={result.horizon_signals.mid}
              matrixOpinion={result.matrix.mid}
            />
            <StructLine
              horizon="长期"
              signal={result.horizon_signals.long}
              matrixOpinion={result.matrix.long}
            />
          </View>
        </View>
      ) : null}

      {/* 选中特征 */}
      {result && result.selected_features.length > 0 ? (
        <View style={styles.featureCard}>
          <Text style={styles.featureTitle}>选中特征 ({result.selected_features.length})</Text>
          <Text style={styles.featureList}>{result.selected_features.join("  ·  ")}</Text>
        </View>
      ) : null}
    </ScrollView>
  );
}

function StructLine({
  horizon,
  signal,
  matrixOpinion,
}: {
  horizon: string;
  signal: string;
  matrixOpinion: string;
}) {
  const opinionLabel = LABEL_MAP[matrixOpinion] ?? matrixOpinion;
  const signalColor = signal === "BUY" ? "#2f9e44" : signal === "SELL" ? "#c92a2a" : "#f08c00";
  return (
    <View style={styles.structLine}>
      <Text style={styles.structHorizon}>{horizon}</Text>
      <Text style={[styles.structSignal, { color: signalColor }]}>{signal}</Text>
      <Text style={styles.structArrow}>→</Text>
      <Text style={styles.structOpinion}>{opinionLabel}</Text>
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
  inputCard: {
    backgroundColor: "#f7f1df",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#d7ccb5",
    padding: 12,
  },
  inputRow: {
    flexDirection: "row",
    gap: 8,
  },
  input: {
    flex: 1,
    height: 44,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#c6d9c0",
    backgroundColor: "#ffffff",
    color: "#1f3a2a",
    paddingHorizontal: 12,
    fontSize: 14,
  },
  diagnoseBtn: {
    width: 72,
    height: 44,
    borderRadius: 12,
    backgroundColor: "#2a4a37",
    justifyContent: "center",
    alignItems: "center",
  },
  diagnoseBtnText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 14,
  },
  suggestionBox: {
    marginTop: 10,
    backgroundColor: "#fff",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#d8e7d2",
    padding: 8,
  },
  suggestionTitle: {
    fontSize: 12,
    color: "#335240",
    fontWeight: "700",
    marginBottom: 4,
  },
  suggestionItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#e3edda",
  },
  suggestionCode: {
    color: "#234130",
    fontWeight: "700",
    fontSize: 13,
  },
  suggestionName: {
    color: "#4f6b5a",
    fontSize: 13,
    marginLeft: 12,
    flex: 1,
    textAlign: "right",
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
  matrixCard: {
    marginTop: 14,
    backgroundColor: "#f4f8ef",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#d8e7d2",
    padding: 12,
  },
  matrixTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#203627",
  },
  matrixSubtitle: {
    marginTop: 4,
    fontSize: 11,
    color: "#4f6b5a",
    lineHeight: 16,
  },
  structSection: {
    marginTop: 12,
    backgroundColor: "#eef6ea",
    borderRadius: 10,
    padding: 10,
    gap: 6,
  },
  structTitle: {
    fontSize: 12,
    fontWeight: "700",
    color: "#2a4a37",
    marginBottom: 4,
  },
  structLine: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  structHorizon: {
    width: 32,
    fontSize: 12,
    fontWeight: "700",
    color: "#2a4a37",
  },
  structSignal: {
    width: 36,
    fontSize: 12,
    fontWeight: "700",
  },
  structArrow: {
    fontSize: 12,
    color: "#7c8b7a",
  },
  structOpinion: {
    fontSize: 12,
    color: "#335240",
    fontWeight: "600",
  },
  featureCard: {
    marginTop: 12,
    backgroundColor: "#fff9f0",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#f1d7b2",
    padding: 12,
  },
  featureTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: "#6d4300",
    marginBottom: 6,
  },
  featureList: {
    fontSize: 12,
    color: "#5f3b00",
    lineHeight: 20,
  },
});
