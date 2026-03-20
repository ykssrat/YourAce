/// <reference path="../react_native_shims.d.ts" />
import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { diagnoseAsset, searchAssets } from "../services/api";
import { DiagnoseResponse, SearchItem, STRATEGY_OPTIONS } from "../types";
import { OpinionMatrixCard } from "./OpinionMatrix";
import { ScoreSignalCard } from "./ScoreSignalCard";

type DiagnoseTabProps = {
  apiBaseUrl: string;
  newsEnabled: boolean;
  initialCode?: string;
};

export function DiagnoseTab({ apiBaseUrl, newsEnabled, initialCode }: DiagnoseTabProps) {
  const [query, setQuery] = useState(initialCode ?? "");
  const [strategy, setStrategy] = useState("momentum_deviation");
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [suggestions, setSuggestions] = useState<SearchItem[]>([]);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DiagnoseResponse | null>(null);
  const analyzingRef = useRef(false);

  useEffect(() => {
    if (initialCode && initialCode.trim()) {
      setQuery(initialCode.trim());
      void handleDiagnose(initialCode.trim());
    }
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
      const data = await diagnoseAsset(finalCode, apiBaseUrl, {
        strategy,
        include_news: newsEnabled,
      });
      setResult(data);
      setQuery(finalCode);
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      analyzingRef.current = false;
      setLoading(false);
    }
  }

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
      <Text style={styles.pageSubtitle}>输入代码查看三个窗口期的诊断与共识看法</Text>

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

        {suggestions.length > 0 ? (
          <View style={styles.suggestionBox}>
            <Text style={styles.suggestionTitle}>{searching ? "搜索中..." : "搜索建议"}</Text>
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

      <View style={styles.strategyRow}>
        <Text style={styles.strategyLabel}>策略算法:</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.strategyScroll}>
          {STRATEGY_OPTIONS.map((opt) => (
            <Pressable
              key={opt.value}
              onPress={() => {
                if (opt.value !== "momentum_deviation") {
                  Alert.alert("该策略暂未上线", "敬请期待");
                  return;
                }
                setStrategy(opt.value);
              }}
              style={[
                styles.strategyChip,
                strategy === opt.value && styles.strategyChipActive,
              ]}
            >
              <Text
                style={[
                  styles.strategyChipText,
                  strategy === opt.value && styles.strategyChipTextActive,
                ]}
              >
                {opt.label}
              </Text>
            </Pressable>
          ))}
        </ScrollView>
      </View>

      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <ScoreSignalCard result={result} />

      {result?.matrix ? (
        <View style={styles.matrixCard}>
          <Text style={styles.matrixTitle}>三个窗口期看法矩阵</Text>
          <OpinionMatrixCard matrix={result.matrix} />
        </View>
      ) : null}
    </ScrollView>
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
  strategyRow: {
    marginTop: 12,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff9f0",
    borderRadius: 12,
    padding: 8,
    borderWidth: 1,
    borderColor: "#f1d7b2",
  },
  strategyLabel: {
    fontSize: 12,
    fontWeight: "700",
    color: "#6d4300",
    marginRight: 8,
  },
  strategyScroll: {
    gap: 8,
  },
  strategyChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#f1d7b2",
  },
  strategyChipActive: {
    backgroundColor: "#2a4a37",
    borderColor: "#2a4a37",
  },
  strategyChipText: {
    fontSize: 12,
    color: "#6d4300",
  },
  strategyChipTextActive: {
    color: "#fff",
    fontWeight: "700",
  },
});
