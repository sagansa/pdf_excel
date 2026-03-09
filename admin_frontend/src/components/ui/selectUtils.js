export const filterSelectOptions = (options = [], query = '') => {
  const searchLower = String(query || '').trim().toLowerCase();
  if (!searchLower) return options;

  const result = [];
  let lastCategory = null;

  for (const option of options) {
    if (option.type === 'separator') continue;

    const label = String(option.label || '').toLowerCase();
    if (!label.includes(searchLower)) continue;

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

  return result;
};

export const findSelectOption = (options = [], value) => {
  const normalizedValue = String(value ?? '');
  return options.find(option => String(option.id ?? '') === normalizedValue);
};

export const findSelectLabel = (options = [], value, fallback = '') => {
  return findSelectOption(options, value)?.label ?? fallback;
};
