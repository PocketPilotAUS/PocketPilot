
import AsyncStorage from "@react-native-async-storage/async-storage";

const ACCOUNTS_KEY = "@pocketpilot_demo_accounts";
const SESSION_KEY = "@pocketpilot_demo_session";

export type DemoUser = {
  id: string;
  name: string;
  email: string;
};

type StoredAccount = DemoUser & {
  password: string;
};

type AuthResult = {
  success: boolean;
  message: string;
  user?: DemoUser;
};

async function getAccounts(): Promise<StoredAccount[]> {
  const stored = await AsyncStorage.getItem(ACCOUNTS_KEY);
  return stored ? JSON.parse(stored) : [];
}

function publicUser(account: StoredAccount): DemoUser {
  return {
    id: account.id,
    name: account.name,
    email: account.email,
  };
}

export async function register(
  name: string,
  email: string,
  password: string
): Promise<AuthResult> {
  const cleanName = name.trim();
  const cleanEmail = email.trim().toLowerCase();

  if (!cleanName || !cleanEmail || !password) {
    return {
      success: false,
      message: "Please fill in all fields.",
    };
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
    return {
      success: false,
      message: "Please enter a valid email address.",
    };
  }

  if (password.length < 6) {
    return {
      success: false,
      message: "Password must contain at least 6 characters.",
    };
  }

  const accounts = await getAccounts();

  if (accounts.some((account) => account.email === cleanEmail)) {
    return {
      success: false,
      message: "An account with this email already exists.",
    };
  }

  const account: StoredAccount = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    name: cleanName,
    email: cleanEmail,
    password,
  };

  await AsyncStorage.setItem(
    ACCOUNTS_KEY,
    JSON.stringify([...accounts, account])
  );

  const user = publicUser(account);

  await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(user));

  return {
    success: true,
    message: "Account created successfully.",
    user,
  };
}

export async function login(
  email: string,
  password: string
): Promise<AuthResult> {
  const accounts = await getAccounts();
  const cleanEmail = email.trim().toLowerCase();

  const account = accounts.find(
    (item) =>
      item.email === cleanEmail &&
      item.password === password
  );

  if (!account) {
    return {
      success: false,
      message: "Incorrect email or password.",
    };
  }

  const user = publicUser(account);

  await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(user));

  return {
    success: true,
    message: "Login successful.",
    user,
  };
}

export async function getCurrentUser(): Promise<DemoUser | null> {
  const stored = await AsyncStorage.getItem(SESSION_KEY);

  return stored ? JSON.parse(stored) : null;
}

export async function logout(): Promise<void> {
  await AsyncStorage.removeItem(SESSION_KEY);
}
