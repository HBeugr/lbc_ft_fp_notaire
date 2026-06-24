<template>
  <div class="rapports-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Rapports de Conformité</h1>
        <p class="page-subtitle">Génération et export des rapports réglementaires (FR-24)</p>
      </div>
    </div>

    <div class="rapports-grid">
      <!-- Rapport conformité périodique -->
      <div class="rapport-card">
        <div class="rapport-icon rapport-icon--blue">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 17H7A5 5 0 017 7h2m6 0h2a5 5 0 010 10h-2M9 12h6"/>
          </svg>
        </div>
        <div class="rapport-body">
          <h3 class="rapport-title">Rapport de conformité périodique</h3>
          <p class="rapport-desc">Vue globale de l'activité conformité sur la période : dossiers traités, alertes, révisions, DOS.</p>
          <div class="rapport-form">
            <div class="form-row">
              <div class="field-group">
                <label class="field-label">Date début</label>
                <input v-model="forms.conformite.date_debut" type="date" class="field-input" />
              </div>
              <div class="field-group">
                <label class="field-label">Date fin</label>
                <input v-model="forms.conformite.date_fin" type="date" class="field-input" />
              </div>
            </div>
          </div>
          <button class="btn-generate" :disabled="generating === 'conformite'" @click="generate('conformite')">
            <svg v-if="generating !== 'conformite'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
              <path d="M12 5v14M5 12l7 7 7-7"/>
            </svg>
            <span v-else class="spinner" />
            Générer PDF
          </button>
        </div>
      </div>

      <!-- Rapport client -->
      <div class="rapport-card">
        <div class="rapport-icon rapport-icon--green">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </div>
        <div class="rapport-body">
          <h3 class="rapport-title">Rapport client (dossier complet)</h3>
          <p class="rapport-desc">Dossier complet KYC, documents, score risque, historique cycle de vie. Sans références DOS (Art. 63).</p>
          <div class="rapport-form">
            <div class="field-group">
              <label class="field-label">Référence dossier</label>
              <input v-model="forms.client.dossier_reference" type="text" class="field-input" placeholder="KYC-202605-XXXXXX" />
            </div>
          </div>
          <button class="btn-generate" :disabled="generating === 'client' || !forms.client.dossier_reference" @click="generate('client')">
            <svg v-if="generating !== 'client'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
              <path d="M12 5v14M5 12l7 7 7-7"/>
            </svg>
            <span v-else class="spinner" />
            Générer PDF
          </button>
        </div>
      </div>

      <!-- Rapport audit -->
      <div class="rapport-card">
        <div class="rapport-icon rapport-icon--gold">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
        </div>
        <div class="rapport-body">
          <h3 class="rapport-title">Rapport d'audit (piste complète)</h3>
          <p class="rapport-desc">Journal intégral des actions utilisateurs avec horodatages UTC et adresses IP (Art. 23).</p>
          <div class="rapport-form">
            <div class="form-row">
              <div class="field-group">
                <label class="field-label">Date début</label>
                <input v-model="forms.audit.date_debut" type="date" class="field-input" />
              </div>
              <div class="field-group">
                <label class="field-label">Date fin</label>
                <input v-model="forms.audit.date_fin" type="date" class="field-input" />
              </div>
            </div>
          </div>
          <button class="btn-generate" :disabled="generating === 'audit'" @click="generate('audit')">
            <svg v-if="generating !== 'audit'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
              <path d="M12 5v14M5 12l7 7 7-7"/>
            </svg>
            <span v-else class="spinner" />
            Générer PDF
          </button>
        </div>
      </div>

    </div>

    <!-- Historique des rapports générés -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Historique des rapports générés</h2>
      </div>
      <div v-if="historique.length === 0" class="empty-state">
        <p>Aucun rapport généré pour le moment.</p>
      </div>
      <table v-else class="data-table">
        <thead>
          <tr><th>Type</th><th>Référence</th><th>Généré par</th><th>Date</th><th>Télécharger</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in historique" :key="r.id">
            <td>{{ r.type_rapport }}</td>
            <td class="td-mono">{{ r.reference }}</td>
            <td>{{ r.generated_by }}</td>
            <td>{{ formatDate(r.created_at) }}</td>
            <td>
              <a class="dl-link" :href="r.download_url" download>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="dl-icon">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                PDF
              </a>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/services/api'

interface RapportHistorique {
  id: string
  type_rapport: string
  reference: string
  generated_by: string
  created_at: string
  download_url: string
}

const generating = ref<string | null>(null)
const historique = ref<RapportHistorique[]>([])

const forms = ref({
  conformite: { date_debut: '', date_fin: '' },
  client: { dossier_reference: '' },
  audit: { date_debut: '', date_fin: '' },
})

async function generate(type: string) {
  generating.value = type
  try {
    const params: Record<string, string> = {}
    const f = forms.value[type as keyof typeof forms.value] as Record<string, string>
    Object.entries(f).forEach(([k, v]) => { if (v) params[k] = v })

    const resp = await api.post(`/rapports/${type}`, params, { responseType: 'blob' })

    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `rapport-${type}-${new Date().toISOString().slice(0, 10)}.pdf`
    a.click()
    URL.revokeObjectURL(url)

    await loadHistorique()
  } finally {
    generating.value = null
  }
}

async function loadHistorique() {
  try {
    const resp = await api.get('/rapports/historique')
    historique.value = resp.data.items ?? []
  } catch { /* ignore */ }
}

function formatDate(d: string) {
  return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(d))
}

onMounted(loadHistorique)
</script>

<style scoped>
.rapports-page { display: flex; flex-direction: column; gap: 1.25rem; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; }
.page-title   { font-size: 1.375rem; font-weight: 800; color: var(--color-sidebar-bg); margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: var(--color-text-secondary); margin: 0; }

.rapports-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }

.rapport-card {
  background: var(--color-bg-card); border: 1px solid var(--color-border);
  border-radius: 10px; padding: 1.25rem; display: flex; gap: 1rem;
}
.rapport-icon {
  width: 44px; height: 44px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.rapport-icon svg { width: 22px; height: 22px; }
.rapport-icon--blue   { background: #dbeafe; } .rapport-icon--blue svg   { stroke: #2563eb; }
.rapport-icon--green  { background: var(--color-risk-low-bg); } .rapport-icon--green svg  { stroke: var(--color-risk-low); }
.rapport-icon--gold   { background: #fef9c3; } .rapport-icon--gold svg   { stroke: #ca8a04; }
.rapport-icon--purple { background: #ede9fe; } .rapport-icon--purple svg { stroke: #7c3aed; }

.rapport-body { flex: 1; display: flex; flex-direction: column; gap: 0.625rem; }
.rapport-title { font-size: 0.9375rem; font-weight: 700; color: var(--color-sidebar-bg); margin: 0; }
.rapport-desc  { font-size: 0.8125rem; color: var(--color-text-secondary); margin: 0; line-height: 1.5; }
.rapport-form  { display: flex; flex-direction: column; gap: 0.5rem; }
.form-row  { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
.field-group { display: flex; flex-direction: column; gap: 0.25rem; }
.field-label { font-size: 0.75rem; font-weight: 500; color: var(--color-text-secondary); }
.field-input { padding: 0.4375rem 0.625rem; border: 1px solid var(--color-border); border-radius: 6px; font-size: 0.8125rem; width: 100%; }

.btn-generate {
  display: flex; align-items: center; gap: 0.375rem;
  padding: 0.5rem 1rem; background: var(--color-sidebar-bg); color: #fff;
  border: none; border-radius: 7px; font-size: 0.8125rem; font-weight: 600;
  cursor: pointer; width: fit-content; align-self: flex-start;
}
.btn-generate:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-generate:not(:disabled):hover { background: var(--color-btn-primary-hover); }
.btn-icon { width: 14px; height: 14px; }

.spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Historique */
.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 10px; overflow: hidden; }
.card-header { padding: 1rem 1.25rem; border-bottom: 1px solid var(--color-border); }
.card-title  { font-size: 1rem; font-weight: 700; color: var(--color-sidebar-bg); margin: 0; }

.data-table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
.data-table th { background: var(--color-bg-page); padding: 0.625rem 0.875rem; font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); text-align: left; }
.data-table td { padding: 0.625rem 0.875rem; border-bottom: 1px solid var(--color-border); }
.td-mono { font-family: monospace; font-size: 0.75rem; }

.dl-link { display: inline-flex; align-items: center; gap: 0.25rem; color: var(--color-sidebar-bg); font-weight: 600; text-decoration: none; font-size: 0.8125rem; }
.dl-link:hover { text-decoration: underline; }
.dl-icon { width: 14px; height: 14px; }

.empty-state { padding: 2rem; text-align: center; color: var(--color-text-muted); font-size: 0.875rem; }
</style>
