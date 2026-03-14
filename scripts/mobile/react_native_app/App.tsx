/// <reference path="./src/react_native_shims.d.ts" />
import React, { useState } from "react";
import { Pressable, SafeAreaView, StatusBar, StyleSheet, Text, TextInput, View } from "react-native";

import { DiagnoseTab } from "./src/components/DiagnoseTab";
import { ScreenTab } from "./src/components/ScreenTab";

type ActiveTab = "screen" | "diagnose";

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("screen");
  const [apiBaseUrl, setApiBaseUrl] = useState("192.168.1.100:8000");
  const [newsEnabled, setNewsEnabled] = useState(true);
  const [settingsExpanded, setSettingsExpanded] = useState(false);
  const [diagnoseCode, setDiagnoseCode] = useState<string | undefined>(undefined);

  function handleGoToDiagnose(code: string) {
    setDiagnoseCode(code);
    setActiveTab("diagnose");
  }

  function handleTabChange(tab: ActiveTab) {
    if (tab !== "diagnose") {
      setDiagnoseCode(undefined);
    }
    setActiveTab(tab);
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor="#dfe9db" />

      <View style={styles.settingsBar}>
        <Pressable style={styles.settingsToggle} onPress={() => setSettingsExpanded(!settingsExpanded)}>
          <Text style={styles.settingsToggleText}>
            {settingsExpanded ? "▲ 收起设置" : "▼ 服务器设置"}
          </Text>
          <View style={styles.settingsStatusDot} />
        </Pressable>

        {settingsExpanded ? (
          <View style={styles.settingsPanel}>
            <Text style={styles.settingsLabel}>后端地址</Text>
            <TextInput
              value={apiBaseUrl}
              onChangeText={setApiBaseUrl}
              placeholder="例如 192.168.1.100:8000"
              placeholderTextColor="#7c8b7a"
              autoCapitalize="none"
              autoCorrect={false}
              style={styles.settingsInput}
            />
            <Text style={styles.settingsHint}>真机：填电脑局域网 IP；模拟器：可留空或用 10.0.2.2:8000</Text>
            <View style={styles.settingsRow}>
              <Text style={styles.settingsLabel}>新闻系统</Text>
              <Pressable
                style={[styles.switchButton, newsEnabled ? styles.switchOn : styles.switchOff]}
                onPress={() => setNewsEnabled(!newsEnabled)}
              >
                <Text style={styles.switchText}>{newsEnabled ? "已开启" : "已关闭"}</Text>
              </Pressable>
            </View>
          </View>
        ) : null}
      </View>

      <View style={styles.content}>
        {activeTab === "screen" ? (
          <ScreenTab apiBaseUrl={apiBaseUrl} onGoToDiagnose={handleGoToDiagnose} />
        ) : (
          <DiagnoseTab
            apiBaseUrl={apiBaseUrl}
            newsEnabled={newsEnabled}
            initialCode={diagnoseCode}
          />
        )}
      </View>

      <View style={styles.tabBar}>
        <TabBarItem label="选股" icon="🔍" active={activeTab === "screen"} onPress={() => handleTabChange("screen")} />
        <TabBarItem label="诊股" icon="📊" active={activeTab === "diagnose"} onPress={() => handleTabChange("diagnose")} />
      </View>
    </SafeAreaView>
  );
}

function TabBarItem({ label, icon, active, onPress }: { label: string; icon: string; active: boolean; onPress: () => void }) {
  return (
    <Pressable style={[styles.tabItem, active && styles.tabItemActive]} onPress={onPress}>
      <Text style={styles.tabIcon}>{icon}</Text>
      <Text style={[styles.tabLabel, active && styles.tabLabelActive]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#dfe9db" },
  settingsBar: { backgroundColor: "#eef6ea", borderBottomWidth: 1, borderBottomColor: "#d8e7d2", paddingHorizontal: 16, paddingVertical: 6 },
  settingsToggle: { flexDirection: "row", alignItems: "center", gap: 8 },
  settingsToggleText: { fontSize: 12, color: "#2a4a37", fontWeight: "600" },
  settingsStatusDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#2f9e44" },
  settingsPanel: { marginTop: 8, gap: 6 },
  settingsLabel: { fontSize: 12, fontWeight: "700", color: "#2a4a37" },
  settingsInput: { height: 38, borderRadius: 10, borderWidth: 1, borderColor: "#c6d9c0", backgroundColor: "#ffffff", color: "#1f3a2a", paddingHorizontal: 10, fontSize: 13 },
  settingsHint: { fontSize: 11, color: "#5b7160" },
  settingsRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  switchButton: { borderRadius: 999, paddingVertical: 4, paddingHorizontal: 10 },
  switchOn: { backgroundColor: "#2f9e44" },
  switchOff: { backgroundColor: "#868e96" },
  switchText: { color: "#ffffff", fontSize: 12, fontWeight: "700" },
  content: { flex: 1, backgroundColor: "#dfe9db" },
  tabBar: { flexDirection: "row", backgroundColor: "#f4f8ef", borderTopWidth: 1, borderTopColor: "#d8e7d2", paddingBottom: 4 },
  tabItem: { flex: 1, alignItems: "center", paddingVertical: 10, gap: 2 },
  tabItemActive: { borderTopWidth: 2, borderTopColor: "#2a4a37" },
  tabIcon: { fontSize: 20 },
  tabLabel: { fontSize: 12, color: "#7c8b7a", fontWeight: "600" },
  tabLabelActive: { color: "#2a4a37", fontWeight: "700" },
});