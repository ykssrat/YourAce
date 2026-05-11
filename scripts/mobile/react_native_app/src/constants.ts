/** 与 android/app/build.gradle 中 versionName 保持一致 */
export const APP_VERSION = "0.1.7";

/** 长按版本号后输入此口令可开启「开发者模式」（仅本机存储开关）。请自行改成私密字符串并勿提交到公开仓库。 */
export const DEVELOPER_UNLOCK_SECRET = "yourace-dev-unlock";

/** 勾选「保持登录」时：服务端 token 有效期天数；客户端至多按此间隔调用 /auth/refresh 续期 */
export const SESSION_REFRESH_INTERVAL_DAYS = 7;
