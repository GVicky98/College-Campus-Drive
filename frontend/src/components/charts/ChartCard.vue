<script setup>
import SectionCard from '../ui/SectionCard.vue'
import ChartCanvas from './ChartCanvas.vue'
defineProps({ title: String, subtitle: String, type: String, labels: Array, series: Array, unit: String, height: { type: Number, default: 280 } })
</script>

<template>
  <SectionCard :title="title" :subtitle="subtitle">
    <ChartCanvas :type="type" :labels="labels" :series="series" :unit="unit" :height="height" />
  </SectionCard>
</template>
