import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "pocketpilot_access_token";

// SecureStore (iOS Keychain / Android Keystore) is not available on web.
// There the token is kept in memory only, never in localStorage, so the
// user signs in again after reloading the page.
const useSecureStore = Platform.OS !== "web";
let memoryToken: string | null = null;

export async function saveToken(token: string): Promise<void> {
  if (!useSecureStore) {
    memoryToken = token;
    return;
  }

  await SecureStore.setItemAsync(TOKEN_KEY, token, {
    // Excluded from device backups, so a copied token cannot be
    // restored onto another phone
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function getToken(): Promise<string | null> {
  if (!useSecureStore) {
    return memoryToken;
  }

  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function clearToken(): Promise<void> {
  memoryToken = null;

  if (useSecureStore) {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  }
}
