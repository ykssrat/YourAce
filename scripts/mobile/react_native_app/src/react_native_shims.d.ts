declare module "react" {
  const React: any;
  export default React;
  export function useState<T>(initial: T): [T, (value: T) => void];
  export function useMemo<T>(factory: () => T, deps: unknown[]): T;
  export function useRef<T>(initial: T): { current: T };
  export function useEffect(effect: () => void | (() => void), deps?: unknown[]): void;
}

declare module "react/jsx-runtime" {
  export const Fragment: any;
  export const jsx: any;
  export const jsxs: any;
}

declare module "react-native" {
  export const SafeAreaView: any;
  export const ScrollView: any;
  export const StatusBar: any;
  export const StyleSheet: any;
  export const Text: any;
  export const TextInput: any;
  export const View: any;
  export const Pressable: any;
}
