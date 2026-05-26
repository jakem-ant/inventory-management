<template>
  <div class="restocking">
    <div class="page-header">
      <h2>Restocking</h2>
      <p>Set your budget, review recommended items driven by demand forecasts, and submit a restock order.</p>
    </div>

    <div class="card budget-card">
      <div class="card-header">
        <h3 class="card-title">Available Budget</h3>
        <span class="budget-display">{{ formatCurrency(budget) }}</span>
      </div>
      <div class="budget-slider-row">
        <input
          type="range"
          class="budget-slider"
          :min="10000"
          :max="1000000"
          :step="10000"
          v-model.number="budget"
        />
      </div>
      <div class="slider-hint">$10K – $1M</div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Items Recommended</div>
        <div class="stat-value">{{ recommendations.length }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Cost</div>
        <div class="stat-value">{{ formatCurrency(totalCost) }}</div>
      </div>
      <div :class="['stat-card', remainingBudget > 0 ? 'success' : 'warning']">
        <div class="stat-label">Remaining Budget</div>
        <div class="stat-value">{{ formatCurrency(remainingBudget) }}</div>
      </div>
    </div>

    <div v-if="successBanner" class="alert-success">
      <span>
        Restock order {{ lastOrder.order_number }} submitted.
        Expected delivery {{ formatDate(lastOrder.expected_delivery) }} ({{ lastOrder.lead_time_days }} days).
      </span>
      <button class="dismiss-btn" @click="successBanner = false">Dismiss</button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Recommended Items ({{ recommendations.length }})</h3>
      </div>

      <div v-if="loading" class="loading">Loading…</div>
      <template v-else>
        <div v-if="recommendations.length === 0" class="empty-state-block">
          No items fit within this budget. Try raising the slider.
        </div>
        <div v-else class="table-container">
          <table class="restock-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Name</th>
                <th>Category</th>
                <th>Trend</th>
                <th>Current / Forecasted</th>
                <th>Recommended Qty</th>
                <th>Unit Cost</th>
                <th>Line Total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in recommendations" :key="rec.item_sku">
                <td><strong>{{ rec.item_sku }}</strong></td>
                <td>{{ rec.item_name }}</td>
                <td>{{ rec.category }}</td>
                <td>
                  <span :class="['badge', rec.trend]">{{ rec.trend }}</span>
                </td>
                <td>{{ rec.current_demand }} / {{ rec.forecasted_demand }}</td>
                <td>{{ rec.recommended_quantity }}</td>
                <td>{{ formatCurrency(rec.unit_cost) }}</td>
                <td><strong>{{ formatCurrency(rec.line_total) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <div class="action-row">
      <button
        class="btn-primary"
        :disabled="recommendations.length === 0 || submitting"
        @click="placeOrder"
      >
        {{ submitting ? 'Submitting…' : 'Place Order' }}
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const budget = ref(250000)
    const recommendations = ref([])
    const loading = ref(true)
    const submitting = ref(false)
    const error = ref(null)
    const lastOrder = ref(null)
    const successBanner = ref(false)

    // Debounce timer ref — cleared on unmount
    const debounceTimer = ref(null)

    const totalCost = computed(() =>
      recommendations.value.reduce((sum, r) => sum + r.line_total, 0)
    )

    const remainingBudget = computed(() => budget.value - totalCost.value)

    const formatDate = (iso) => {
      const d = new Date(iso)
      if (isNaN(d.getTime())) return iso
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
    }

    const loadRecommendations = async () => {
      loading.value = true
      error.value = null
      try {
        recommendations.value = await api.getRestockRecommendations(budget.value)
      } catch (err) {
        error.value = 'Failed to load recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Debounced watch — 250ms delay before firing API call
    watch(budget, () => {
      clearTimeout(debounceTimer.value)
      debounceTimer.value = setTimeout(() => {
        loadRecommendations()
      }, 250)
    })

    onBeforeUnmount(() => {
      clearTimeout(debounceTimer.value)
    })

    const placeOrder = async () => {
      submitting.value = true
      error.value = null
      const items = recommendations.value.map(r => ({
        sku: r.item_sku,
        name: r.item_name,
        quantity: r.recommended_quantity,
        unit_cost: r.unit_cost
      }))
      try {
        const order = await api.createRestockOrder(items)
        lastOrder.value = order
        recommendations.value = []
        successBanner.value = true
      } catch (err) {
        error.value = 'Failed to place order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadRecommendations)

    return {
      budget,
      recommendations,
      loading,
      submitting,
      error,
      lastOrder,
      successBanner,
      totalCost,
      remainingBudget,
      formatCurrency,
      formatDate,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.budget-display {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.025em;
}

.budget-slider-row {
  padding: 0.5rem 0 0.25rem;
}

.budget-slider {
  width: 100%;
  height: 6px;
  appearance: none;
  -webkit-appearance: none;
  background: var(--border-color);
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid #ffffff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: background 0.15s ease;
  /* WebKit aligns the thumb's top to the track's top, so a 20px thumb on a
     6px track sits below the line; pull it up by (20 - 6) / 2 to center it. */
  margin-top: -7px;
}

.budget-slider::-webkit-slider-thumb:hover {
  background: #2563eb;
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid #ffffff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
  cursor: pointer;
}

.budget-slider::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 3px;
  background: var(--border-color);
}

.budget-slider::-moz-range-track {
  height: 6px;
  border-radius: 3px;
  background: var(--border-color);
}

.slider-hint {
  font-size: 0.813rem;
  color: var(--text-muted);
  margin-top: 0.375rem;
}

.empty-state-block {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 2.5rem;
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.938rem;
  margin: 0.5rem 0;
}

.action-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 1rem;
}

.btn-primary {
  background: #3b82f6;
  color: #ffffff;
  border: none;
  padding: 0.625rem 1.5rem;
  border-radius: 6px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.alert-success {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #dcfce7;
  border: 1px solid #22c55e;
  color: #166534;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
}

.dismiss-btn {
  background: none;
  border: none;
  color: #166534;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
  margin-left: 1rem;
  flex-shrink: 0;
}

.dismiss-btn:hover {
  color: #14532d;
}

.restock-table {
  width: 100%;
}
</style>
