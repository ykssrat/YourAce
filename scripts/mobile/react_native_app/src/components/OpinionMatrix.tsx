/// <reference path="../react_native_shims.d.ts" />
import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { Opinion, OpinionMatrix } from "../types";

const OPINIONS: Opinion[] = ["BUY", "HOLD", "SELL"];

const OPINION_LABELS: Record<Opinion, string> = {
  BUY: "看多",
  HOLD: "观望",
  SELL: "看空",
};

const OPINION_ACTIVE_COLORS: Record<Opinion, string> = {
  BUY: "#2f9e44",
  HOLD: "#f08c00",
  SELL: "#c92a2a",
};

const HORIZONS: { key: keyof OpinionMatrix; label: string }[] = [
  { key: "short", label: "短期" },
  { key: "mid", label: "中期" },
  { key: "long", label: "长期" },
];

type OpinionMatrixCardProps = {
  matrix: OpinionMatrix;
};

export function OpinionMatrixCard({ matrix }: OpinionMatrixCardProps) {
  return (
    <View style={styles.container}>
      {/* 表头行 */}
      <View style={styles.row}>
        <View style={styles.labelCell} />
        {OPINIONS.map((op) => (
          <View key={op} style={styles.headerCell}>
            <Text style={styles.headerText}>{OPINION_LABELS[op]}</Text>
          </View>
        ))}
      </View>

      {/* 数据行：每个窗口期高亮当前看法 */}
      {HORIZONS.map(({ key, label }) => {
        const current = matrix[key];
        return (
          <View style={styles.row} key={key}>
            <View style={styles.labelCell}>
              <Text style={styles.labelText}>{label}</Text>
            </View>
            {OPINIONS.map((op) => {
              const active = current === op;
              return (
                <View
                  key={op}
                  style={[
                    styles.cell,
                    active && { backgroundColor: OPINION_ACTIVE_COLORS[op] },
                  ]}
                >
                  {active ? <Text style={styles.activeCheck}>✓</Text> : null}
                </View>
              );
            })}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#d8e7d2",
    overflow: "hidden",
    backgroundColor: "#f4f8ef",
  },
  row: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: "#d8e7d2",
  },
  labelCell: {
    width: 44,
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 10,
    backgroundColor: "#eef6ea",
    borderRightWidth: 1,
    borderRightColor: "#d8e7d2",
  },
  labelText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#2a4a37",
  },
  headerCell: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 6,
    backgroundColor: "#eef6ea",
    borderRightWidth: 1,
    borderRightColor: "#d8e7d2",
  },
  headerText: {
    fontSize: 10,
    color: "#335240",
    fontWeight: "600",
    textAlign: "center",
  },
  cell: {
    flex: 1,
    height: 38,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "transparent",
    borderRightWidth: 1,
    borderRightColor: "#d8e7d2",
  },
  activeCheck: {
    fontSize: 14,
    fontWeight: "800",
    color: "#ffffff",
  },
});
