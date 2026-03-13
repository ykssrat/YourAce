import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

type WatchlistPanelProps = {
  items: string[];
  onPick: (code: string) => void;
};

export function WatchlistPanel(props: WatchlistPanelProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>自选列表</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {props.items.map((item) => (
          <Pressable key={item} style={styles.chip} onPress={() => props.onPick(item)}>
            <Text style={styles.chipText}>{item}</Text>
          </Pressable>
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
  row: {
    marginTop: 10,
    gap: 8,
    paddingRight: 8,
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
});
