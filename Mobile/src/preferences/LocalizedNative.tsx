import React, { forwardRef } from "react";
import { Text as NativeText, TextInput as NativeInput, View as NativeView, Alert as NativeAlert, TextProps, TextInputProps, ViewProps } from "react-native";
import { usePreferences } from "./PreferencesContext";
import { localize } from "./localize";
import { currencyText } from "./currency";

const display = (text: string, language?: Parameters<typeof localize>[1]) => currencyText(text, value => localize(value, language));

export type Text = NativeText;
export const Text = forwardRef<NativeText, TextProps & { localize?: boolean }>(function LocalizedText({ children, style, localize: enabled = true, ...props }, ref) {
  const { language } = usePreferences();
  const values = React.Children.toArray(children);
  const content = enabled && values.every(value => typeof value === "string" || typeof value === "number")
    ? display(values.join(""), language)
    : React.Children.map(children, value => enabled && typeof value === "string" ? display(value, language) : value);
  return <NativeText {...props} ref={ref} accessibilityLabel={props.accessibilityLabel ? display(props.accessibilityLabel, language) : undefined}
    accessibilityHint={props.accessibilityHint ? display(props.accessibilityHint, language) : undefined}
    style={[style, { writingDirection: language === "ar" || language === "ur" ? "rtl" : "ltr" }]}>{content}</NativeText>;
});

export type TextInput = NativeInput;
export const TextInput = Object.assign(forwardRef<NativeInput, TextInputProps>(function LocalizedInput(props, ref) {
  const { language } = usePreferences();
  return <NativeInput {...props} ref={ref} placeholder={props.placeholder ? display(props.placeholder, language) : undefined}
    accessibilityLabel={props.accessibilityLabel ? display(props.accessibilityLabel, language) : undefined} />;
}), { State: NativeInput.State });

export type View = NativeView;
export const View = forwardRef<NativeView, ViewProps>(function LocalizedView(props, ref) {
  const { language } = usePreferences();
  return <NativeView {...props} ref={ref} accessibilityLabel={props.accessibilityLabel ? display(props.accessibilityLabel, language) : undefined}
    accessibilityHint={props.accessibilityHint ? display(props.accessibilityHint, language) : undefined}
    style={[props.style, { direction: language === "ar" || language === "ur" ? "rtl" : "ltr" }]} />;
});

export const Alert: typeof NativeAlert = {
  ...NativeAlert,
  alert: (title, message, buttons, options) => NativeAlert.alert(display(title), message ? display(message) : message,
    buttons?.map(button => ({ ...button, text: button.text ? localize(button.text) : button.text })), options),
};
