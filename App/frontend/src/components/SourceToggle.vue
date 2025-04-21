<template>
  <div class="source-toggle">
    <div class="toggle-container">
      <button
        :class="['toggle-btn', { active: props.modelValue === 'news' }]"
        @click="emit('update:modelValue', 'news')"
      >
        News
      </button>
      <button
        :class="['toggle-btn', { active: props.modelValue === 'reddit' }]"
        @click="emit('update:modelValue', 'reddit')"
      >
        Reddit
      </button>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

// Props definition using defineProps
const props = defineProps({
  modelValue: {
    type: String,
    required: true,
    validator: value => ['news', 'reddit'].includes(value)
  }
});

// Emits definition using defineEmits
const emit = defineEmits(['update:modelValue']);
</script>


<style>
/* ... existing styles ... */
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');

.source-toggle {
  display: flex;
  justify-content: center;
  margin: 0 0 20px 0;
  width: 100%;
}

.toggle-container {
  display: flex;
  background-color: #ffdc92;
  padding: 4px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  font-family: "Inter", Arial;
}

.toggle-btn {
  padding: 8px 24px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 16px;
  border-radius: 6px;
  transition: all 0.3s ease;
  min-width: 100px;
  color: rgb(255, 255, 255);
  font-family: "Inter", Arial;
  font-weight: 700
}

.toggle-btn.active {
  background-color: #eca406;
  color: white;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.toggle-btn:not(.active):hover {
  background-color: #e6bf6c;
}
</style>