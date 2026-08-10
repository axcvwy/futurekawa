<script setup lang="ts">
import { use, init, type ECharts, type EChartsCoreOption } from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { Mesure } from "../lib/types";

use([LineChart, GridComponent, LegendComponent, MarkAreaComponent, TooltipComponent, CanvasRenderer]);

interface Props {
  mesures: Mesure[];
  seuils?: {
    temperature_min_c?: number | null;
    temperature_max_c?: number | null;
    humidite_min_pct?: number | null;
    humidite_max_pct?: number | null;
  };
}

const props = defineProps<Props>();

const conteneur = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;

interface Point {
  horodatage: string;
  temperature: number | null;
  humidite: number | null;
  tempHorsBande: boolean;
  humHorsBande: boolean;
}

function horsBande(valeur: number | null, min: number | null, max: number | null): boolean {
  return valeur != null && min != null && max != null && (valeur < min || valeur > max);
}

function construireOption(): EChartsCoreOption {
  const teintes = getComputedStyle(document.documentElement);
  const css = (propriete: string, defaut: string): string =>
    teintes.getPropertyValue(propriete).trim() || defaut;

  const couleurBordure = css("--border", "#e5e4e7");
  const couleurMuted = css("--muted-foreground", "#6b7280");
  const couleurAccent = css("--accent", "#2e8b57");
  const couleurTemp = css("--temperature", "#d97706");
  const couleurHum = css("--humidite", "#2563eb");
  const couleurDestructive = css("--destructive", "#dc2626");
  const couleurCarte = css("--card", "#ffffff");

  const seuils = props.seuils ?? {};
  const tempMin = seuils.temperature_min_c ?? null;
  const tempMax = seuils.temperature_max_c ?? null;
  const humMin = seuils.humidite_min_pct ?? null;
  const humMax = seuils.humidite_max_pct ?? null;

  const points: Point[] = [...props.mesures]
    .sort((a, b) => new Date(a.date_mesure).getTime() - new Date(b.date_mesure).getTime())
    .map((m) => ({
      horodatage: new Intl.DateTimeFormat("fr-FR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(m.date_mesure)),
      temperature: m.temperature_c ?? null,
      humidite: m.humidite_pct ?? null,
      tempHorsBande: horsBande(m.temperature_c ?? null, tempMin, tempMax),
      humHorsBande: horsBande(m.humidite_pct ?? null, humMin, humMax),
    }));

  const donneesTemperature = points.map((p) => ({
    value: p.temperature,
    symbolSize: p.tempHorsBande ? 7 : 0,
    itemStyle: p.tempHorsBande ? { color: couleurDestructive, borderColor: couleurDestructive } : undefined,
  }));

  const donneesHumidite = points.map((p) => ({
    value: p.humidite,
    symbolSize: p.humHorsBande ? 7 : 0,
    itemStyle: p.humHorsBande ? { color: couleurDestructive, borderColor: couleurDestructive } : undefined,
  }));

  return {
    grid: { top: 8, right: 16, left: 8, bottom: 0, containLabel: true },
    tooltip: {
      trigger: "axis",
      backgroundColor: couleurCarte,
      borderColor: couleurBordure,
      borderRadius: 8,
      textStyle: { color: css("--foreground", "#1f2937"), fontSize: 12 },
    },
    legend: { top: 0, textStyle: { fontSize: 12 } },
    xAxis: {
      type: "category",
      data: points.map((p) => p.horodatage),
      axisLabel: { color: couleurMuted, fontSize: 11 },
      axisLine: { lineStyle: { color: couleurBordure } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: "value",
        name: "°C",
        nameTextStyle: { color: couleurMuted, fontSize: 11 },
        axisLabel: { color: couleurMuted, fontSize: 11 },
        splitLine: { lineStyle: { color: couleurBordure, type: "dashed" } },
      },
      {
        type: "value",
        name: "%",
        nameTextStyle: { color: couleurMuted, fontSize: 11 },
        axisLabel: { color: couleurMuted, fontSize: 11 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "Température (°C)",
        type: "line",
        yAxisIndex: 0,
        data: donneesTemperature,
        smooth: true,
        showSymbol: true,
        connectNulls: true,
        lineStyle: { color: couleurTemp, width: 2 },
        itemStyle: { color: couleurTemp },
        markArea:
          tempMin != null && tempMax != null
            ? {
                silent: true,
                itemStyle: { color: couleurAccent, opacity: 0.08 },
                data: [[{ yAxis: tempMin }, { yAxis: tempMax }]],
              }
            : undefined,
      },
      {
        name: "Humidité (%)",
        type: "line",
        yAxisIndex: 1,
        data: donneesHumidite,
        smooth: true,
        showSymbol: true,
        connectNulls: true,
        lineStyle: { color: couleurHum, width: 2 },
        itemStyle: { color: couleurHum },
        markArea:
          humMin != null && humMax != null
            ? {
                silent: true,
                itemStyle: { color: couleurHum, opacity: 0.06 },
                data: [[{ yAxis: humMin }, { yAxis: humMax }]],
              }
            : undefined,
      },
    ],
  };
}

function redessiner(): void {
  if (!chart) return;
  chart.setOption(construireOption(), true);
}

function redimensionner(): void {
  chart?.resize();
}

onMounted(() => {
  if (!conteneur.value) return;
  chart = init(conteneur.value);
  chart.setOption(construireOption());
  window.addEventListener("resize", redimensionner);
});

watch(
  () => [props.mesures, props.seuils] as const,
  () => redessiner(),
  { deep: true },
);

onBeforeUnmount(() => {
  window.removeEventListener("resize", redimensionner);
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div ref="conteneur" class="h-[340px] w-full"></div>
</template>
