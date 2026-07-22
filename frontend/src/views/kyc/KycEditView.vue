<template>
  <div class="kyc-edit-page">
    <div v-if="error" class="card error-card">{{ error }}</div>
    <div v-else class="card loading-card">Redirection vers le formulaire KYC…</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { dossiersService } from '@/services/dossiers'

const route = useRoute()
const router = useRouter()

const dossierId = route.params.id as string
const error = ref('')

// Cette route est un alias historique : on redirige vers le formulaire KYC
// notaire canonique (KycPPView / KycPMView) selon le type de client.
onMounted(async () => {
  try {
    const dossier = await dossiersService.get(dossierId)
    const name = dossier.type_client === 'PP' ? 'kyc-pp' : 'kyc-pm'
    router.replace({ name, params: { id: dossierId } })
  } catch {
    error.value = 'Dossier introuvable.'
  }
})
</script>

<style scoped>
.kyc-edit-page { max-width: 860px; }
.loading-card, .error-card {
  padding: 2rem; text-align: center;
  background: var(--color-bg-card); border-radius: 10px;
  border: 1px solid var(--color-border);
}
.error-card { color: var(--color-risk-high); }
</style>
