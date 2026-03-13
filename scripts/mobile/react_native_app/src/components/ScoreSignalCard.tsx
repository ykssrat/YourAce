import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { AnalyzeResponse } from "../types";

type ScoreSignalCardProps = {
  result: AnalyzeResponse | null;
};

const labelMap: Record<string, string> = {
  STRONG_BUY: "强烈看多",
  BUY: "较为看多",
  HOLD: "观望",
  SELL: "较为看空",
  STRONG_SELL: "强烈看空",
};

function signalColor(signal: "BUY" | "HOLD" | "SELL"): string {
  if (signal === "BUY") {
    return "#2f9e44";
  }
  if (signal === "SELL") {
    return "#c92a2a";
  }
  return "#f08c00";
}

export function ScoreSignalCard(props: ScoreSignalCardProps) {
  if (!props.result) {
    return (
      <View style={styles.emptyCard}>
        <Text style={styles.emptyText}>等待分析结果...</Text>
      </View>
    );
  }

  const { score, label, horizon_signals } = props.result;
  return (
    <View style={styles.card}>
      <Text style={styles.title}>评分仪表盘</Text>
      <View style={styles.scoreRing}>
        <Text style={styles.scoreText}>{score}</Text>
      </View>
      <Text style={styles.labelText}>{labelMap[label] ?? label}</Text>

      <View style={styles.row}>
        <TrafficLight title="短期" signal={horizon_signals.short} />
        <TrafficLight title="中期" signal={horizon_signals.mid} />
        <TrafficLight title="长期" signal={horizon_signals.long} />
      </View>
    </View>
  );
}

function TrafficLight(props: { title: string; signal: "BUY" | "HOLD" | "SELL" }) {
  return (
    <View style={styles.lightBox}>
      <Text style={styles.lightTitle}>{props.title}</Text>
      <View style={[styles.lightDot, { backgroundColor: signalColor(props.signal) }]} />
      <Text style={styles.lightSignal}>{props.signal}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginTop: 14,
    backgroundColor: "#fff4e3",
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    borderColor: "#f0d7b7",
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    color: "#5f3b00",
  },
  scoreRing: {
    marginTop: 12,
    width: 118,
    height: 118,
    borderRadius: 59,
    borderWidth: 8,
    borderColor: "#ffa94d",
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "center",
    backgroundColor: "#fff9f0",
  },
  scoreText: {
    fontSize: 34,
    fontWeight: "800",
    color: "#8c5100",
  },
  labelText: {
    marginTop: 10,
    textAlign: "center",
    fontSize: 15,
    fontWeight: "700",
    color: "#7a3e00",
  },
  row: {
    marginTop: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 10,
  },
  lightBox: {
    flex: 1,
    backgroundColor: "#fff",
    borderRadius: 12,
    paddingVertical: 10,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#f1d7b2",
  },
  lightTitle: {
    color: "#7b5b35",
    fontSize: 12,
    fontWeight: "600",
  },
  lightDot: {
    marginTop: 8,
    width: 16,
    height: 16,
    borderRadius: 8,
  },
  lightSignal: {
    marginTop: 6,
    color: "#5c4d35",
    fontWeight: "700",
    fontSize: 11,
  },
  emptyCard: {
    marginTop: 14,
    backgroundColor: "#f2f2f2",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
  },
  emptyText: {
    color: "#666",
    fontSize: 14,
  },
});
