/// <reference path="./src/react_native_shims.d.ts" />
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Pressable, SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, View } from "react-native";

import { ScoreSignalCard } from "./src/components/ScoreSignalCard";
import { SearchPanel } from "./src/components/SearchPanel";
import { WatchlistPanel } from "./src/components/WatchlistPanel";
import { analyzeAsset, searchAssets } from "./src/services/api";
import { AnalyzeResponse, SearchItem } from "./src/types";

export default function App() {
  const [query, setQuery] = useState("000001");
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [suggestions, setSuggestions] = useState<SearchItem[]>([]);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const analyzingRef = useRef(false);

  const watchlist = useMemo(() => ["000001", "600519", "510300", "159915"], []);

  async function handleAnalyze(inputCode?: string) {
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
      const data = await analyzeAsset(finalCode);
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
        const items = await searchAssets(keyword, 8);
        setSuggestions(items);
      } catch {
        setSuggestions([]);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor="#dfe9db" />
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.header}>YourAce 移动端原型</Text>

        <SearchPanel
          query={query}
          onQueryChange={setQuery}
          onSubmit={handleAnalyze}
          loading={loading}
        />

        <WatchlistPanel
          items={watchlist}
          onPick={(code) => {
            setQuery(code);
            void handleAnalyze(code);
          }}
        />

        {suggestions.length > 0 ? (
          <View style={styles.suggestionBox}>
            <Text style={styles.suggestionTitle}>{searching ? "检索中..." : "搜索建议"}</Text>
            {suggestions.map((item: SearchItem) => (
              <Pressable
                key={`${item.code}-${item.name}`}
                style={styles.suggestionItem}
                onPress={() => {
                  setQuery(item.code);
                  void handleAnalyze(item.code);
                }}
              >
                <Text style={styles.suggestionCode}>{item.code}</Text>
                <Text style={styles.suggestionName}>{item.name}</Text>
              </Pressable>
            ))}
          </View>
        ) : null}

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        <ScoreSignalCard result={result} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#dfe9db",
  },
  container: {
    padding: 16,
    paddingBottom: 24,
  },
  header: {
    fontSize: 28,
    fontFamily: "Georgia",
    fontWeight: "700",
    color: "#203627",
    marginBottom: 12,
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
  },
  suggestionBox: {
    marginTop: 12,
    backgroundColor: "#f4f8ef",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#d7e4cf",
    padding: 10,
  },
  suggestionTitle: {
    fontSize: 13,
    color: "#335240",
    fontWeight: "700",
    marginBottom: 6,
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
  },
  suggestionName: {
    color: "#4f6b5a",
    marginLeft: 12,
    flex: 1,
    textAlign: "right",
  },
});
