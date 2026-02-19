<template>
  <Combobox
    v-model="selectedValue"
    as="div"
    class="relative"
  >
    <div class="relative">
      <div class="relative w-full cursor-default overflow-hidden rounded-lg bg-gray-50/50 border border-gray-200 text-left focus-within:ring-2 focus-within:ring-indigo-500 focus-within:ring-opacity-50 transition-all">
        <ComboboxInput
          class="w-full border-none py-2 pl-3 pr-14 text-xs leading-5 text-gray-900 focus:ring-0 bg-transparent outline-none"
          :class="{ 'text-orange-500 italic': isMissingMark(selectedValue) }"
          :displayValue="(val) => getLabel(val)"
          @change="query = $event.target.value"
          :placeholder="placeholder"
        />
        <div class="absolute inset-y-0 right-0 flex items-center pr-2 gap-1">
          <button
            v-if="selectedValue"
            type="button"
            @click.stop="selectedValue = ''"
            class="p-1 hover:bg-gray-200 rounded-full transition-colors"
          >
            <i class="bi bi-x text-xs text-gray-400 hover:text-gray-600"></i>
          </button>
          <ComboboxButton class="flex items-center">
            <i class="bi bi-chevron-down text-[10px] text-gray-400"></i>
          </ComboboxButton>
        </div>
      </div>

      <transition
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
        @after-leave="query = ''"
      >
        <ComboboxOptions
          class="absolute z-30 mt-1 max-h-60 min-w-[200px] w-full overflow-auto rounded-xl bg-white py-1 text-xs shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
        >
          <div v-if="filteredOptions.length === 0 && query !== ''" class="relative cursor-default select-none py-2 px-4 text-gray-700 italic">
            No results found.
          </div>

          <ComboboxOption
            v-for="option in filteredOptions"
            :key="option.id"
            :value="option.id"
            v-slot="{ active, selected }"
          >
            <li
              v-if="option.type === 'separator'"
              class="border-t border-gray-100 my-1 mx-2"
            ></li>
            <li
              v-else
              :class="[
                active ? 'bg-indigo-50 text-indigo-900' : 'text-gray-900',
                'relative cursor-default select-none py-2 pl-10 pr-4'
              ]"
            >
              <span :class="[selected ? 'font-semibold' : 'font-normal', 'block truncate']">
                {{ option.label }}
              </span>
              <span
                v-if="selected"
                class="absolute inset-y-0 left-0 flex items-center pl-3 text-indigo-600"
              >
                <i class="bi bi-check text-lg"></i>
              </span>
            </li>
          </ComboboxOption>
        </ComboboxOptions>
      </transition>
    </div>
  </Combobox>
</template>

<script setup>
import { ref, computed } from 'vue';
import {
  Combobox,
  ComboboxInput,
  ComboboxButton,
  ComboboxOptions,
  ComboboxOption,
} from '@headlessui/vue';

const props = defineProps({
  modelValue: [String, Number],
  options: {
    type: Array,
    required: true
  },
  placeholder: {
    type: String,
    default: 'Select...'
  }
});

const emit = defineEmits(['update:modelValue']);

const query = ref('');

const selectedValue = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const getLabel = (id) => {
  const opt = props.options.find(o => o.id === id);
  if (opt) return opt.label;
  
  // Fallback: show ID with prefix if mark not found in options
  if (id) {
    return `[Missing Mark] ${id.substring(0, 8)}...`;
  }
  
  return '';
};

const isMissingMark = (id) => {
  return id && !props.options.find(o => o.id === id);
};

const filteredOptions = computed(() => {
  if (query.value === '') return props.options;

  const searchLower = query.value.toLowerCase();
  const result = [];
  
  // Reuse the logic from MultiSelect for separators
  let lastCategory = null;

  for (const option of props.options) {
    if (option.type === 'separator') continue;

    if (option.label.toLowerCase().includes(searchLower)) {
      if (option.category && option.category !== lastCategory) {
        if (lastCategory !== null) {
          result.push({
            id: `separator-${option.category}`,
            type: 'separator',
            category: option.category
          });
        }
        lastCategory = option.category;
      }
      result.push(option);
    }
  }

  return result;
});
</script>
