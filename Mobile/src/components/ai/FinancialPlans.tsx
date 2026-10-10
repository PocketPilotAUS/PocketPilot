import React from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { CalendarClock, ChartLine, MessageCircle, Scissors, Target } from "lucide-react-native";

import { useAITheme } from "./useAITheme";
import type { FinancialPlan } from "../../types/plans";
import { formatAED, formatPercent } from "../../utils/dashboard";
import { formatShortDate } from "../../utils/transactions";

const FEATURES = [
  { title: "Savings targets", description: "Set how much you want to save, from an emergency fund to a holiday.", Icon: Target },
  { title: "Deadlines", description: "Choose a date and see the monthly amount needed to get there.", Icon: CalendarClock },
  { title: "Suggested spending cuts", description: "Keep the cuts PocketPilot suggests based on your spending.", Icon: Scissors },
  { title: "Progress", description: "Follow how close you are to each goal over time.", Icon: ChartLine },
];

type Props = {
  plans: FinancialPlan[];
  onStartPlanning: () => void;
};

function PlanCard({ plan }: { plan: FinancialPlan }) {
  const { ai, styles } = useAITheme();
  const progress = plan.targetAmount > 0 ? Math.min(100, (plan.savedAmount / plan.targetAmount) * 100) : 0;

  return (
    <View style={styles.card}>
      <Text style={ai.planTitle}>{plan.title}</Text>
      <Text style={styles.cardSubtitle}>
        {formatAED(plan.savedAmount)} of {formatAED(plan.targetAmount)}
      </Text>

      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${progress}%` }]} />
      </View>
      <Text style={styles.progressCaption}>{formatPercent(progress)} complete</Text>

      <View style={ai.planMeta}>
        {plan.deadline && (
          <View style={ai.planTag}>
            <Text style={ai.planTagText}>By {formatShortDate(plan.deadline)}</Text>
          </View>
        )}
        {plan.monthlyContribution !== null && (
          <View style={ai.planTag}>
            <Text style={ai.planTagText}>{formatAED(plan.monthlyContribution)} / month</Text>
          </View>
        )}
      </View>

      {plan.spendingCuts.map((cut) => (
        <View key={cut.category} style={ai.planCut}>
          <Text style={styles.mutedText}>Cut {cut.category}</Text>
          <Text style={styles.mutedText}>{formatAED(cut.monthlyAmount)} / month</Text>
        </View>
      ))}
    </View>
  );
}

export default function FinancialPlans({ plans, onStartPlanning }: Props) {
  const { ai, styles, palette, mode } = useAITheme();

  if (plans.length > 0) {
    return (
      <ScrollView contentContainerStyle={ai.plansContent}>
        {plans.map((plan) => (
          <PlanCard key={plan.id} plan={plan} />
        ))}
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={ai.plansContent}>
      <View style={styles.card}>
        <View style={ai.plansHero}>
          <LinearGradient
            colors={mode === "dark" ? ["#5FF0CE", "#1FA88A"] : ["#2CC9A6", "#0B8A71"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={ai.orb}
          >
            <Target size={28} color={palette.onAccent} strokeWidth={2.2} />
          </LinearGradient>

          <View style={ai.comingSoon}>
            <Text style={ai.comingSoonText}>Coming soon</Text>
          </View>

          <Text style={ai.welcomeTitle}>No financial plans yet</Text>
          <Text style={ai.welcomeText}>
            Soon you’ll be able to save plans from AI Chat and track your financial goals here.
          </Text>
        </View>

        <View style={ai.featureList}>
          {FEATURES.map(({ title, description, Icon }) => (
            <View key={title} style={ai.featureRow}>
              <View style={ai.featureIcon}>
                <Icon size={17} color={palette.accent} strokeWidth={2.2} />
              </View>
              <View style={ai.featureText}>
                <Text style={ai.featureTitle}>{title}</Text>
                <Text style={ai.featureDescription}>{description}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      <Text style={[styles.mutedText, ai.plansHint]}>
        In the meantime, AI Chat can help you work out a plan.
      </Text>

      <Pressable
        onPress={onStartPlanning}
        style={({ pressed }) => [styles.emptyButton, ai.centered, pressed && styles.buttonDisabled]}
        accessibilityRole="button"
      >
        <MessageCircle size={16} color={palette.onAccent} strokeWidth={2.4} />
        <Text style={styles.emptyButtonText}>Plan a goal in AI Chat</Text>
      </Pressable>
    </ScrollView>
  );
}
