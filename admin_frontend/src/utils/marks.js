/**
 * Mapping helpers shared by marks views and components.
 * A mark can expose `mappings_real` / `mappings_coretax` directly, or a
 * combined `mappings` array tagged with `report_type`.
 */

export const getRealMappings = (mark) => {
  if (Array.isArray(mark?.mappings_real)) return mark.mappings_real;
  if (Array.isArray(mark?.mappings)) {
    return mark.mappings.filter((mapping) => (
      String(mapping?.report_type || 'real').trim().toLowerCase() === 'real'
    ));
  }
  return [];
};

export const getCoretaxMappings = (mark) => (
  Array.isArray(mark?.mappings_coretax)
    ? mark.mappings_coretax
    : (Array.isArray(mark?.mappings)
        ? mark.mappings.filter((mapping) => (
          String(mapping?.report_type || '').trim().toLowerCase() === 'coretax'
        ))
        : [])
);

export const isMarkUnmapped = (mark) => (
  getRealMappings(mark).length === 0 && getCoretaxMappings(mark).length === 0
);

/**
 * Reporting surfaces a mark feeds, derived from its own fields so the list
 * can show downstream impact without extra API calls.
 */
export const getMarkImpactAreas = (mark) => {
  const areas = [];
  if (getRealMappings(mark).length > 0) {
    areas.push('Financial Reports', 'Trial Balance');
  }
  if (Boolean(mark?.is_coretax) || getCoretaxMappings(mark).length > 0) {
    areas.push('Coretax');
  }
  if (Boolean(mark?.is_salary_component)) {
    areas.push('Payroll');
  }
  if (Boolean(mark?.is_rental)) {
    areas.push('Laporan Sewa');
  }
  return areas;
};
