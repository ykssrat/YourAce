/// <reference path="./src/react_native_shims.d.ts" />
import AsyncStorage from "@react-native-async-storage/async-storage";
import React, { useEffect, useState } from "react";
import { ActivityIndicator, ImageBackground, Pressable, SafeAreaView, StatusBar, StyleSheet, Text, TextInput, View } from "react-native";

import { DiagnoseTab } from "./src/components/DiagnoseTab";
import { ScreenTab } from "./src/components/ScreenTab";
import { checkServerHealth } from "./src/services/api";

const STORAGE_KEY_BASE_URL = "yourace_api_base_url";
const STORAGE_KEY_NEWS = "yourace_news_enabled";
// 默认使用电脑局域网 IP，手机同 WiFi 下可直连
const DEFAULT_BASE_URL = "43.138.223.57";
const STARTUP_MIN_DURATION_MS = 2000;
const STARTUP_COVER_IMAGE = require("./src/assets/startup-cover.png");

type ActiveTab = "screen" | "diagnose";

type KnowledgeCard = {
  title: string;
  summary: string;
};

const STARTUP_KNOWLEDGE_CARDS: KnowledgeCard[] = [
  { title: "马丁策略", summary: "只要让我赢一次！" },
  { title: "价值投资", summary: "低估买入，耐心持有。" },
  { title: "行为金融学", summary: "投资者总是非理性。" },
  { title: "正和博弈", summary: "只要公司经济持续向好，并不是你赚我赔，你死我活。" },
  { title: "利弗莫尔策略", summary: "市场永远是对的。" },
  { title: "马科维茨投资组合理论", summary: "不要把鸡蛋装在一个篮子里。" },
  { title: "沉没成本", summary: "不参与重大决策。" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("screen");
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_BASE_URL);
  const [newsEnabled, setNewsEnabled] = useState(true);
  const [settingsExpanded, setSettingsExpanded] = useState(false);
  const [diagnoseCode, setDiagnoseCode] = useState<string | undefined>(undefined);
  const [checkingHealth, setCheckingHealth] = useState(false);
  const [healthMessage, setHealthMessage] = useState("");
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [startupReady, setStartupReady] = useState(false);
  const [startupCard] = useState<KnowledgeCard>(() => pickStartupKnowledgeCard());
  const [startupStatus, setStartupStatus] = useState("正在加载本地设置...");

  // 启动时从持久化存储加载设置
  useEffect(() => {
    let mounted = true;

    async function bootstrapApp() {
      const minWait = waitFor(STARTUP_MIN_DURATION_MS);
      let nextBaseUrl = DEFAULT_BASE_URL;
      let nextNewsEnabled = true;

      try {
        const pairs = await AsyncStorage.multiGet([STORAGE_KEY_BASE_URL, STORAGE_KEY_NEWS]);
        const urlVal = pairs[0][1];
        const newsVal = pairs[1][1];

        if (urlVal !== null) {
          nextBaseUrl = urlVal;
        }
        if (newsVal !== null) {
          nextNewsEnabled = newsVal === "true";
        }

        if (mounted) {
          setApiBaseUrl(nextBaseUrl);
          setNewsEnabled(nextNewsEnabled);
          setStartupStatus("正在预热连接...");
        }
      } catch {
        if (mounted) {
          setStartupStatus("正在使用默认配置启动...");
        }
      }

      try {
        const health = await checkServerHealth(nextBaseUrl);
        if (!mounted) {
          return;
        }
        setHealthMessage(health.message);
        setHealthOk(health.ok);
        setStartupStatus(health.ok ? "连接预热完成，正在进入应用..." : "预热已完成，正在进入应用...");
      } catch {
        if (mounted) {
          setStartupStatus("预热已完成，正在进入应用...");
        }
      }

      await minWait;
      if (mounted) {
        setStartupReady(true);
      }
    }

    void bootstrapApp();

    return () => {
      mounted = false;
    };
  }, []);

  function handleSetApiBaseUrl(val: string) {
    setApiBaseUrl(val);
    setHealthMessage("");
    setHealthOk(null);
    AsyncStorage.setItem(STORAGE_KEY_BASE_URL, val).catch(() => {});
  }

  function handleSetNewsEnabled(val: boolean) {
    setNewsEnabled(val);
    AsyncStorage.setItem(STORAGE_KEY_NEWS, val ? "true" : "false").catch(() => {});
  }

  async function handleCheckHealth() {
    setCheckingHealth(true);
    setHealthMessage("");
    setHealthOk(null);
    const result = await checkServerHealth(apiBaseUrl);
    setHealthMessage(result.message);
    setHealthOk(result.ok);
    setCheckingHealth(false);
  }

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

  if (!startupReady) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <StatusBar barStyle="dark-content" backgroundColor="#fffbf0" />
        <ImageBackground source={STARTUP_COVER_IMAGE} resizeMode="cover" style={styles.startupBackground}>
          <View style={styles.startupOverlay}>
            <View style={styles.startupHero}>
              <Text style={styles.startupEyebrow}>YourAce 正在准备中</Text>
              <Text style={styles.startupTitle}>您的投资，更有章法。</Text>
              <Text style={styles.startupDate}>{formatTodayLabel()}</Text>
            </View>

            <View style={styles.startupBottom}>
              <View style={styles.startupCard}>
                <Text style={styles.startupCardLabel}>今日理财小知识</Text>
                <Text style={styles.startupCardTitle}>{startupCard.title}</Text>
                <Text style={styles.startupCardBody}>{startupCard.summary}</Text>
              </View>

              <View style={styles.startupFooter}>
                <ActivityIndicator color="#013E75" size="small" />
                <Text style={styles.startupStatus}>{startupStatus}</Text>
              </View>
            </View>
          </View>
        </ImageBackground>
      </SafeAreaView>
    );
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
              onChangeText={handleSetApiBaseUrl}
              placeholder="例如 192.168.1.100:8000"
              placeholderTextColor="#7c8b7a"
              autoCapitalize="none"
              autoCorrect={false}
              style={styles.settingsInput}
            />
            <Text style={styles.settingsHint}>真机：填电脑局域网 IP；模拟器：可留空或用 10.0.2.2:8000</Text>
            <View style={styles.healthRow}>
              <Pressable style={styles.healthBtn} onPress={handleCheckHealth} disabled={checkingHealth}>
                {checkingHealth ? (
                  <ActivityIndicator color="#ffffff" size="small" />
                ) : (
                  <Text style={styles.healthBtnText}>测试连接</Text>
                )}
              </Pressable>
              {healthMessage ? (
                <Text style={[styles.healthMsg, healthOk ? styles.healthMsgOk : styles.healthMsgFail]}>
                  {healthOk ? "成功" : "失败"}：{healthMessage}
                </Text>
              ) : null}
            </View>
            <View style={styles.settingsRow}>
              <Text style={styles.settingsLabel}>新闻系统</Text>
              <Pressable
                style={[styles.switchButton, newsEnabled ? styles.switchOn : styles.switchOff]}
                onPress={() => handleSetNewsEnabled(!newsEnabled)}
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

function pickStartupKnowledgeCard(): KnowledgeCard {
  const now = new Date();
  const dayIndex = Math.floor(now.getTime() / 86400000);
  return STARTUP_KNOWLEDGE_CARDS[dayIndex % STARTUP_KNOWLEDGE_CARDS.length];
}

function formatTodayLabel(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function waitFor(durationMs: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, durationMs);
  });
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
  healthRow: { marginTop: 2, gap: 6 },
  healthBtn: {
    height: 34,
    width: 90,
    borderRadius: 8,
    backgroundColor: "#2a4a37",
    justifyContent: "center",
    alignItems: "center",
  },
  healthBtnText: { color: "#ffffff", fontSize: 12, fontWeight: "700" },
  healthMsg: { fontSize: 11 },
  healthMsgOk: { color: "#2f9e44" },
  healthMsgFail: { color: "#c92a2a" },
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
  startupBackground: {
    flex: 1,
    backgroundColor: "#fffbf0",
  },
  startupOverlay: {
    flex: 1,
    paddingHorizontal: 22,
    paddingTop: 28,
    paddingBottom: 24,
    justifyContent: "space-between",
    backgroundColor: "rgba(255,251,240,0.16)",
  },
  startupHero: {
    gap: 6,
  },
  startupBottom: {
    marginTop: "auto",
    gap: 14,
    paddingTop: 24,
  },
  startupEyebrow: {
    fontSize: 12,
    color: "#013E75",
    fontWeight: "700",
    letterSpacing: 0.5,
  },
  startupTitle: {
    fontSize: 32,
    lineHeight: 38,
    color: "#a42423",
    fontWeight: "800",
  },
  startupDate: {
    fontSize: 13,
    color: "#013E75",
    fontWeight: "600",
  },
  startupCard: {
    backgroundColor: "rgba(255,251,240,0.92)",
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "rgba(1,62,117,0.12)",
    paddingHorizontal: 22,
    paddingVertical: 26,
    shadowColor: "#013E75",
    shadowOpacity: 0.1,
    shadowRadius: 22,
    shadowOffset: { width: 0, height: 12 },
    elevation: 4,
  },
  startupCardLabel: {
    fontSize: 11,
    lineHeight: 16,
    color: "#013E75",
    fontWeight: "700",
    letterSpacing: 0.3,
    marginBottom: 8,
  },
  startupCardTitle: {
    fontSize: 28,
    lineHeight: 32,
    color: "#013E75",
    fontWeight: "800",
    marginBottom: 12,
  },
  startupCardBody: {
    fontSize: 21,
    lineHeight: 30,
    color: "#2b2b2b",
    fontWeight: "600",
  },
  startupCardHint: {
    marginTop: 18,
    fontSize: 12,
    lineHeight: 18,
    color: "#516579",
  },
  startupFooter: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "rgba(255,251,240,0.92)",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "rgba(1,62,117,0.12)",
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  startupStatus: {
    flex: 1,
    fontSize: 13,
    color: "#013E75",
    fontWeight: "600",
  },
});
