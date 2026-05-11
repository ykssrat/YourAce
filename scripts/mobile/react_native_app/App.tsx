/// <reference path="./src/react_native_shims.d.ts" />
import AsyncStorage from "@react-native-async-storage/async-storage";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  AppState,
  AppStateStatus,
  Modal,
  Pressable,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { DEVELOPER_UNLOCK_SECRET, SESSION_REFRESH_INTERVAL_DAYS } from "./src/constants";
import { LoginPanel } from "./src/components/LoginPanel";
import { DiagnoseTab } from "./src/components/DiagnoseTab";
import { RealtimeWatchlistTab } from "./src/components/RealtimeWatchlistTab";
import { ScreenTab } from "./src/components/ScreenTab";
import { checkServerHealth, loginUser, refreshAuthSession, registerUser } from "./src/services/api";
import { AuthResponse } from "./src/types";

const STORAGE_KEY_BASE_URL = "yourace_api_base_url";
const STORAGE_KEY_NEWS = "yourace_news_enabled";
const STORAGE_KEY_AUTH = "yourace_auth_user";
/** 仅当上次登录勾选「保持登录」为 true 时，冷启动恢复 STORAGE_KEY_AUTH */
const STORAGE_KEY_SESSION_PERSISTED = "yourace_session_persisted";
const STORAGE_KEY_REMEMBER_PASSWORD = "yourace_remember_password";
const STORAGE_KEY_STAY_LOGGED_IN_PREF = "yourace_stay_logged_in_pref";
const STORAGE_KEY_SAVED_USERNAME = "yourace_saved_username";
const STORAGE_KEY_SAVED_PASSWORD = "yourace_saved_password";
const STORAGE_KEY_DEVELOPER_MODE = "yourace_developer_mode";
const STORAGE_KEY_SESSION_LAST_REFRESH = "yourace_session_last_refresh";

const SESSION_REFRESH_INTERVAL_MS = SESSION_REFRESH_INTERVAL_DAYS * 24 * 60 * 60 * 1000;
// 默认使用电脑局域网 IP，手机同 WiFi 下可直连
const DEFAULT_BASE_URL = "43.138.223.57";
const STARTUP_MIN_DURATION_MS = 2000;

type ActiveTab = "screen" | "watchlist" | "diagnose";

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
  const [startupCard] = useState<KnowledgeCard>(pickStartupKnowledgeCard());
  const [startupStatus, setStartupStatus] = useState("正在加载本地设置...");
  const [authUser, setAuthUser] = useState<AuthResponse | null>(null);
  const [authUsername, setAuthUsername] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [rememberPassword, setRememberPassword] = useState(false);
  const [stayLoggedIn, setStayLoggedIn] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [developerMode, setDeveloperMode] = useState(false);
  const [devUnlockVisible, setDevUnlockVisible] = useState(false);
  const [devUnlockInput, setDevUnlockInput] = useState("");

  // 启动时从持久化存储加载设置
  useEffect(() => {
    let mounted = true;

    async function bootstrapApp() {
      const minWait = waitFor(STARTUP_MIN_DURATION_MS);
      let nextBaseUrl = DEFAULT_BASE_URL;
      let nextNewsEnabled = true;
      let nextAuthUser: AuthResponse | null = null;

      try {
        const pairs = await AsyncStorage.multiGet([
          STORAGE_KEY_BASE_URL,
          STORAGE_KEY_NEWS,
          STORAGE_KEY_AUTH,
          STORAGE_KEY_SESSION_PERSISTED,
          STORAGE_KEY_REMEMBER_PASSWORD,
          STORAGE_KEY_STAY_LOGGED_IN_PREF,
          STORAGE_KEY_SAVED_USERNAME,
          STORAGE_KEY_SAVED_PASSWORD,
          STORAGE_KEY_DEVELOPER_MODE,
          STORAGE_KEY_SESSION_LAST_REFRESH,
        ]);
        const urlVal = pairs[0][1];
        const newsVal = pairs[1][1];
        const authVal = pairs[2][1];
        const sessionPersisted = pairs[3][1] === "true";
        const rememberVal = pairs[4][1] === "true";
        const stayPrefVal = pairs[5][1] !== "false";
        const savedUser = pairs[6][1] ?? "";
        const savedPass = pairs[7][1] ?? "";
        const devModeVal = pairs[8][1] === "true";
        const lastRefreshStr = pairs[9][1];

        if (urlVal !== null) {
          nextBaseUrl = urlVal;
        }
        if (newsVal !== null) {
          nextNewsEnabled = newsVal === "true";
        }
        if (authVal && !sessionPersisted) {
          await AsyncStorage.removeItem(STORAGE_KEY_AUTH).catch(() => {});
        }
        if (authVal && sessionPersisted) {
          try {
            nextAuthUser = JSON.parse(authVal) as AuthResponse;
          } catch {
            nextAuthUser = null;
          }
        }

        if (nextAuthUser && sessionPersisted) {
          const needRefresh =
            !lastRefreshStr ||
            Date.now() - new Date(lastRefreshStr).getTime() >= SESSION_REFRESH_INTERVAL_MS;
          if (needRefresh) {
            try {
              const refreshed = await refreshAuthSession(nextAuthUser.user_id, nextAuthUser.token, nextBaseUrl);
              nextAuthUser = refreshed;
              await AsyncStorage.setItem(STORAGE_KEY_AUTH, JSON.stringify(refreshed));
              await AsyncStorage.setItem(STORAGE_KEY_SESSION_LAST_REFRESH, new Date().toISOString());
            } catch {
              nextAuthUser = null;
              await AsyncStorage.removeItem(STORAGE_KEY_AUTH).catch(() => {});
            }
          }
        }

        if (mounted) {
          setApiBaseUrl(nextBaseUrl);
          setNewsEnabled(nextNewsEnabled);
          setAuthUser(nextAuthUser);
          setDeveloperMode(devModeVal);
          setRememberPassword(rememberVal);
          setStayLoggedIn(stayPrefVal);
          if (rememberVal) {
            setAuthUsername(savedUser);
            setAuthPassword(savedPass);
          }
          if (nextAuthUser) {
            setActiveTab("watchlist");
            setStartupStatus("正在恢复登录状态...");
          } else {
            setStartupStatus("正在预热连接...");
          }
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

  async function persistLoginSideEffects(
    payload: AuthResponse,
    creds: { username: string; password: string },
    options: { skipSaveCredentials: boolean },
  ) {
    const remember = rememberPassword;
    const stay = stayLoggedIn;
    await AsyncStorage.setItem(STORAGE_KEY_SESSION_PERSISTED, stay ? "true" : "false");
    await AsyncStorage.setItem(STORAGE_KEY_REMEMBER_PASSWORD, remember ? "true" : "false");
    await AsyncStorage.setItem(STORAGE_KEY_STAY_LOGGED_IN_PREF, stay ? "true" : "false");
    if (stay) {
      await AsyncStorage.setItem(STORAGE_KEY_AUTH, JSON.stringify(payload));
      await AsyncStorage.setItem(STORAGE_KEY_SESSION_LAST_REFRESH, new Date().toISOString());
    } else {
      await AsyncStorage.removeItem(STORAGE_KEY_AUTH);
      await AsyncStorage.removeItem(STORAGE_KEY_SESSION_LAST_REFRESH);
    }
    if (remember && !options.skipSaveCredentials) {
      await AsyncStorage.multiSet([
        [STORAGE_KEY_SAVED_USERNAME, creds.username],
        [STORAGE_KEY_SAVED_PASSWORD, creds.password],
      ]);
    } else {
      await AsyncStorage.multiRemove([STORAGE_KEY_SAVED_USERNAME, STORAGE_KEY_SAVED_PASSWORD]);
    }
  }

  async function handleGuestTrial() {
    setAuthLoading(true);
    setAuthError("");

    try {
      const creds = createGuestCredentials();
      const payload = await registerUser(
        { username: creds.username, password: creds.password, persist_session: stayLoggedIn },
        apiBaseUrl,
      );
      await persistLoginSideEffects(payload, creds, { skipSaveCredentials: true });
      setAuthUser(payload);
      setActiveTab("watchlist");
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "游客试用失败，请检查后端地址与网络");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleAuthSubmit(mode: "login" | "register") {
    const username = authUsername.trim();
    const password = authPassword.trim();

    if (!username) {
      setAuthError("请输入账号");
      return;
    }
    if (!password) {
      setAuthError("请输入密码");
      return;
    }

    setAuthLoading(true);
    setAuthError("");

    try {
      const payload =
        mode === "login"
          ? await loginUser({ username, password, persist_session: stayLoggedIn }, apiBaseUrl)
          : await registerUser({ username, password, persist_session: stayLoggedIn }, apiBaseUrl);

      await persistLoginSideEffects(payload, { username, password }, { skipSaveCredentials: false });
      setAuthUser(payload);
      if (!rememberPassword) {
        setAuthUsername("");
        setAuthPassword("");
      }
      setActiveTab("watchlist");
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleLogout() {
    setAuthUser(null);
    setActiveTab("screen");
    setDiagnoseCode(undefined);
    setAuthError("");
    await AsyncStorage.removeItem(STORAGE_KEY_AUTH).catch(() => {});
    await AsyncStorage.setItem(STORAGE_KEY_SESSION_PERSISTED, "false").catch(() => {});
    await AsyncStorage.removeItem(STORAGE_KEY_SESSION_LAST_REFRESH).catch(() => {});
  }

  function trySubmitDevUnlock() {
    if (devUnlockInput.trim() === DEVELOPER_UNLOCK_SECRET) {
      setDeveloperMode(true);
      void AsyncStorage.setItem(STORAGE_KEY_DEVELOPER_MODE, "true");
      setDevUnlockVisible(false);
      setDevUnlockInput("");
    } else {
      Alert.alert("口令错误", "请向维护者确认开发者口令，或修改源码中的 DEVELOPER_UNLOCK_SECRET。");
    }
  }

  async function handleDisableDeveloperMode() {
    setDeveloperMode(false);
    setSettingsExpanded(false);
    await AsyncStorage.setItem(STORAGE_KEY_DEVELOPER_MODE, "false");
  }

  // 已登录且保持登录：回到前台时按间隔续期（与冷启动一致）
  useEffect(() => {
    const onAppState = (state: AppStateStatus) => {
      if (state !== "active" || !authUser) {
        return;
      }
      void (async () => {
        const sp = await AsyncStorage.getItem(STORAGE_KEY_SESSION_PERSISTED);
        if (sp !== "true") {
          return;
        }
        const last = await AsyncStorage.getItem(STORAGE_KEY_SESSION_LAST_REFRESH);
        if (last && Date.now() - new Date(last).getTime() < SESSION_REFRESH_INTERVAL_MS) {
          return;
        }
        try {
          const refreshed = await refreshAuthSession(authUser.user_id, authUser.token, apiBaseUrl);
          setAuthUser(refreshed);
          await AsyncStorage.setItem(STORAGE_KEY_AUTH, JSON.stringify(refreshed));
          await AsyncStorage.setItem(STORAGE_KEY_SESSION_LAST_REFRESH, new Date().toISOString());
        } catch {
          setAuthUser(null);
          setActiveTab("screen");
          setDiagnoseCode(undefined);
          await AsyncStorage.removeItem(STORAGE_KEY_AUTH).catch(() => {});
          await AsyncStorage.setItem(STORAGE_KEY_SESSION_PERSISTED, "false").catch(() => {});
          await AsyncStorage.removeItem(STORAGE_KEY_SESSION_LAST_REFRESH).catch(() => {});
        }
      })();
    };
    const sub = AppState.addEventListener("change", onAppState);
    return () => sub.remove();
  }, [authUser, apiBaseUrl]);

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
        <View style={styles.startupBackground}>
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
        </View>
      </SafeAreaView>
    );
  }

  if (!authUser) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <StatusBar barStyle="dark-content" backgroundColor="#dfe9db" />

        {developerMode ? (
          <View style={styles.settingsBar}>
            <Pressable style={styles.settingsToggle} onPress={() => setSettingsExpanded(!settingsExpanded)}>
              <Text style={styles.settingsToggleText}>
                {settingsExpanded ? "▲ 收起设置" : "▼ 开发者 · 连接与功能"}
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
                <Pressable style={styles.devOffBtn} onPress={() => void handleDisableDeveloperMode()}>
                  <Text style={styles.devOffBtnText}>关闭开发者模式</Text>
                </Pressable>
              </View>
            ) : null}
          </View>
        ) : null}

        <View style={styles.content}>
          <LoginPanel
            username={authUsername}
            password={authPassword}
            rememberPassword={rememberPassword}
            stayLoggedIn={stayLoggedIn}
            loading={authLoading}
            error={authError}
            onUsernameChange={setAuthUsername}
            onPasswordChange={setAuthPassword}
            onRememberPasswordChange={setRememberPassword}
            onStayLoggedInChange={setStayLoggedIn}
            onLogin={() => void handleAuthSubmit("login")}
            onRegister={() => void handleAuthSubmit("register")}
            onGuestTrial={() => void handleGuestTrial()}
            onVersionLongPress={() => setDevUnlockVisible(true)}
          />
        </View>

        <Modal transparent animationType="fade" visible={devUnlockVisible} onRequestClose={() => setDevUnlockVisible(false)}>
          <View style={styles.modalBackdrop}>
            <View style={styles.modalCard}>
              <Text style={styles.modalTitle}>开发者模式</Text>
              <Text style={styles.modalHint}>请输入口令后解锁服务器地址与连接测试（口令仅保存在源码常量中，请勿外传）。</Text>
              <TextInput
                value={devUnlockInput}
                onChangeText={setDevUnlockInput}
                placeholder="口令"
                placeholderTextColor="#868e96"
                secureTextEntry
                autoCapitalize="none"
                style={styles.modalInput}
              />
              <View style={styles.modalActions}>
                <Pressable style={styles.modalCancel} onPress={() => setDevUnlockVisible(false)}>
                  <Text style={styles.modalCancelText}>取消</Text>
                </Pressable>
                <Pressable style={styles.modalOk} onPress={trySubmitDevUnlock}>
                  <Text style={styles.modalOkText}>确定</Text>
                </Pressable>
              </View>
            </View>
          </View>
        </Modal>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor="#dfe9db" />

      {developerMode ? (
        <View style={styles.settingsBar}>
          <Pressable style={styles.settingsToggle} onPress={() => setSettingsExpanded(!settingsExpanded)}>
            <Text style={styles.settingsToggleText}>
              {settingsExpanded ? "▲ 收起设置" : "▼ 开发者 · 连接与功能"}
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
              <View style={styles.authRow}>
                <Text style={styles.settingsLabel}>当前账号</Text>
                <Text style={styles.accountText}>{formatAccountLabel(authUser)}</Text>
                <Pressable style={styles.logoutBtn} onPress={() => void handleLogout()}>
                  <Text style={styles.logoutBtnText}>退出登录</Text>
                </Pressable>
              </View>
              <Pressable style={styles.devOffBtn} onPress={() => void handleDisableDeveloperMode()}>
                <Text style={styles.devOffBtnText}>关闭开发者模式</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      ) : (
        <View style={styles.userBar}>
          <Text style={styles.userBarText}>
            已登录 · {formatAccountLabel(authUser)}
          </Text>
          <Pressable style={styles.userBarLogout} onPress={() => void handleLogout()}>
            <Text style={styles.userBarLogoutText}>退出</Text>
          </Pressable>
        </View>
      )}

      <View style={styles.content}>
        {activeTab === "screen" ? (
          <ScreenTab apiBaseUrl={apiBaseUrl} onGoToDiagnose={handleGoToDiagnose} />
        ) : activeTab === "watchlist" ? (
          <RealtimeWatchlistTab
            apiBaseUrl={apiBaseUrl}
            auth={authUser}
            onGoToDiagnose={handleGoToDiagnose}
            onAuthExpired={() => void handleLogout()}
          />
        ) : (
          <DiagnoseTab
            apiBaseUrl={apiBaseUrl}
            newsEnabled={newsEnabled}
            initialCode={diagnoseCode}
          />
        )}
      </View>

      <View style={styles.tabBar}>
        <TabBarItem
          label="选股"
          icon="🔍"
          active={activeTab === "screen"}
          onPress={() => handleTabChange("screen")}
          onLongPress={!developerMode ? () => setDevUnlockVisible(true) : undefined}
        />
        <TabBarItem label="看盘" icon="📈" active={activeTab === "watchlist"} onPress={() => handleTabChange("watchlist")} />
        <TabBarItem label="诊股" icon="📊" active={activeTab === "diagnose"} onPress={() => handleTabChange("diagnose")} />
      </View>

      <Modal transparent animationType="fade" visible={devUnlockVisible} onRequestClose={() => setDevUnlockVisible(false)}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>开发者模式</Text>
            <Text style={styles.modalHint}>请输入口令。也可在登录页长按「客户端版本」打开本窗口。</Text>
            <TextInput
              value={devUnlockInput}
              onChangeText={setDevUnlockInput}
              placeholder="口令"
              placeholderTextColor="#868e96"
              secureTextEntry
              autoCapitalize="none"
              style={styles.modalInput}
            />
            <View style={styles.modalActions}>
              <Pressable style={styles.modalCancel} onPress={() => setDevUnlockVisible(false)}>
                <Text style={styles.modalCancelText}>取消</Text>
              </Pressable>
              <Pressable style={styles.modalOk} onPress={trySubmitDevUnlock}>
                <Text style={styles.modalOkText}>确定</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function createGuestCredentials(): { username: string; password: string } {
  const suffix = `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 11)}`;
  return {
    username: `guest_${suffix}`,
    password: `guest_pw_${suffix}_${Math.random().toString(36).slice(2, 14)}`,
  };
}

function formatAccountLabel(auth: AuthResponse): string {
  if (auth.username.startsWith("guest_")) {
    return "游客";
  }
  return auth.username;
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

function TabBarItem({
  label,
  icon,
  active,
  onPress,
  onLongPress,
}: {
  label: string;
  icon: string;
  active: boolean;
  onPress: () => void;
  onLongPress?: () => void;
}) {
  return (
    <Pressable
      style={[styles.tabItem, active && styles.tabItemActive]}
      onPress={onPress}
      onLongPress={onLongPress}
      delayLongPress={500}
    >
      <Text style={styles.tabIcon}>{icon}</Text>
      <Text style={[styles.tabLabel, active && styles.tabLabelActive]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#dfe9db" },
  userBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#eef6ea",
    borderBottomWidth: 1,
    borderBottomColor: "#d8e7d2",
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  userBarText: { fontSize: 13, color: "#2a4a37", fontWeight: "700" },
  userBarLogout: {
    borderRadius: 999,
    paddingVertical: 6,
    paddingHorizontal: 14,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#d6c8b0",
  },
  userBarLogoutText: { fontSize: 12, color: "#6d4300", fontWeight: "800" },
  devOffBtn: {
    marginTop: 6,
    alignSelf: "flex-start",
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#adb5bd",
    backgroundColor: "#f8f9fa",
  },
  devOffBtnText: { fontSize: 11, color: "#495057", fontWeight: "700" },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "center",
    paddingHorizontal: 28,
  },
  modalCard: {
    backgroundColor: "#fffbf0",
    borderRadius: 18,
    padding: 20,
    borderWidth: 1,
    borderColor: "rgba(1,62,117,0.16)",
  },
  modalTitle: { fontSize: 17, fontWeight: "800", color: "#013E75", marginBottom: 8 },
  modalHint: { fontSize: 12, color: "#495057", lineHeight: 18, marginBottom: 14 },
  modalInput: {
    height: 44,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#ced4da",
    paddingHorizontal: 12,
    marginBottom: 16,
    fontSize: 15,
    color: "#1f3a2a",
  },
  modalActions: { flexDirection: "row", justifyContent: "flex-end", gap: 12 },
  modalCancel: { paddingVertical: 10, paddingHorizontal: 14 },
  modalCancelText: { fontSize: 14, color: "#495057", fontWeight: "700" },
  modalOk: {
    paddingVertical: 10,
    paddingHorizontal: 18,
    borderRadius: 12,
    backgroundColor: "#2a4a37",
  },
  modalOkText: { fontSize: 14, color: "#fff", fontWeight: "800" },
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
  authRow: { marginTop: 2, gap: 8 },
  accountText: { fontSize: 12, color: "#2a4a37", fontWeight: "700" },
  logoutBtn: {
    alignSelf: "flex-start",
    borderRadius: 999,
    paddingVertical: 4,
    paddingHorizontal: 10,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#d6c8b0",
  },
  logoutBtnText: { color: "#6d4300", fontSize: 12, fontWeight: "700" },
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
