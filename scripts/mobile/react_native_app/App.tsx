import React, { useMemo, useState } from "react";
import { SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, View } from "react-native";

import { ScoreSignalCard } from "./src/components/ScoreSignalCard";
import { SearchPanel } from "./src/components/SearchPanel";
import { WatchlistPanel } from "./src/components/WatchlistPanel";
import { analyzeAsset } from "./src/services/api";
import { AnalyzeResponse } from "./src/types";

export default function App() {
  const [query, setQuery] = useState("000001");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  const watchlist = useMemo(() => ["000001", "600519", "510300", "159915"], []);

  async function handleAnalyze() {
    if (!query.trim()) {
      setError("请输入代码或名称");
      return;
    }

    try {
      setLoading(true);
      setError("");
      const data = await analyzeAsset(query.trim());
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

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
            void handleAnalyze();
          }}
        />

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
});
