/// <reference path="../react_native_shims.d.ts" />
import React from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { APP_VERSION } from "../constants";

type LoginPanelProps = {
  username: string;
  password: string;
  rememberPassword: boolean;
  stayLoggedIn: boolean;
  loading: boolean;
  error: string;
  onUsernameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onRememberPasswordChange: (value: boolean) => void;
  onStayLoggedInChange: (value: boolean) => void;
  onLogin: () => void;
  onRegister: () => void;
  onGuestTrial: () => void;
  /** 长按底部版本号打开开发者口令（由 App 处理） */
  onVersionLongPress: () => void;
};

function CheckRow({
  checked,
  label,
  onToggle,
  disabled,
}: {
  checked: boolean;
  label: string;
  onToggle: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      style={[styles.checkRow, disabled && styles.buttonDisabled]}
      onPress={onToggle}
      disabled={disabled}
      hitSlop={6}
    >
      <Text style={styles.checkMark}>{checked ? "☑" : "☐"}</Text>
      <Text style={styles.checkLabel}>{label}</Text>
    </Pressable>
  );
}

export function LoginPanel(props: LoginPanelProps) {
  return (
    <View style={styles.container}>
      <View style={styles.hero}>
        <Text style={styles.loginMark}>登录</Text>
        <Text style={styles.title}>使用账号密码登录，或先游客试用。</Text>
        <Text style={styles.subtitle}>
          微信一键登录需开放平台资质与协议，暂不接入；手机号验证码通常对接短信服务商并按条计费。
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>账号</Text>
        <TextInput
          value={props.username}
          onChangeText={props.onUsernameChange}
          placeholder="用户名"
          placeholderTextColor="#7a5b3f"
          autoCapitalize="none"
          autoCorrect={false}
          style={styles.input}
        />

        <Text style={[styles.label, styles.passwordLabel]}>密码</Text>
        <TextInput
          value={props.password}
          onChangeText={props.onPasswordChange}
          placeholder="密码（至少 4 位）"
          placeholderTextColor="#7a5b3f"
          autoCapitalize="none"
          autoCorrect={false}
          secureTextEntry
          style={styles.input}
        />

        <View style={styles.checkBlock}>
          <CheckRow
            checked={props.rememberPassword}
            label="记住密码（保存在本机，勿在共用设备开启）"
            onToggle={() => props.onRememberPasswordChange(!props.rememberPassword)}
            disabled={props.loading}
          />
          <CheckRow
            checked={props.stayLoggedIn}
            label="保持登录（服务端签发更长会话；关闭则冷启动需重新登录）"
            onToggle={() => props.onStayLoggedInChange(!props.stayLoggedIn)}
            disabled={props.loading}
          />
        </View>

        {props.error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{props.error}</Text>
          </View>
        ) : null}

        <View style={styles.buttonRow}>
          <Pressable style={styles.secondaryButton} onPress={props.onLogin} disabled={props.loading}>
            <Text style={styles.secondaryButtonText}>{props.loading ? "处理中…" : "登录"}</Text>
          </Pressable>
          <Pressable style={styles.primaryButton} onPress={props.onRegister} disabled={props.loading}>
            <Text style={styles.primaryButtonText}>{props.loading ? "处理中…" : "注册"}</Text>
          </Pressable>
        </View>

        <Pressable
          style={[styles.guestButton, props.loading && styles.buttonDisabled]}
          onPress={props.onGuestTrial}
          disabled={props.loading}
        >
          <Text style={styles.guestButtonText}>{props.loading ? "处理中…" : "游客试用"}</Text>
        </Pressable>

        <View style={styles.wechatSuspended}>
          <Text style={styles.wechatSuspendedTitle}>微信登录（筹备中）</Text>
          <Text style={styles.wechatSuspendedBody}>待开放平台应用与后端授权链路就绪后启用。</Text>
        </View>

        <Pressable onLongPress={props.onVersionLongPress} delayLongPress={450} hitSlop={12}>
          <Text style={styles.buildLabel}>客户端版本 {APP_VERSION}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 18,
    paddingTop: 18,
    paddingBottom: 24,
    backgroundColor: "#dfe9db",
    justifyContent: "space-between",
  },
  hero: {
    gap: 8,
    paddingHorizontal: 4,
  },
  loginMark: {
    fontSize: 22,
    color: "#c92a2a",
    fontWeight: "800",
    letterSpacing: 1,
  },
  title: {
    fontSize: 18,
    lineHeight: 26,
    color: "#2a4a37",
    fontWeight: "700",
  },
  subtitle: {
    fontSize: 12,
    lineHeight: 18,
    color: "#5b7160",
    fontWeight: "500",
  },
  card: {
    backgroundColor: "rgba(255,251,240,0.95)",
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "rgba(1,62,117,0.14)",
    padding: 18,
    shadowColor: "#013E75",
    shadowOpacity: 0.08,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 3,
    gap: 0,
  },
  label: {
    fontSize: 12,
    color: "#013E75",
    fontWeight: "700",
    marginBottom: 6,
  },
  passwordLabel: {
    marginTop: 12,
  },
  input: {
    height: 44,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#d6c8b0",
    backgroundColor: "#fffaf0",
    paddingHorizontal: 14,
    color: "#1f3a2a",
    fontSize: 14,
  },
  checkBlock: {
    marginTop: 14,
    gap: 10,
  },
  checkRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
  },
  checkMark: {
    fontSize: 16,
    color: "#2a4a37",
    lineHeight: 22,
  },
  checkLabel: {
    flex: 1,
    fontSize: 12,
    lineHeight: 18,
    color: "#2a4a37",
    fontWeight: "600",
  },
  errorBox: {
    marginTop: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: "#ffe3e3",
    borderWidth: 1,
    borderColor: "#ffa8a8",
  },
  errorText: {
    color: "#a61e4d",
    fontSize: 12,
    fontWeight: "600",
  },
  buttonRow: {
    marginTop: 14,
    flexDirection: "row",
    gap: 10,
  },
  primaryButton: {
    flex: 1,
    height: 46,
    borderRadius: 14,
    backgroundColor: "#2a4a37",
    alignItems: "center",
    justifyContent: "center",
  },
  primaryButtonText: {
    color: "#ffffff",
    fontWeight: "800",
    fontSize: 14,
  },
  secondaryButton: {
    flex: 1,
    height: 46,
    borderRadius: 14,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#d6c8b0",
  },
  secondaryButtonText: {
    color: "#6d4300",
    fontWeight: "800",
    fontSize: 14,
  },
  guestButton: {
    marginTop: 12,
    height: 44,
    borderRadius: 14,
    backgroundColor: "#eef6ea",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#c6d9c0",
  },
  guestButtonText: {
    color: "#2a4a37",
    fontWeight: "800",
    fontSize: 13,
  },
  wechatSuspended: {
    marginTop: 16,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: "rgba(1,62,117,0.1)",
    gap: 4,
  },
  wechatSuspendedTitle: {
    fontSize: 12,
    color: "#868e96",
    fontWeight: "700",
  },
  wechatSuspendedBody: {
    fontSize: 11,
    lineHeight: 16,
    color: "#868e96",
    fontWeight: "500",
  },
  buildLabel: {
    marginTop: 12,
    fontSize: 11,
    color: "#868e96",
    textAlign: "center",
    fontWeight: "600",
  },
  buttonDisabled: {
    opacity: 0.55,
  },
});
