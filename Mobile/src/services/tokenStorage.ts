import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "pocketpilot_access_token"; // Legacy access-only storage
const SESSION_KEY = "pocketpilot_session_v2";
const useSecureStore = Platform.OS !== "web";
export type TokenPair = { access_token: string; refresh_token: string };
let memorySession: TokenPair | null = null;
let generation = 0;
let writes: Promise<void> = Promise.resolve();
export const sessionGeneration = () => generation;

function serialize<T>(operation: () => Promise<T>): Promise<T> {
  const result = writes.then(operation);
  writes = result.then(() => undefined, () => undefined);
  return result;
}

export async function getSession(): Promise<TokenPair | null> {
  await writes;
  if (!useSecureStore) return memorySession;
  const saved = await SecureStore.getItemAsync(SESSION_KEY);
  if (saved) {
    const pair = JSON.parse(saved) as TokenPair;
    if (typeof pair.access_token === "string" && typeof pair.refresh_token === "string") return pair;
    throw new Error("Invalid saved session");
  }
  const legacy = await SecureStore.getItemAsync(TOKEN_KEY);
  return legacy ? { access_token: legacy, refresh_token: "" } : null;
}

export async function getToken(): Promise<string | null> {
  return (await getSession())?.access_token ?? null;
}

// Store the pair in ONE SecureStore value so rotation cannot leave a mixed pair.
// expectedGeneration prevents a late refresh from undoing logout/new login.
export function saveSession(pair: TokenPair, expectedGeneration?: number): Promise<boolean> {
  if (expectedGeneration === undefined) generation += 1;
  const expected = expectedGeneration ?? generation;
  return serialize(async () => {
    if (expected !== generation) return false;
    if (useSecureStore) {
      await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(pair), {
        keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
      });
      await SecureStore.deleteItemAsync(TOKEN_KEY);
    } else {
      // Web stays memory-only; never persist a long-lived token in localStorage.
      memorySession = pair;
    }
    return expected === generation;
  });
}

export function clearToken(): Promise<void> {
  generation += 1;
  return serialize(async () => {
    memorySession = null;
    if (useSecureStore) {
      await SecureStore.deleteItemAsync(SESSION_KEY);
      await SecureStore.deleteItemAsync(TOKEN_KEY);
    }
  });
}
