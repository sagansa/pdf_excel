<template>
  <Combobox
    v-model="selectedValue"
    as="div"
    class="relative"
  >
    <div class="relative">
      <div class="ui-input-shell">
        <ComboboxInput
          class="w-full border-none bg-transparent py-2 pl-3 pr-14 text-xs leading-5 outline-none focus:placeholder-transparent focus:ring-0"
          style="color: var(--color-text)"
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
            class="ui-clear-button"
          >
            <i class="bi bi-x text-xs"></i>
          </button>
          <ComboboxButton class="flex items-center">
            <i class="bi bi-chevron-down text-[10px] text-muted"></i>
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
          class="ui-dropdown-panel absolute z-30 mt-1 max-h-60 min-w-[200px] w-full overflow-auto rounded-xl py-1 text-xs focus:outline-none"
        >
          <div v-if="filteredOptions.length === 0 && query !== ''" class="relative cursor-default select-none py-2 px-4 text-muted italic">
            No results found.
          </div>

          <ComboboxOption
            v-for="option in filteredOptions"
            :key="option.id || (option.type === 'separator' ? 'sep-' + option.label : Math.random())"
            :value="option.id"
            :disabled="option.type === 'separator'"
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
                'relative cursor-default select-none py-2 pl-10 pr-4'
              ]"
            >
              <span :class="[selected ? 'font-semibold' : 'font-normal', 'block truncate']">
                {{ option.label }}
              </span>
              <span
                v-if="selected"
                class="absolute inset-y-0 left-0 flex items-center pl-3"
                style="color: var(--color-primary)"
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
import { filterSelectOptions, findSelectLabel } from './selectUtils';

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
  const label = findSelectLabel(props.options, id, '');
  if (label) return label;
  
  // Fallback: show ID with prefix if mark not found in options
  if (id) {
    return `[Missing Mark] ${id.substring(0, 8)}...`;
  }
  
  return '';
};

const isMissingMark = (id) => {
  return id && !findSelectLabel(props.options, id, '');
};

const filteredOptions = computed(() => {
  return filterSelectOptions(props.options, query.value);
});
</script>
