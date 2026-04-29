/**
 * useBankDirection
 * 
 * Transaction direction from the owner's / cash-account perspective.
 * 
 * Internal db_cr convention:
 *   DB (Debit)  = money coming INTO your account = Uang Masuk
 *   CR (Credit) = money going OUT of your account = Uang Keluar
 * 
 * Accounting impact on Cash/Bank asset COA is handled separately by
 * natural_direction + mapping_type — this util is DISPLAY ONLY.
 */

/**
 * Returns true if the transaction is an inflow (money coming in).
 * @param {string} db_cr - 'CR' or 'DB'
 */
export function isInflow(db_cr) {
  return String(db_cr || '').toUpperCase().trim() === 'DB';
}

/**
 * Human-readable label from company's money-flow perspective.
 * @param {string} db_cr
 * @returns {'Masuk' | 'Keluar'}
 */
export function getFlowLabel(db_cr) {
  return isInflow(db_cr) ? 'Masuk' : 'Keluar';
}

/**
 * Bootstrap icon class for the direction.
 * @param {string} db_cr
 */
export function getFlowIcon(db_cr) {
  return isInflow(db_cr) ? 'bi-arrow-down-circle-fill' : 'bi-arrow-up-circle-fill';
}

/**
 * Sign prefix for display (+/-).
 * @param {string} db_cr
 */
export function getAmountSign(db_cr) {
  return isInflow(db_cr) ? '+' : '-';
}

/**
 * Tailwind/CSS color class for the direction.
 * @param {string} db_cr
 * @param {'text'|'bg'|'border'} type
 */
export function getFlowColorClass(db_cr, type = 'text') {
  if (isInflow(db_cr)) {
    return type === 'text' ? 'text-success'
         : type === 'bg'   ? 'bg-success/10 text-success border border-success/20'
         : 'border-success/20';
  }
  return type === 'text' ? 'text-danger'
       : type === 'bg'   ? 'bg-danger/10 text-danger border border-danger/20'
       : 'border-danger/20';
}

/**
 * Vue composable wrapper (optional, for use in <script setup>).
 */
export function useBankDirection() {
  return { isInflow, getFlowLabel, getFlowIcon, getAmountSign, getFlowColorClass };
}
