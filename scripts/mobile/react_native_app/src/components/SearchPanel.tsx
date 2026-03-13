/// <reference path="../react_native_shims.d.ts" />
import React from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

type SearchPanelProps = {
  query: string;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
};

export function SearchPanel(props: SearchPanelProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>YourAce Radar</Text>
      <Text style={styles.subtitle}>输入代码或名称，触发本地分析引擎</Text>
      <View style={styles.row}>
        <TextInput
          value={props.query}
          onChangeText={props.onQueryChange}
          placeholder="例如 000001 或 平安银行"
          placeholderTextColor="#7c8b7a"
          style={styles.input}
        />
        <Pressable style={styles.button} onPress={props.onSubmit} disabled={props.loading}>
          <Text style={styles.buttonText}>{props.loading ? "分析中" : "分析"}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#f7f1df",
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: "#d7ccb5",
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1e3426",
    fontFamily: "Georgia",
  },
  subtitle: {
    marginTop: 6,
    color: "#4f5a49",
    fontSize: 13,
  },
  row: {
    marginTop: 12,
    flexDirection: "row",
    gap: 8,
  },
  input: {
    flex: 1,
    height: 44,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#c7bca6",
    paddingHorizontal: 12,
    color: "#25352a",
    backgroundColor: "#fffaf0",
  },
  button: {
    width: 86,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: "#2f6b3f",
  },
  buttonText: {
    color: "#f6fff6",
    fontWeight: "700",
  },
});
