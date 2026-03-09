<template>
  <Listbox
    v-model="selectedValues"
    multiple
    as="div"
    class="relative"
  >
    <div class="relative">
      <ListboxButton
        class="ui-dropdown-trigger"
      >
        <span class="block truncate">
          {{ selectedLabel }}
        </span>
        <span class="pointer-events-none flex items-center">
          <i class="bi bi-chevron-down text-[10px] text-muted"></i>
        </span>
      </ListboxButton>

      <transition
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <ListboxOptions
          class="ui-dropdown-panel absolute z-10 mt-1 max-h-60 min-w-[250px] overflow-auto rounded-xl py-1 text-xs focus:outline-none"
        >
          <!-- Search Input -->
          <div class="ui-dropdown-toolbar sticky top-0 z-20 border-b px-3 py-2">
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-2 flex items-center text-muted">
                <i class="bi bi-search text-[10px]"></i>
              </span>
              <input
                ref="searchInput"
                type="text"
                v-model="query"
                @click.stop
                @keydown.stop
                class="ui-dropdown-search"
                placeholder="Search..."
              />
            </div>
          </div>

          <!-- Select All / Clear All -->
          <div class="ui-dropdown-toolbar sticky top-[45px] z-10 flex gap-2 border-b px-2 py-1">
            <button 
              @click.stop="selectAll" 
              class="text-[9px] hover:opacity-80 font-medium"
              style="color: var(--color-primary)"
            >
              Select All
            </button>
            <button 
              @click.stop="clearAll" 
              class="text-[9px] text-muted hover:text-theme font-medium"
            >
              Clear
            </button>
          </div>

          <div v-if="filteredOptions.length === 0" class="px-4 py-2 text-muted italic">
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
              class="border-t my-1 mx-2"
              style="border-color: var(--color-border)"
            ></li>
            <li
              v-else
              :class="[
                active ? 'ui-dropdown-option--active' : 'text-theme',
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
                class="absolute inset-y-0 left-0 flex items-center pl-2"
                style="color: var(--color-primary)"
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
import { filterSelectOptions, findSelectLabel } from './selectUtils';

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
  return filterSelectOptions(props.options, query.value);
});

const selectedLabel = computed(() => {
  if (selectedValues.value.length === 0) return props.placeholder;
  if (selectedValues.value.length === 1) {
    return findSelectLabel(props.options, selectedValues.value[0], props.placeholder);
  }
  return `${selectedValues.value.length} selected`;
});

const selectAll = () => {
    const allIds = props.options.filter(o => o.type !== 'separator').map(o => o.id);
    emit('update:modelValue', allIds);
};

const clearAll = () => {
    query.value = '';
    emit('update:modelValue', []);
};
</script>
