import React, { useEffect, useRef } from "react";
import { Keyboard, KeyboardAvoidingView, Platform, ScrollView, ScrollViewProps, TextInput } from "react-native";
import { createKeyboardFormStyles } from "../styles/KeyboardFormStyles";

export default function KeyboardFormScrollView({ avoidKeyboard = true, ...props }: ScrollViewProps & { avoidKeyboard?: boolean }) {
  const scroll = useRef<ScrollView>(null);
  const offset = useRef(0);
  const keyboardTop = useRef<number | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const styles = createKeyboardFormStyles();
  const reveal = () => {
    const input = TextInput.State.currentlyFocusedInput();
    const top = keyboardTop.current;
    if (!input || top === null) return;
    input.measureInWindow((_x, y, _width, height) => {
      const overlap = y + height + 24 - top;
      if (overlap > 0) scroll.current?.scrollTo({ y: offset.current + overlap, animated: true });
    });
  };
  const scheduleReveal = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(reveal, 180);
  };
  useEffect(() => {
    const show = Keyboard.addListener("keyboardDidShow", event => { keyboardTop.current = event.endCoordinates.screenY; scheduleReveal(); });
    const change = Keyboard.addListener("keyboardDidChangeFrame", event => { keyboardTop.current = event.endCoordinates.screenY; scheduleReveal(); });
    const hide = Keyboard.addListener("keyboardDidHide", () => { keyboardTop.current = null; });
    return () => { show.remove(); change.remove(); hide.remove(); if (timer.current) clearTimeout(timer.current); };
  }, []);
  const content = <ScrollView {...props} ref={scroll} keyboardShouldPersistTaps="handled" keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"} scrollEventThrottle={16}
    onScroll={event => { offset.current = event.nativeEvent.contentOffset.y; props.onScroll?.(event); }}
    onTouchEnd={event => { scheduleReveal(); props.onTouchEnd?.(event); }} />;
  return avoidKeyboard ? <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : "height"}>{content}</KeyboardAvoidingView> : content;
}
