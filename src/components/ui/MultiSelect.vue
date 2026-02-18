<template>
  <Listbox
    v-model="selectedValues"
    multiple
    as="div"
    class="relative"
  >
    <div class="relative">
      <ListboxButton
        class="input-base !py-1.5 !text-xs text-left flex items-center justify-between gap-1 min-h-[32px]"
      >
        <span class="block truncate">
          {{ selectedLabel }}
        </span>
        <span class="pointer-events-none flex items-center">
          <i class="bi bi-chevron-down text-[10px] text-gray-400"></i>
        </span>
      </ListboxButton>

      <transition
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <ListboxOptions
          class="absolute z-10 mt-1 max-h-60 min-w-[250px] overflow-auto rounded-xl bg-white py-1 text-xs shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
        >
          <!-- Search Input -->
          <div class="px-3 py-2 border-b border-gray-100 sticky top-0 bg-white z-20">
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-2 flex items-center text-gray-400">
                <i class="bi bi-search text-[10px]"></i>
              </span>
              <input
                ref="searchInput"
                type="text"
                v-model="query"
                @click.stop
                @keydown.stop
                class="w-full pl-7 pr-2 py-1 text-[10px] border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Search..."
              />
            </div>
          </div>

          <!-- Select All / Clear All -->
          <div class="px-2 py-1 flex gap-2 border-b border-gray-50 bg-gray-50/30 sticky top-[45px] bg-white z-10">
            <button 
              @click.stop="selectAll" 
              class="text-[9px] text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Select All
            </button>
            <button 
              @click.stop="clearAll" 
              class="text-[9px] text-gray-500 hover:text-gray-700 font-medium"
            >
              Clear
            </button>
          </div>

          <div v-if="filteredOptions.length === 0" class="px-4 py-2 text-gray-400 italic">
            No results found
          </div>

          <ListboxOption
            v-for="option in filteredOptions"
            :key="option.id"
            :value="option.id"
            v-slot="{ active, selected }"
          >
            <li
              v-if="option.type === 'separator'"
              class="border-t border-gray-200 my-1 mx-2"
            ></li>
            <li
              v-else
              :class="[
                active ? 'bg-indigo-50 text-indigo-900' : 'text-gray-900',
                'relative cursor-default select-none py-2 pl-8 pr-4'
              ]"
            >
              <span
                :class="[
                  selected ? 'font-semibold' : 'font-normal',
                  'block'
                ]"
              >
                {{ option.label }}
              </span>

              <span
                v-if="selected"
                :class="[
                  active ? 'text-indigo-600' : 'text-indigo-600',
                  'absolute inset-y-0 left-0 flex items-center pl-2'
                ]"
              >
                <i class="bi bi-check2 text-sm"></i>
              </span>
            </li>
          </ListboxOption>
        </ListboxOptions>
      </transition>
    </div>
  </Listbox>
</template>

<script setup>
import { ref, computed } from 'vue';
import {
  Listbox,
  ListboxButton,
  ListboxOptions,
  ListboxOption,
} from '@headlessui/vue';

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
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
const searchInput = ref(null);

const selectedValues = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const filteredOptions = computed(() => {
  if (query.value === '') return props.options;

  const searchLower = query.value.toLowerCase();
  const result = [];
  const filteredRegularOptions = [];

  // First, filter all regular (non-separator) options
  for (const option of props.options) {
    if (option.type === 'separator') continue;
    if (option.label.toLowerCase().includes(searchLower)) {
      filteredRegularOptions.push(option);
    }
  }

  // If no filtered options, return empty
  if (filteredRegularOptions.length === 0) return [];

  // Now rebuild the structure with separators
  let lastCategory = null;

  for (const option of props.options) {
    if (option.type === 'separator') {
      // Skip separator for now, will add later
      continue;
    }

    if (option.label.toLowerCase().includes(searchLower)) {
      // Add separator if category changed and it's not the first option
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

const selectedLabel = computed(() => {
  if (selectedValues.value.length === 0) return props.placeholder;
  if (selectedValues.value.length === 1) {
    const opt = props.options.find(o => o.id === selectedValues.value[0]);
    return opt ? opt.label : props.placeholder;
  }
  return `${selectedValues.value.length} selected`;
});

const selectAll = () => {
    const allIds = props.options.filter(o => o.type !== 'separator').map(o => o.id);
    emit('update:modelValue', allIds);
};

const clearAll = () => {
    emit('update:modelValue', []);
};
</script>
