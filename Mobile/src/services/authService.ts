import AsyncStorage from "@react-native-async-storage/async-storage";

import { clearToken, getToken, saveToken } from "./tokenStorage";

// Keys used by the old demo login, which stored plain-text passwords on the
// device. They are removed on start-up and logout so test devices are cleaned.
const LEGACY_DEMO_KEYS = [
  "@pocketpilot_demo_accounts",
  "@pocketpilot_demo_session",
];

// Same rules as the backend (Backend/app/schemas/user.py)
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;
const NAME_MAX_LENGTH = 100;
const EMAIL_MAX_LENGTH = 254;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Session restore should not keep the loading screen up for long
// if the backend cannot be reached
const RESTORE_TIMEOUT_MS = 8000;

const CONNECTION_ERROR =
  "Could not connect to PocketPilot backend. Check that FastAPI is running.";
const SERVICE_UNAVAILABLE =
  "PocketPilot is temporarily unavailable. Please try again later.";
const LOGIN_FAILED = "Incorrect email or password.";

export type AuthUser = {
  id: number;
  name: string;
  email: string;
  created_at: string;
};

type AuthResult = {
  success: boolean;
  message: string;
  user?: AuthUser;
};

export type RestoreResult =
  | { status: "authenticated"; user: AuthUser }
  | { status: "signedOut" }
  // A token is saved but the backend could not be reached to check it
  | { status: "offline" };

type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

type ValidationError = {
  loc?: (string | number)[];
};

function failure(message: string): AuthResult {
  return { success: false, message };
}

function postJson(apiBaseUrl: string, path: string, body: object) {
  return fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
}

function fetchProfile(
  apiBaseUrl: string,
  token: string,
  signal?: AbortSignal
) {
  return fetch(`${apiBaseUrl}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    signal,
  });
}

async function registrationErrorMessage(response: Response): Promise<string> {
  try {
    const data: { detail?: ValidationError[] } = await response.json();
    const field = data.detail?.[0]?.loc?.[1];

    if (field === "name") {
      return `Please enter a name of up to ${NAME_MAX_LENGTH} characters.`;
    }

    if (field === "email") {
      return "Please enter a valid email address.";
    }

    if (field === "password") {
      return `Password must be ${PASSWORD_MIN_LENGTH} to ${PASSWORD_MAX_LENGTH} characters.`;
    }
  } catch {
    // Fall through to the general message
  }

  return "Please check your details and try again.";
}

async function removeLegacyDemoData(): Promise<void> {
  try {
    await AsyncStorage.multiRemove(LEGACY_DEMO_KEYS);
  } catch {
    // Not critical; try again next time
  }
}

export async function register(
  apiBaseUrl: string,
  name: string,
  email: string,
  password: string
): Promise<AuthResult> {
  const cleanName = name.trim();
  const cleanEmail = email.trim().toLowerCase();

  if (!cleanName || !cleanEmail || !password) {
    return failure("Please fill in all fields.");
  }

  if (cleanName.length > NAME_MAX_LENGTH) {
    return failure(`Name must be ${NAME_MAX_LENGTH} characters or fewer.`);
  }

  if (
    cleanEmail.length > EMAIL_MAX_LENGTH ||
    !EMAIL_PATTERN.test(cleanEmail)
  ) {
    return failure("Please enter a valid email address.");
  }

  // Passwords are never trimmed: spaces are part of the password
  if (password.length < PASSWORD_MIN_LENGTH) {
    return failure(
      `Password must contain at least ${PASSWORD_MIN_LENGTH} characters.`
    );
  }

  if (password.length > PASSWORD_MAX_LENGTH) {
    return failure(
      `Password must be ${PASSWORD_MAX_LENGTH} characters or fewer.`
    );
  }

  let response: Response;

  try {
    response = await postJson(apiBaseUrl, "/auth/register", {
      name: cleanName,
      email: cleanEmail,
      password,
    });
  } catch {
    return failure(CONNECTION_ERROR);
  }

  if (response.status === 409) {
    return failure("An account with this email already exists.");
  }

  if (response.status === 422) {
    return failure(await registrationErrorMessage(response));
  }

  if (response.status !== 201) {
    return failure(
      response.status === 503
        ? SERVICE_UNAVAILABLE
        : "Unable to create your account. Please try again."
    );
  }

  // Registration does not return a token, so sign in straight away
  const result = await login(
    apiBaseUrl,
    cleanEmail,
    password,
    "Account created successfully."
  );

  if (!result.success) {
    // The account exists now; registering again would say "already exists"
    return failure(
      "Your account was created, but signing in failed. Please sign in."
    );
  }

  return result;
}

export async function login(
  apiBaseUrl: string,
  email: string,
  password: string,
  successMessage = "Login successful."
): Promise<AuthResult> {
  const cleanEmail = email.trim().toLowerCase();

  if (!cleanEmail || !password) {
    return failure("Please enter your email and password.");
  }

  let response: Response;

  try {
    response = await postJson(apiBaseUrl, "/auth/login", {
      email: cleanEmail,
      password,
    });
  } catch {
    return failure(CONNECTION_ERROR);
  }

  // 422 only happens for values no account could have (e.g. too long),
  // so it gets the same message as a wrong password
  if (response.status === 401 || response.status === 422) {
    return failure(LOGIN_FAILED);
  }

  if (!response.ok) {
    return failure(
      response.status === 503
        ? SERVICE_UNAVAILABLE
        : "Unable to log in. Please try again."
    );
  }

  try {
    const { access_token }: TokenResponse = await response.json();

    // Load the profile with the new token before saving it
    const profile = await fetchProfile(apiBaseUrl, access_token);

    if (!profile.ok) {
      return failure("Unable to log in. Please try again.");
    }

    const user: AuthUser = await profile.json();

    await saveToken(access_token);

    return { success: true, message: successMessage, user };
  } catch {
    await clearToken();
    return failure("Unable to log in. Please try again.");
  }
}

export async function restoreSession(
  apiBaseUrl: string
): Promise<RestoreResult> {
  await removeLegacyDemoData();

  const token = await getToken();

  if (!token) {
    return { status: "signedOut" };
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), RESTORE_TIMEOUT_MS);

  try {
    const response = await fetchProfile(apiBaseUrl, token, controller.signal);

    if (response.status === 401) {
      // Expired or invalid token
      await clearToken();
      return { status: "signedOut" };
    }

    if (!response.ok) {
      return { status: "offline" };
    }

    const user: AuthUser = await response.json();

    return { status: "authenticated", user };
  } catch {
    return { status: "offline" };
  } finally {
    clearTimeout(timeout);
  }
}

export async function logout(): Promise<void> {
  await clearToken();
  await removeLegacyDemoData();
}
