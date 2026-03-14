/// <reference path="../react_native_shims.d.ts" />
import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

type WatchlistPanelProps = {
  items: string[];
  draftCode: string;
  onAdd: (code: string) => void;
  onRemove: (code: string) => void;
  onPick: (code: string) => void;
};

export function WatchlistPanel(props: WatchlistPanelProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>自选列表</Text>
      <View style={styles.actions}>
        <Text style={styles.hint}>当前代码: {props.draftCode || "(空)"}</Text>
        <Pressable style={styles.addBtn} onPress={() => props.onAdd(props.draftCode)}>
          <Text style={styles.addBtnText}>添加</Text>
        </Pressable>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {props.items.map((item) => (
          <View key={item} style={styles.chipWrap}>
            <Pressable style={styles.chip} onPress={() => props.onPick(item)}>
              <Text style={styles.chipText}>{item}</Text>
            </Pressable>
            <Pressable style={styles.delBtn} onPress={() => props.onRemove(item)}>
              <Text style={styles.delBtnText}>x</Text>
            </Pressable>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 14,
    backgroundColor: "#edf3e4",
    borderRadius: 16,
    padding: 14,
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    color: "#264a38",
  },
  actions: {
    marginTop: 10,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  hint: {
    color: "#4a5d4c",
    fontSize: 12,
  },
  addBtn: {
    backgroundColor: "#2f6b3f",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
  },
  addBtnText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 12,
  },
  row: {
    marginTop: 10,
    gap: 8,
    paddingRight: 8,
  },
  chipWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  chip: {
    backgroundColor: "#ffffff",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: "#c8dbc7",
  },
  chipText: {
    fontWeight: "600",
    color: "#29503e",
  },
  delBtn: {
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#ffe3e3",
    borderWidth: 1,
    borderColor: "#ffc9c9",
  },
  delBtnText: {
    color: "#a61e4d",
    fontWeight: "700",
    lineHeight: 16,
  },
});
