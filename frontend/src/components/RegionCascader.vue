<template>
  <el-cascader
    :model-value="modelValue"
    :options="regionData"
    :props="{ expandTrigger: 'hover' }"
    placeholder="选择省/市/区"
    clearable
    filterable
    style="width: 100%"
    @update:model-value="$emit('update:modelValue', $event)"
  />
</template>

<script setup>
import { regionData } from '../utils/region-data'

defineProps({
  modelValue: { type: Array, default: () => [] },
})
defineEmits(['update:modelValue'])
</script>
