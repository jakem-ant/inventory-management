<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'create' ? t('purchaseOrder.createTitle') : t('purchaseOrder.viewTitle') }}
            </h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <!-- Create mode body -->
          <div v-if="mode === 'create'" class="modal-body">
            <div class="item-summary">
              <div class="summary-row">
                <span class="summary-label">{{ t('purchaseOrder.item') }}</span>
                <span class="summary-value">{{ translateProductName(backlogItem.item_name) }}</span>
              </div>
              <div class="summary-row">
                <span class="summary-label">{{ t('purchaseOrder.sku') }}</span>
                <span class="summary-value mono">{{ backlogItem.item_sku }}</span>
              </div>
              <div class="summary-row">
                <span class="summary-label">{{ t('purchaseOrder.shortage') }}</span>
                <span class="summary-value shortage-value">{{ shortage }} {{ t('purchaseOrder.unitsShort') }}</span>
              </div>
            </div>

            <form @submit.prevent class="po-form">
              <div class="form-group">
                <label for="po-supplier">{{ t('purchaseOrder.supplier') }}</label>
                <input
                  id="po-supplier"
                  v-model="form.supplier_name"
                  type="text"
                  required
                  :placeholder="t('purchaseOrder.supplierPlaceholder')"
                  class="form-input"
                />
              </div>

              <div class="form-row-2">
                <div class="form-group">
                  <label for="po-quantity">{{ t('purchaseOrder.quantity') }}</label>
                  <input
                    id="po-quantity"
                    v-model.number="form.quantity"
                    type="number"
                    required
                    min="1"
                    class="form-input"
                  />
                </div>

                <div class="form-group">
                  <label for="po-unit-cost">{{ t('purchaseOrder.unitCost') }}</label>
                  <input
                    id="po-unit-cost"
                    v-model.number="form.unit_cost"
                    type="number"
                    required
                    min="0"
                    step="0.01"
                    class="form-input"
                  />
                </div>
              </div>

              <div class="form-group">
                <label for="po-delivery">{{ t('purchaseOrder.expectedDelivery') }}</label>
                <input
                  id="po-delivery"
                  v-model="form.expected_delivery_date"
                  type="date"
                  required
                  class="form-input"
                />
              </div>

              <div class="form-group">
                <label for="po-notes">{{ t('purchaseOrder.notes') }}</label>
                <textarea
                  id="po-notes"
                  v-model="form.notes"
                  :placeholder="t('purchaseOrder.notesPlaceholder')"
                  class="form-input form-textarea"
                  rows="3"
                />
              </div>

              <div class="total-cost-row">
                <span class="total-cost-label">{{ t('purchaseOrder.totalCost') }}</span>
                <span class="total-cost-value">{{ formattedTotal }}</span>
              </div>

              <div v-if="submitError" class="inline-error">{{ submitError }}</div>
            </form>
          </div>

          <!-- View mode body -->
          <div v-else class="modal-body">
            <div v-if="poLoading" class="state-message">{{ t('purchaseOrder.loading') }}</div>
            <div v-else-if="poLoadError" class="inline-error">{{ poLoadError }}</div>
            <div v-else-if="poData" class="po-detail">
              <div class="info-grid">
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.poNumber') }}</div>
                  <div class="info-value mono">{{ poData.id }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.item') }}</div>
                  <div class="info-value">{{ translateProductName(backlogItem.item_name) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.sku') }}</div>
                  <div class="info-value mono">{{ backlogItem.item_sku }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.supplier') }}</div>
                  <div class="info-value">{{ poData.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.quantity') }}</div>
                  <div class="info-value">{{ poData.quantity }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.unitCost') }}</div>
                  <div class="info-value">{{ formatCurrency(poData.unit_cost, currentCurrency) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.totalCost') }}</div>
                  <div class="info-value">{{ formatCurrency(poData.quantity * poData.unit_cost, currentCurrency) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.expectedDelivery') }}</div>
                  <div class="info-value">{{ formatDate(poData.expected_delivery_date) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.createdDate') }}</div>
                  <div class="info-value">{{ formatDate(poData.created_date) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.status') }}</div>
                  <div class="info-value">
                    <span class="badge success">
                      {{ poData.status === 'Submitted' ? t('purchaseOrder.statusSubmitted') : poData.status }}
                    </span>
                  </div>
                </div>
                <div v-if="poData.notes" class="info-item full-width">
                  <div class="info-label">{{ t('purchaseOrder.notes') }}</div>
                  <div class="info-value">{{ poData.notes }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="close">{{ t('common.close') }}</button>
            <button
              v-if="mode === 'create'"
              type="button"
              class="btn-primary"
              :disabled="!isFormValid || submitting"
              @click="handleSubmit"
            >
              {{ submitting ? t('purchaseOrder.creating') : t('purchaseOrder.submit') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { useI18n } from '../composables/useI18n'
import { api } from '../api'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'PurchaseOrderModal',
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    backlogItem: {
      type: Object,
      default: null
    },
    mode: {
      type: String,
      default: 'create'
    }
  },
  emits: ['close', 'po-created'],
  setup(props, { emit }) {
    const { t, currentLocale, currentCurrency, translateProductName } = useI18n()

    // Create mode state
    const form = ref({
      supplier_name: '',
      quantity: 0,
      unit_cost: '',
      expected_delivery_date: '',
      notes: ''
    })
    const submitting = ref(false)
    const submitError = ref(null)

    // View mode state
    const poData = ref(null)
    const poLoading = ref(false)
    const poLoadError = ref(null)

    const shortage = computed(() => {
      if (!props.backlogItem) return 0
      return Math.abs(props.backlogItem.quantity_needed - props.backlogItem.quantity_available)
    })

    const isFormValid = computed(() => {
      return (
        form.value.supplier_name.trim() !== '' &&
        form.value.quantity >= 1 &&
        form.value.unit_cost !== '' && form.value.unit_cost !== null &&
        form.value.expected_delivery_date !== ''
      )
    })

    const formattedTotal = computed(() => {
      const qty = Number(form.value.quantity) || 0
      const cost = Number(form.value.unit_cost) || 0
      return formatCurrency(qty * cost, currentCurrency.value)
    })

    const getDefaultDeliveryDate = () => {
      const date = new Date()
      date.setDate(date.getDate() + 14)
      return date.toISOString().split('T')[0]
    }

    const initForm = () => {
      form.value = {
        supplier_name: '',
        quantity: shortage.value,
        unit_cost: '',
        expected_delivery_date: getDefaultDeliveryDate(),
        notes: ''
      }
      submitError.value = null
      submitting.value = false
    }

    const initView = async () => {
      poData.value = null
      poLoadError.value = null

      // Use already-fetched PO data if the Dashboard attached it after creation
      if (props.backlogItem.purchase_order) {
        poData.value = props.backlogItem.purchase_order
        return
      }

      poLoading.value = true
      try {
        poData.value = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
      } catch (err) {
        poLoadError.value = t('purchaseOrder.loadError')
        console.error(err)
      } finally {
        poLoading.value = false
      }
    }

    // Reset or load whenever the modal opens (or the target item changes while open)
    watch(
      [() => props.isOpen, () => props.backlogItem],
      ([newOpen]) => {
        if (newOpen && props.backlogItem) {
          if (props.mode === 'create') {
            initForm()
          } else {
            initView()
          }
        }
      }
    )

    const close = () => {
      emit('close')
    }

    const handleSubmit = async () => {
      if (!isFormValid.value || submitting.value) return

      submitting.value = true
      submitError.value = null
      try {
        const response = await api.createPurchaseOrder({
          backlog_item_id: props.backlogItem.id,
          supplier_name: form.value.supplier_name,
          quantity: form.value.quantity,
          unit_cost: form.value.unit_cost,
          expected_delivery_date: form.value.expected_delivery_date,
          notes: form.value.notes
        })
        emit('po-created', response)
        emit('close')
      } catch (err) {
        submitError.value = t('purchaseOrder.createError') + ': ' + err.message
        console.error(err)
      } finally {
        submitting.value = false
      }
    }

    const formatDate = (dateString) => {
      if (!dateString) return '-'
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return '-'
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, { month: 'short', day: 'numeric', year: 'numeric' })
    }

    return {
      t,
      currentCurrency,
      translateProductName,
      form,
      submitting,
      submitError,
      poData,
      poLoading,
      poLoadError,
      shortage,
      isFormValid,
      formattedTotal,
      close,
      handleSubmit,
      formatDate,
      formatCurrency
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: var(--bg-card);
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.025em;
  margin: 0;
}

.close-button {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: var(--bg-surface);
  color: var(--text-primary);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.modal-footer {
  padding: 1.25rem 1.5rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

/* Backlog item summary strip */
.item-summary {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.summary-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.summary-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  min-width: 100px;
}

.summary-value {
  font-size: 0.938rem;
  color: var(--text-primary);
  font-weight: 500;
}

.summary-value.mono {
  font-family: 'Monaco', 'Courier New', monospace;
}

.shortage-value {
  color: #dc2626;
  font-weight: 700;
}

/* Form */
.po-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input {
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 0.938rem;
  font-family: inherit;
  background: var(--bg-surface);
  color: var(--text-primary);
  transition: border-color 0.15s ease;
  width: 100%;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

/* Total cost display */
.total-cost-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 1rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.total-cost-label {
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
}

.total-cost-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
}

/* Inline error */
.inline-error {
  font-size: 0.875rem;
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 0.625rem 0.875rem;
}

/* Loading/empty state */
.state-message {
  padding: 2rem;
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.938rem;
}

/* PO detail view */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
}

.info-value {
  font-size: 0.938rem;
  color: var(--text-primary);
  font-weight: 500;
}

.info-value.mono {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
}

/* Buttons */
.btn-secondary {
  padding: 0.625rem 1.25rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary:hover {
  background: var(--border-color);
}

.btn-primary {
  padding: 0.625rem 1.25rem;
  background: #3b82f6;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  color: white;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal transitions */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
